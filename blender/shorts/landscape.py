"""Landscape builders: heightfield terrain, rocks, grass tufts, sea ice, and section faces.

Height functions are plain Python callables h(x, y) -> z, so the same function can
build the terrain surface, the matching cut face of a section, and placement of props.
Coordinates are meters.
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector, noise

from . import materials, shapes


# ---------------------------------------------------------------- noise helpers

def fbm(x, y, scale=1.0, octaves=4, seed=0, z=0.0):
    """Fractal noise in roughly [-1, 1] at feature size `scale` (meters)."""
    p = Vector((x / scale + seed * 17.13, y / scale - seed * 9.71, z + seed * 3.3))
    return noise.fractal(p, 0.5, 2.0, octaves, noise_basis="PERLIN_ORIGINAL") * 0.9


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def spaced(segments):
    """1D coordinates from [(start, end, spacing), ...] segments (contiguous, increasing)."""
    out = []
    for a, b, step in segments:
        n = max(int(math.ceil((b - a) / step)), 1)
        for i in range(n):
            out.append(a + (b - a) * i / n)
    out.append(segments[-1][1])
    return out


def with_exact(coords, *values):
    """Insert exact coordinates (e.g. a section plane) into a sorted coordinate list."""
    out = sorted(set(round(c, 6) for c in coords) | set(values))
    return out


# ---------------------------------------------------------------- meshes

def _attr(mesh, name, values):
    a = mesh.attributes.new(name, "FLOAT", "POINT")
    a.data.foreach_set("value", values)


def heightfield(name, xs, ys, height, mat=None, attrs=None):
    """A grid surface over the tensor product of xs and ys with z = height(x, y).

    attrs: {attribute_name: f(x, y, z) -> float} stored per vertex for shaders.
    """
    nx, ny = len(xs), len(ys)
    verts, values = [], {k: [] for k in (attrs or {})}
    for y in ys:
        for x in xs:
            z = height(x, y)
            verts.append((x, y, z))
            for k, f in (attrs or {}).items():
                values[k].append(f(x, y, z))
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.shade_smooth()
    for k, v in values.items():
        _attr(mesh, k, v)
    obj = bpy.data.objects.new(name, mesh)
    if mat is not None:
        materials.assign(obj, mat)
    return shapes._link(obj)


def section_face(name, xs, plane_y, top, z_bottom, rows=90, thickness=0.01, mat=None, top_bias=2.2):
    """A vertical slab at y = plane_y whose top edge follows top(x): the cut face of a section.

    Rows are denser near the top edge. The slab extends `thickness` behind the plane so it
    is a closed solid (booleans can carve holes into it).
    """
    nx = len(xs)
    verts = []
    for j in range(rows + 1):
        t = 1 - (1 - j / rows) ** top_bias  # 0 at bottom, 1 at top, denser near top
        for x in xs:
            verts.append((x, plane_y, z_bottom + (top(x) - z_bottom) * t))
    faces = []
    for j in range(rows):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + nx, a + nx + 1, a + 1))  # normal toward -y (the camera side)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    shapes._link(obj)
    mod = obj.modifiers.new("Thickness", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = 1.0  # grow behind the plane (+y), away from the camera
    mod.use_even_offset = True
    shapes.bake(obj)
    if mat is not None:
        materials.assign(obj, mat)
    return obj


def set_point_attrs(obj, attrs):
    """(Re)compute per-vertex float attributes from world-ish coordinates: {name: f(x, y, z)}."""
    mesh = obj.data
    for k, f in attrs.items():
        if k in mesh.attributes:
            mesh.attributes.remove(mesh.attributes[k])
        _attr(mesh, k, [f(*v.co) for v in mesh.vertices])


def flip_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def height_image(name, x_range, y_range, size, ground, surface, cavity=None, cavity_box=None):
    """Bake a float image for matlib.heightmap_fields: R = ground(x, y), G = surface(x, y),
    B/A = bottom/top z of the cavity mesh object above (x, y) (found by vertical ray casts,
    only inside cavity_box ((x0, x1), (y0, y1))). Pixel centers span x_range, y_range."""
    from mathutils.bvhtree import BVHTree
    w, h = size
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    img.alpha_mode = "CHANNEL_PACKED"
    tree = None
    if cavity is not None:
        mw = cavity.matrix_world
        tree = BVHTree.FromPolygons([mw @ v.co for v in cavity.data.vertices],
                                    [p.vertices for p in cavity.data.polygons])
    px = []
    up = Vector((0, 0, 1))
    for j in range(h):
        y = y_range[0] + (y_range[1] - y_range[0]) * (j + 0.5) / h
        for i in range(w):
            x = x_range[0] + (x_range[1] - x_range[0]) * (i + 0.5) / w
            lo, hi = 1e4, -1e4
            if tree is not None and cavity_box[0][0] <= x <= cavity_box[0][1] and cavity_box[1][0] <= y <= cavity_box[1][1]:
                hit = tree.ray_cast(Vector((x, y, -50.0)), up)[0]
                if hit is not None:
                    top = tree.ray_cast(hit + up * 1e-4, up)[0]
                    if top is not None:
                        lo, hi = hit.z, top.z
            px += (ground(x, y), surface(x, y), lo, hi)
    img.pixels.foreach_set(px)
    try:
        img.pack()  # keep the pixels in the saved .blend
    except RuntimeError:
        pass
    return img


# ---------------------------------------------------------------- rocks

def rock_mesh(name, seed=0, size=(1.0, 0.8, 0.6), detail=3, roughness=0.35):
    """A unique irregular rock (unit-ish size, flattened base) as a mesh datablock."""
    rng = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=detail, radius=0.5)
    off = Vector((rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-50, 50)))
    # A few planar facets make it read as rock rather than a lumpy potato.
    planes = [(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.3, 1))).normalized(),
               rng.uniform(0.32, 0.42)) for _ in range(5)]
    for v in bm.verts:
        d = v.co.normalized()
        n = noise.fractal(d * 1.6 + off, 0.55, 2.0, 5, noise_basis="PERLIN_ORIGINAL")
        r = 0.5 * (1 + roughness * n)
        p = d * r
        for normal, dist in planes:
            h = p.dot(normal)
            if h > dist:
                p -= normal * (h - dist) * 0.85
        v.co = Vector((p.x * size[0], p.y * size[1], max(p.z, -0.18) * size[2]))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.shade_smooth()
    return mesh


def tuft_mesh(name, seed=0, blades=18, height=(0.12, 0.3), spread=0.06, lean=(1, 0.2)):
    """Dry sedge/grass tuft: thin tapered blades leaning downwind (lean = wind direction xy)."""
    rng = random.Random(seed)
    verts, faces = [], []
    wx, wy = lean
    for _ in range(blades):
        a = rng.uniform(0, 2 * math.pi)
        r = spread * math.sqrt(rng.random())
        bx, by = r * math.cos(a), r * math.sin(a)
        h = rng.uniform(*height)
        bend = rng.uniform(0.2, 0.7)
        face_a = rng.uniform(0, math.pi)
        w = rng.uniform(0.004, 0.008)
        segs = 4
        base = len(verts)
        for s in range(segs + 1):
            t = s / segs
            ox = bx + (wx * bend * t * t + 0.4 * math.cos(a) * t * 0.3) * h
            oy = by + (wy * bend * t * t + 0.4 * math.sin(a) * t * 0.3) * h
            oz = h * (t - 0.35 * bend * t * t)
            ww = w * (1 - t) + 0.0005
            dx, dy = math.cos(face_a) * ww, math.sin(face_a) * ww
            verts += [(ox - dx, oy - dy, oz), (ox + dx, oy + dy, oz)]
        for s in range(segs):
            i = base + 2 * s
            faces.append((i, i + 1, i + 3, i + 2))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.shade_smooth()
    return mesh


def scatter(name, meshes, points, mat, seed=0, scale=(0.5, 1.0), sink=0.3, tilt=0.2, parent=None):
    """Place linked copies of meshes at points [(x, y, z), ...] with random yaw/scale/tilt.

    sink: fraction of the object's height pushed below z (so rocks sit in the snow, not on it).
    """
    rng = random.Random(seed)
    objs = []
    for i, (x, y, z) in enumerate(points):
        mesh = meshes[rng.randrange(len(meshes))]
        obj = bpy.data.objects.new(f"{name}_{i}", mesh)
        s = rng.uniform(*scale)
        sz = s * rng.uniform(0.8, 1.2)
        obj.scale = (s, s * rng.uniform(0.8, 1.2), sz)
        h = max(v.co.z for v in mesh.vertices) - min(v.co.z for v in mesh.vertices)
        obj.location = (x, y, z - sink * h * sz)
        obj.rotation_euler = (rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), rng.uniform(0, 2 * math.pi))
        if not mesh.materials:
            mesh.materials.append(mat)
        shapes._link(obj, parent)
        objs.append(obj)
    return objs


def poisson_points(region, count, accept, seed=0, min_dist=0.5, tries=40):
    """Random (x, y) points in region ((x0, x1), (y0, y1)) where accept(x, y) is true, kept apart."""
    rng = random.Random(seed)
    pts = []
    (x0, x1), (y0, y1) = region
    for _ in range(count * tries):
        if len(pts) >= count:
            break
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if not accept(x, y, rng):
            continue
        if all((x - px) ** 2 + (y - py) ** 2 > min_dist ** 2 for px, py in pts):
            pts.append((x, y))
    return pts


# ---------------------------------------------------------------- sea ice

def pressure_ridge(name, points, mat, seed=0, height=(0.5, 1.8), block=(0.6, 1.6), density=1.4, base_z=0.0):
    """A jumbled line of tilted ice blocks along a polyline, merged into one mesh."""
    rng = random.Random(seed)
    bm = bmesh.new()
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        seg = math.hypot(bx - ax, by - ay)
        for k in range(int(seg * density)):
            t = rng.random()
            x, y = ax + (bx - ax) * t + rng.gauss(0, 1.2), ay + (by - ay) * t + rng.gauss(0, 1.2)
            sx, sy, sz = rng.uniform(*block), rng.uniform(*block) * 0.6, rng.uniform(0.15, 0.4)
            geom = bmesh.ops.create_cube(bm, size=1.0)
            vs = geom["verts"]
            bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=vs)
            rot = Matrix.Rotation(rng.uniform(0, math.pi), 4, "Z") @ Matrix.Rotation(
                rng.uniform(0.4, 1.3) * rng.choice((-1, 1)), 4, "X")
            bmesh.ops.transform(bm, matrix=rot, verts=vs)
            h = rng.uniform(*height) * (0.4 + 0.6 * math.sin(math.pi * t) ** 0.5)
            bmesh.ops.translate(bm, vec=(x, y, base_z + h * 0.5), verts=vs)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    materials.assign(obj, mat)
    return shapes._link(obj)
