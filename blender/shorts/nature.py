"""Natural building materials: sticks, branches, and similar scattered pieces."""

import math
import random

import bpy
import bmesh
from mathutils import Vector

from . import materials, shapes

_STICK_MESH = None


def _stick_mesh():
    """Shared unit cylinder (radius 1, length 1 along Z). Sticks scale it per object."""
    global _STICK_MESH
    if _STICK_MESH is None or _STICK_MESH.name not in bpy.data.meshes:
        mesh = bpy.data.meshes.new("StickUnit")
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=1.0, radius2=0.85, depth=1.0)
        bm.to_mesh(mesh)
        bm.free()
        mesh.shade_smooth()
        mesh.materials.append(None)
        _STICK_MESH = mesh
    return _STICK_MESH


def stick_materials(prefix="Stick"):
    return [
        materials.matte(f"{prefix}A", "stick", roughness=0.8),
        materials.matte(f"{prefix}B", "stick_dark", roughness=0.8),
        materials.matte(f"{prefix}C", "stick_dark", roughness=0.8),
        materials.matte(f"{prefix}D", "stick_light", roughness=0.8),
    ]


def sticks_on_ellipsoid(name, center, radii, count, seed=1, length=(0.6, 1.4), thickness=(0.025, 0.05),
                        mats=None, parent=None, z_min=None, slope_bias=0.7, embed=0.4, keep=None):
    """Scatter sticks over the upper half of an ellipsoid, lying along its surface.

    slope_bias 0 gives random directions; 1 points every stick straight down the slope.
    embed is how far (in stick radii) each stick sinks into the surface.
    keep(position) -> bool can reject positions (e.g. to leave an opening).
    Returns stick objects; each has its resting scale stored in obj["rest_scale"].
    """
    rng = random.Random(seed)
    mats = mats or stick_materials(name)
    mesh = _stick_mesh()
    c = Vector(center)
    a, b, h = radii
    sticks = []
    attempts = 0
    while len(sticks) < count and attempts < count * 20:
        attempts += 1
        theta = rng.uniform(0, 2 * math.pi)
        uz = rng.uniform(0.0, 1.0)
        r = math.sqrt(1 - uz * uz)
        u = Vector((r * math.cos(theta), r * math.sin(theta), uz))
        pos = c + Vector((a * u.x, b * u.y, h * u.z))
        if z_min is not None and pos.z < z_min:
            continue
        if keep is not None and not keep(pos):
            continue
        normal = Vector((u.x / a, u.y / b, u.z / h)).normalized()
        down = Vector((0, 0, -1)) + normal * normal.z  # straight down, projected onto the surface
        down = down.normalized() if down.length > 1e-4 else Vector((1, 0, 0))
        rand = normal.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
        direction = (rand * (1 - slope_bias) + down * slope_bias).normalized()

        radius = rng.uniform(*thickness)
        obj = bpy.data.objects.new(f"{name}_{len(sticks):03d}", mesh)
        obj.location = pos + normal * radius * (1 - embed)
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction)
        obj.scale = (radius, radius, rng.uniform(*length))
        obj["rest_scale"] = tuple(obj.scale)
        shapes._link(obj, parent)
        # The mesh is shared, so each stick sets its color on the object instead.
        obj.material_slots[0].link = "OBJECT"
        obj.material_slots[0].material = rng.choice(mats)
        sticks.append(obj)
    return sticks
