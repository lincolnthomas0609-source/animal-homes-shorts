"""Primitive builders and cutaway helpers."""

import bpy
import bmesh

from . import materials


def _link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    return _link(obj, parent)


def _mesh_object(name, build, mat=None, parent=None, smooth=True):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    if mat is not None:
        materials.assign(obj, mat)
    return _link(obj, parent)


def sphere(name, radius=1.0, mat=None, parent=None, segments=96, rings=48):
    return _mesh_object(
        name,
        lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius),
        mat, parent,
    )


def ellipsoid(name, radii, location=(0, 0, 0), mat=None, parent=None, segments=64, rings=32):
    """A sphere scaled to radii (rx, ry, rz), with its origin at its center."""
    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
        bmesh.ops.scale(bm, vec=radii, verts=bm.verts)

    obj = _mesh_object(name, build, mat, parent)
    obj.location = location
    return obj


def shaft(name, radius, length, mat=None, parent=None, segments=24):
    """A straight vertical cylinder with its origin at the bottom center (scale Z to grow it upward)."""
    def build(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=length)
        bmesh.ops.translate(bm, vec=(0, 0, length / 2), verts=bm.verts)

    return _mesh_object(name, build, mat, parent, smooth=False)


def tube(name, points, radius, mat=None, parent=None, resolution=4):
    """A closed, capped tube through a list of 3D points (use anim.smooth_path for curves).

    Not for perfectly vertical straight paths (the bevel can't orient itself); use shaft().
    """
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    tmp = bpy.data.objects.new(name + "_curve", curve)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(curve)
    mesh.name = name
    mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    if mat is not None:
        materials.assign(obj, mat)
    return _link(obj, parent)


def bake(obj, single_material=True):
    """Apply all modifiers permanently. Use after static booleans so they aren't recomputed every frame.

    Booleans copy the cutter's material slots onto the result; single_material=True
    discards those so the whole object keeps only its original first material.
    """
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    old = obj.data
    obj.modifiers.clear()
    obj.data = mesh
    mesh.name = old.name
    if single_material and len(mesh.materials) > 1:
        first = mesh.materials[0]
        for poly in mesh.polygons:
            poly.material_index = 0
        mesh.materials.clear()
        mesh.materials.append(first)
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


def delete(*objs):
    for obj in objs:
        bpy.data.objects.remove(obj)


def box(name, size=(1, 1, 1), location=(0, 0, 0), mat=None, parent=None, bevel=0.0):
    def build(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=size, verts=bm.verts)
        bmesh.ops.translate(bm, vec=location, verts=bm.verts)

    obj = _mesh_object(name, build, mat, parent, smooth=False)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 4
        mod.harden_normals = True
    return obj


def cylinder(name, radius=1.0, depth=1.0, location=(0, 0, 0), mat=None, parent=None, segments=96):
    def build(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=depth)
        bmesh.ops.translate(bm, vec=location, verts=bm.verts)

    obj = _mesh_object(name, build, mat, parent)
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = min(radius, depth) * 0.04
    mod.segments = 3
    mod.limit_method = "ANGLE"
    mod.harden_normals = True
    return obj


def studio_floor(z=-1.4, color="background", world_strength=0.9, fade=(2.5, 10.0)):
    """A floor that catches shadows near the subject and blends into the world color.

    Beyond fade[1] units from the center, the floor renders as the exact world color,
    so there's no visible horizon line. world_strength must match lighting.world().
    """
    mat = bpy.data.materials.new("StudioFloor")
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = materials.color(color)
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.1

    flat = nodes.new("ShaderNodeEmission")
    flat.inputs["Color"].default_value = materials.color(color)
    flat.inputs["Strength"].default_value = world_strength

    coords = nodes.new("ShaderNodeTexCoord")
    dist = nodes.new("ShaderNodeVectorMath")
    dist.operation = "LENGTH"
    ramp = nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = fade
    mix = nodes.new("ShaderNodeMixShader")

    links.new(coords.outputs["Object"], dist.inputs[0])
    links.new(dist.outputs["Value"], ramp.inputs["Value"])
    links.new(ramp.outputs["Result"], mix.inputs["Fac"])
    links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    links.new(flat.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], nodes["Material Output"].inputs["Surface"])

    def build(bm):
        bmesh.ops.create_circle(bm, cap_ends=True, segments=64, radius=200)

    obj = _mesh_object("Floor", build, mat, smooth=False)
    obj.location = (0, 0, z)
    return obj


def shell(obj, thickness):
    """Turn a closed mesh into a hollow shell of the given inward thickness."""
    mod = obj.modifiers.new("Shell", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = -1.0
    mod.use_even_offset = True
    return mod


def cutter(name, size, location, parent=None):
    """An invisible box used as a boolean operand."""
    obj = box(name, size=size, location=(0, 0, 0), parent=parent)
    obj.location = location
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


def boolean(obj, operand, operation="DIFFERENCE"):
    mod = obj.modifiers.new(f"Cut_{operand.name}", "BOOLEAN")
    mod.operation = operation
    mod.object = operand
    mod.solver = "EXACT"
    return mod


def layered_sphere(name, layers, parent=None, wedge_size=None):
    """Concentric spherical layers with an optional removable wedge.

    layers: list of (layer_name, outer_radius, material), outermost first.
    The innermost layer is solid; the rest are hollow shells down to the next radius.

    If wedge_size is given, each layer is split into a body (with the wedge cut out)
    and a wedge piece. Both are returned, and the wedge pieces share one parent empty
    that can be animated to pull the wedge out and reveal the interior.
    Returns (bodies, wedge_pieces, wedge_rig).
    """
    root = parent
    bodies, pieces = [], []
    wedge_rig = None
    cut = piece_cut = None
    if wedge_size is not None:
        s = wedge_size
        corner = (s / 2, -s / 2, s / 2)
        cut = cutter(f"{name}_WedgeCutter", size=(s, s, s), location=corner, parent=root)
        wedge_rig = empty(f"{name}_Wedge", parent=root)
        # Booleans evaluate in world space, so the pieces need a cutter that travels with them.
        piece_cut = cutter(f"{name}_WedgePieceCutter", size=(s, s, s), location=corner, parent=wedge_rig)

    for i, (layer_name, radius, mat) in enumerate(layers):
        inner = layers[i + 1][1] if i + 1 < len(layers) else None
        body = sphere(f"{name}_{layer_name}", radius, mat, parent=root)
        if inner is not None:
            shell(body, radius - inner)
        bodies.append(body)
        if cut is not None:
            piece = sphere(f"{name}_{layer_name}_wedge", radius, mat, parent=wedge_rig)
            if inner is not None:
                shell(piece, radius - inner)
            boolean(piece, piece_cut, "INTERSECT")
            boolean(body, cut, "DIFFERENCE")
            pieces.append(piece)
    return bodies, pieces, wedge_rig
