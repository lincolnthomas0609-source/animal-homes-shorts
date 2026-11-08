"""Sculpted polar bear: one smooth merged body built from metaball elements.

Replaces the separate-ellipsoid look of creatures.polar_bear for close shots. The body is
described in body space (u = along the spine toward the nose, v = toward her left side,
w = toward her back; meters at size 1, adult female about 1.9 m nose to tail), then
posed and bent along a gentle C curve. Proportions follow the species: long neck, small
narrow head with a straight profile, rump as high as the shoulders, large paws, no
shoulder hump (unlike brown bears).

Poses (static; for walking shots keep using creatures.polar_bear):
- "sternal": lying on her belly, head resting on her forepaws, hind legs tucked, the
  body curved so head and rump come toward -Y (the camera side of a section).
- "side": lying on her left side, back to +Y, paws toward -Y.
"""

import math

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import anim, creatures, matlib, shapes

_META = 0.574  # a metaball element of radius 1 polygonizes to a surface of radius ~0.574

# (name, (u, v, w), semi-axes (a_u, a_v, a_w), pitch_deg); pitch > 0 tilts the u axis toward -w.
# Names starting with "Head", "Muzzle", "Ear" turn with head_turn.
POSES = {
    "sternal": dict(
        lift=0.27,
        torso=[
            ("Tail", (-0.90, 0.0, 0.10), (0.07, 0.05, 0.05), -20),
            ("Rump", (-0.56, 0.0, 0.03), (0.32, 0.27, 0.27), 0),
            ("Belly", (-0.16, 0.0, -0.02), (0.40, 0.30, 0.26), 0),
            ("Chest", (0.24, 0.0, -0.02), (0.32, 0.28, 0.27), 0),
            ("Withers", (0.42, 0.0, 0.06), (0.22, 0.21, 0.21), 5),
            ("Neck1", (0.60, 0.0, 0.00), (0.20, 0.17, 0.18), 22),
            ("Neck2", (0.75, 0.0, -0.06), (0.16, 0.14, 0.15), 18),
            ("Head", (0.90, 0.0, -0.07), (0.16, 0.125, 0.13), 6),
            ("Muzzle", (1.03, 0.0, -0.10), (0.12, 0.08, 0.075), 10),
        ],
        paired=[
            ("Ear", (0.84, 0.08, 0.05), (0.035, 0.028, 0.045), 0),
            ("ArmUpper", (0.46, 0.16, -0.15), (0.11, 0.10, 0.15), -10),
            ("ArmLower", (0.68, 0.13, -0.22), (0.17, 0.085, 0.065), 0),
            ("FrontPaw", (0.88, 0.12, -0.235), (0.13, 0.10, 0.05), 0),
            ("Haunch", (-0.52, 0.20, -0.06), (0.22, 0.12, 0.19), -25),
            ("Shin", (-0.40, 0.22, -0.20), (0.16, 0.08, 0.07), 0),
            ("HindPaw", (-0.22, 0.23, -0.235), (0.14, 0.09, 0.05), 0),
        ],
        features=[
            ("Nose", (1.15, 0.0, -0.09), (1.0, 0.0, 0.1), 0.034),
            ("EyeL", (0.97, 0.072, -0.01), (0.35, 0.75, 0.55), 0.016),
            ("EyeR", (0.97, -0.072, -0.01), (0.35, -0.75, 0.55), 0.016),
        ],
    ),
    "side": dict(
        lift=0.27,
        torso=[
            ("Tail", (-0.90, 0.0, 0.08), (0.07, 0.05, 0.05), -20),
            ("Rump", (-0.56, 0.0, 0.03), (0.32, 0.25, 0.28), 0),
            ("Belly", (-0.16, 0.0, -0.02), (0.40, 0.27, 0.29), 0),
            ("Chest", (0.24, 0.0, -0.03), (0.32, 0.25, 0.30), 0),
            ("Withers", (0.42, 0.0, 0.05), (0.22, 0.21, 0.23), 5),
            ("Neck1", (0.62, 0.0, 0.02), (0.20, 0.17, 0.19), 18),
            ("Neck2", (0.77, 0.0, -0.05), (0.16, 0.14, 0.15), 32),
            ("Head", (0.88, 0.0, -0.14), (0.16, 0.125, 0.13), 40),
            ("Muzzle", (0.97, 0.0, -0.25), (0.12, 0.08, 0.08), 52),
        ],
        paired=[
            ("Ear", (0.82, 0.08, -0.03), (0.035, 0.028, 0.045), 40),
            ("ArmUpper", (0.42, 0.13, -0.26), (0.12, 0.11, 0.20), -50),
            ("ArmLower", (0.60, 0.12, -0.40), (0.10, 0.09, 0.17), -80),
            ("FrontPaw", (0.76, 0.12, -0.44), (0.14, 0.095, 0.065), 0),
            ("Thigh", (-0.45, 0.14, -0.18), (0.19, 0.13, 0.25), -45),
            ("Shin", (-0.30, 0.13, -0.40), (0.10, 0.085, 0.15), 45),
            ("HindPaw", (-0.36, 0.13, -0.50), (0.15, 0.095, 0.065), 10),
        ],
        features=[
            ("Nose", (1.07, 0.0, -0.33), (0.6, 0.0, -0.8), 0.036),
            ("EyeL", (0.95, 0.07, -0.10), (0.3, 0.8, 0.4), 0.017),
            ("EyeR", (0.95, -0.07, -0.10), (0.3, -0.8, 0.4), 0.017),
        ],
    ),
}
_HEAD = ("Head", "Muzzle", "Ear", "Nose", "Eye")
_NECK_PIVOT = Vector((0.66, 0.0, 0.0))


def _pose(kind, curl_radius, head_turn_deg):
    """Return place(point, rotation) -> (posed position, quaternion) for body-space input."""
    side = Matrix.Rotation(math.radians(-90), 3, "X") if kind == "side" else Matrix.Identity(3)
    turn = Matrix.Rotation(math.radians(head_turn_deg), 3, "Z")

    def place(name, p, rot):
        p = Vector(p)
        if name.startswith(_HEAD):
            p = _NECK_PIVOT + turn @ (p - _NECK_PIVOT)
            rot = turn @ rot
        x, y, z = side @ p  # bend in the horizontal plane, curving toward -Y
        theta = x / curl_radius
        r = curl_radius + y
        pos = Vector((r * math.sin(theta), r * math.cos(theta) - curl_radius, z))
        q = Matrix.Rotation(-theta, 3, "Z") @ side @ rot
        return pos, q.to_quaternion()

    return place


def _juvenile(spec):
    """Young-cub proportions: bigger head, shorter muzzle, shorter body and limbs."""
    def adjust(items):
        out = []
        for n, (u, v, w), (a, b, c), p in items:
            if n.startswith(("Head", "Ear")):
                a, b, c = a * 1.35, b * 1.35, c * 1.35
            elif n.startswith("Muzzle"):
                u, a, b, c = u - 0.05, a * 0.85, b * 1.2, c * 1.2
            elif n.startswith(("Arm", "Front", "Haunch", "Shin", "Hind", "Thigh")):
                a, b, c = a * 0.85, b * 0.95, c * 0.85
            elif n in ("Rump", "Belly", "Chest"):
                u, a = u * 0.9, a * 0.9
            out.append((n, (u, v, w), (a, b, c), p))
        return out
    features = [(n, co, o, r * (1.6 if n.startswith("Eye") else 1.3)) for n, co, o, r in spec["features"]]
    return dict(spec, torso=adjust(spec["torso"]), paired=adjust(spec["paired"]), features=features)


def polar_bear_resting(name="Bear", size=1.0, pose="sternal", curl_radius=1.1, head_turn=0.0, fur=None,
                       resolution=0.018, mirror=False, juvenile=False):
    """Adult polar bear lying down. Returns (root, body).

    Put root on the floor under the spine's midpoint; she faces +X and her body curves
    toward -Y. head_turn (degrees, + toward her left/+Y, - toward -Y) turns the head.
    mirror=True puts the head toward -X. Animate breathe(body, ...) for a slow breath.
    """
    s = size
    spec = _juvenile(POSES[pose]) if juvenile else POSES[pose]
    fur = fur or matlib.fur(f"{name}_Fur")
    dark = matlib.glossy_dark(f"{name}_Dark")
    place = _pose(pose, curl_radius / s, head_turn)

    mb = bpy.data.metaballs.new(f"{name}_Meta")
    mb.resolution = mb.render_resolution = resolution / s
    mb.threshold = 0.6
    paired = []
    for n, (u, v, w), a, p in spec["paired"]:
        paired.append((n, (u, v, w), a, p))
        nudge = 0.04 if n in ("ArmLower", "FrontPaw") else 0.0
        paired.append((n + "R", (u + nudge, -v, w), a, p))
    for n, co, semi, pitch in spec["torso"] + paired:
        el = mb.elements.new(type="ELLIPSOID")
        pos, q = place(n, co, Matrix.Rotation(math.radians(pitch), 3, "Y"))
        el.co = pos
        el.rotation = q
        el.radius = 1.0
        el.size_x, el.size_y, el.size_z = (x / _META for x in semi)
        el.stiffness = 2.0
    meta = bpy.data.objects.new(f"{name}_MetaObj", mb)
    bpy.context.scene.collection.objects.link(meta)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(meta.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(meta)
    bpy.data.metaballs.remove(mb)
    mesh.name = f"{name}_Body"
    mesh.shade_smooth()

    root = shapes.empty(name)
    body = bpy.data.objects.new(f"{name}_Body", mesh)
    shapes._link(body, root)
    body.location = (0, 0, spec["lift"])
    mesh.materials.append(fur)
    smooth = body.modifiers.new("Smooth", "SMOOTH")
    smooth.factor, smooth.iterations = 0.6, 4

    # Eyes and nose: small glossy dark shapes, ray-cast onto the head surface.
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], [p.vertices for p in mesh.polygons])
    ident = Matrix.Identity(3)
    for label, co, outward, r in spec["features"]:
        target, _ = place(label, co, ident)
        tip, _ = place(label, tuple(c + 0.5 * o for c, o in zip(co, Vector(outward).normalized())), ident)
        direction = (target - tip).normalized()
        hit = tree.ray_cast(tip, direction)[0]
        pos = (hit if hit is not None else target) + direction * r * 0.45
        shapes.ellipsoid(f"{name}_{label}", (r, r, r), tuple(pos), dark, body, segments=16, rings=10)
    root.scale = (-s if mirror else s, s, s)
    return root, body


def polar_bear_curled(name="Bear", size=1.0, curl_radius=0.95, **kw):
    """Lying on her side, curled (see polar_bear_resting)."""
    return polar_bear_resting(name, size, pose="side", curl_radius=curl_radius, **kw)


# ---------------------------------------------------------------- walking bear

# Standing body (body space as above; w = 0 is the spine at body-center height).
STAND_TORSO = [
    ("Tail", (-0.90, 0.0, 0.10), (0.07, 0.05, 0.05), -20),
    ("Rump", (-0.55, 0.0, 0.04), (0.33, 0.27, 0.30), 0),
    ("Belly", (-0.15, 0.0, -0.01), (0.40, 0.28, 0.30), 0),
    ("Chest", (0.24, 0.0, 0.0), (0.33, 0.26, 0.31), 0),
    ("Withers", (0.42, 0.0, 0.06), (0.22, 0.21, 0.23), 5),
    ("Neck1", (0.60, 0.0, 0.05), (0.20, 0.17, 0.19), -8),
]
NECK_PIVOT = (0.60, 0.0, 0.05)
STAND_HEAD = [  # relative to body space; moved to the neck pivot when built
    ("Neck2", (0.76, 0.0, 0.05), (0.17, 0.145, 0.155), -5),
    ("Head", (0.92, 0.0, 0.03), (0.16, 0.125, 0.13), 10),
    ("Muzzle", (1.05, 0.0, -0.02), (0.12, 0.08, 0.075), 16),
    ("EarL", (0.86, 0.08, 0.15), (0.035, 0.028, 0.045), 0),
    ("EarR", (0.86, -0.08, 0.15), (0.035, 0.028, 0.045), 0),
]
STAND_FEATURES = [
    ("Nose", (1.16, 0.0, -0.03), (1.0, 0.0, 0.0), 0.034),
    ("EyeL", (0.99, 0.072, 0.08), (0.35, 0.75, 0.55), 0.016),
    ("EyeR", (0.99, -0.072, 0.08), (0.35, -0.75, 0.55), 0.016),
]
BODY_HEIGHT = 0.65  # spine height above the ground when standing (size 1)
# Legs hang from a pivot (shoulder/hip) at spine height; elements in pivot space.
FRONT_LEG = [("Upper", (0.0, 0.0, -0.14), (0.12, 0.11, 0.22), 0),
             ("Lower", (0.02, 0.0, -0.40), (0.085, 0.08, 0.20), 0),
             ("Paw", (0.07, 0.0, -0.60), (0.14, 0.095, 0.05), 0)]
HIND_LEG = [("Thigh", (-0.02, 0.0, -0.14), (0.17, 0.13, 0.25), 0),
            ("Lower", (0.01, 0.0, -0.42), (0.09, 0.08, 0.20), 0),
            ("Paw", (0.07, 0.0, -0.60), (0.15, 0.095, 0.05), 0)]
LEG_PIVOTS = [("FrontL", (0.44, 0.15, 0.0), FRONT_LEG), ("FrontR", (0.44, -0.15, 0.0), FRONT_LEG),
              ("HindL", (-0.50, 0.16, 0.02), HIND_LEG), ("HindR", (-0.50, -0.16, 0.02), HIND_LEG)]


def _meta_mesh(name, elements, s, resolution, offset=(0.0, 0.0, 0.0)):
    """Polygonize metaball ellipsoids [(name, center, semi-axes, pitch_deg)] into a smooth mesh."""
    mb = bpy.data.metaballs.new(f"{name}_Meta")
    mb.resolution = mb.render_resolution = resolution
    mb.threshold = 0.6
    for _, co, semi, pitch in elements:
        el = mb.elements.new(type="ELLIPSOID")
        el.co = tuple((c - o) * s for c, o in zip(co, offset))
        el.rotation = Matrix.Rotation(math.radians(pitch), 3, "Y").to_quaternion()
        el.radius = 1.0
        el.size_x, el.size_y, el.size_z = (x * s / _META for x in semi)
    meta = bpy.data.objects.new(f"{name}_MetaObj", mb)
    bpy.context.scene.collection.objects.link(meta)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(meta.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(meta)
    bpy.data.metaballs.remove(mb)
    mesh.name = name
    mesh.shade_smooth()
    return mesh


def _smooth_part(name, mesh, mat, parent):
    obj = bpy.data.objects.new(name, mesh)
    shapes._link(obj, parent)
    mesh.materials.append(mat)
    mod = obj.modifiers.new("Smooth", "SMOOTH")
    mod.factor, mod.iterations = 0.6, 3
    return obj


class WalkingBear(creatures.Quadruped):
    """The smooth bear split into torso, head and four legs, so it can walk.

    Same interface as creatures.Quadruped (root follows paths, rig bobs, hips swing),
    plus a neck pivot for head motion and a dig() action. Faces +X.
    """

    def __init__(self, name="WalkBear", size=1.0, fur=None, resolution=0.02):
        s = size
        fur = fur or matlib.fur(f"{name}_Fur")
        dark = matlib.glossy_dark(f"{name}_Dark")
        root = shapes.empty(name)
        rig = shapes.empty(f"{name}_Rig", (0, 0, 0), root)  # Quadruped poses offset this from 0
        body = shapes.empty(f"{name}_BodyCenter", (0, 0, BODY_HEIGHT * s), rig)
        res = resolution * max(s, 0.35)
        self.parts = [_smooth_part(f"{name}_Torso", _meta_mesh(f"{name}_Torso", STAND_TORSO, s, res), fur, body)]
        self.neck = shapes.empty(f"{name}_Neck", tuple(c * s for c in NECK_PIVOT), body)
        head_mesh = _meta_mesh(f"{name}_Head", STAND_HEAD, s, res * 0.8, offset=NECK_PIVOT)
        head = _smooth_part(f"{name}_Head", head_mesh, fur, self.neck)
        self.parts.append(head)
        tree = BVHTree.FromPolygons([v.co for v in head_mesh.vertices], [p.vertices for p in head_mesh.polygons])
        for label, co, outward, r in STAND_FEATURES:
            target = Vector([(c - o) * s for c, o in zip(co, NECK_PIVOT)])
            direction = -Vector(outward).normalized()
            hit = tree.ray_cast(target - direction * 0.5 * s, direction)[0]
            pos = (hit if hit is not None else target) + direction * r * s * 0.45
            self.parts.append(shapes.ellipsoid(f"{name}_{label}", (r * s,) * 3, tuple(pos), dark, head,
                                               segments=16, rings=10))
        hips = []
        for label, pivot, elements in LEG_PIVOTS:
            hip = shapes.empty(f"{name}_{label}Hip", tuple(c * s for c in pivot), body)
            self.parts.append(_smooth_part(f"{name}_{label}Leg", _meta_mesh(f"{name}_{label}Leg", elements, s, res),
                                           fur, hip))
            hips.append(hip)
        super().__init__(root, rig, hips, BODY_HEIGHT * s)
        self.size = s
        self.fur = fur

    def stride_cadence(self, distance, frames, amp=0.4):
        """Strides per second so the feet roughly keep pace with the ground (little sliding)."""
        leg = BODY_HEIGHT * self.size
        speed = distance / (frames / 30.0)
        return max(speed / (4 * leg * math.sin(amp)), 0.4)

    def walk(self, start, end, cadence=1.2, amp=0.4, nod=0.06):
        super().walk(start, end, cadence, amp)
        anim.hold_before(self.neck, "rotation_euler", start)
        for f in range(start, end + 1):
            fade = min(1.0, (f - start) / 6, (end - f) / 6)
            t = (f - start) / 30.0
            anim.key(self.neck, "rotation_euler", f, (0, nod * fade * math.sin(4 * math.pi * cadence * t), 0))

    def dig(self, start, end, cadence=2.4, amp=0.75):
        """Front paws scrape alternately with the head lowered; hind legs planted."""
        front = self.hips[:2]
        for hip in front:
            anim.hold_before(hip, "rotation_euler", start)
        anim.hold_before(self.neck, "rotation_euler", start)
        for f in range(start, end + 1):
            t = (f - start) / 30.0
            fade = min(1.0, (f - start) / 5, (end - f) / 5)
            for hip, phase in zip(front, (0.0, math.pi)):
                swing = -0.35 + amp * math.sin(2 * math.pi * cadence * t + phase)
                anim.key(hip, "rotation_euler", f, (0, swing * fade, 0))
            anim.key(self.neck, "rotation_euler", f, (0, 0.35 * fade, 0))

    def visible(self, toggles):
        """toggles: [(frame, bool), ...] in order. Instant show/hide of every part."""
        visibility(self.parts, toggles)


def visibility(objs, toggles):
    """Key hide_render (and viewport) on objs: [(frame, visible), ...] in chronological order."""
    for obj in objs:
        for frame, on in toggles:
            anim.key(obj, "hide_render", frame, not on)
            anim.key(obj, "hide_viewport", frame, not on)


def resting_parts(root):
    return [c for c in root.children_recursive if c.type == "MESH"]


def breathe(body, start, end, period=3.4, amount=0.018):
    """Slow sleeping breath: the ribcage swells slightly (scale about the spine)."""
    for f in range(start, end + 1):
        k = 0.5 - 0.5 * math.cos(2 * math.pi * (f - start) / (30 * period))
        anim.key(body, "scale", f, (1.0, 1.0 + amount * k, 1.0 + 0.6 * amount * k))
