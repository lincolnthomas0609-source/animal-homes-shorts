"""Atmosphere and explanation effects: snowfall, puffs, glows, and path highlights."""

import random

import bmesh
import bpy

from . import anim, materials, shapes


def snowfall(name, x, y, z_top, start, end, count=1500, flake=0.022, fall_seconds=4.0):
    """Particle snow falling from a rectangle at z_top. Returns the flake object.

    Animate the returned flake's scale to 0 to make all snow vanish instantly.
    """
    flake_obj = shapes.sphere(f"{name}_Flake", flake, materials.matte(f"{name}_FlakeMat", "#FFFFFF",
                              roughness=0.4, emission="#FFFFFF", emission_strength=0.6), segments=8, rings=6)
    flake_obj.location = (0, 0, -100)

    def plane(bm):
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bmesh.ops.scale(bm, vec=(x[1] - x[0], y[1] - y[0], 1), verts=bm.verts)

    emitter = shapes._mesh_object(f"{name}_Emitter", plane, smooth=False)
    emitter.location = ((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, z_top)
    emitter.rotation_euler = (3.14159, 0, 0)  # face down, so flakes start moving downward
    emitter.show_instancer_for_render = False
    emitter.show_instancer_for_viewport = False

    mod = emitter.modifiers.new("Snow", "PARTICLE_SYSTEM")
    ps = mod.particle_system.settings
    ps.count = count
    ps.frame_start = start - int(30 * fall_seconds)  # pre-roll so snow is already falling at `start`
    ps.frame_end = end
    cache = mod.particle_system.point_cache
    cache.frame_start = int(ps.frame_start)
    cache.frame_end = int(end + 30 * fall_seconds * 2)
    ps.use_scale_instance = True
    ps.lifetime = int(30 * fall_seconds * 1.6)
    ps.emit_from = "FACE"
    ps.normal_factor = 1.2
    ps.factor_random = 0.3
    ps.brownian_factor = 0.15
    ps.effector_weights.gravity = 0.05
    ps.render_type = "OBJECT"
    ps.instance_object = flake_obj
    ps.particle_size = 1.0
    ps.size_random = 0.6
    return flake_obj


def windblown_snow(name, x, y, z_top, start, end, count=600, flake=0.008, wind=(1.4, 0.0), fall=0.5,
                   preroll=6.0):
    """Sparse, small flakes drifting downwind (x, y: emitter extents; wind in m/s).

    Returns (flake_obj, alpha_socket). Fade all flakes out smoothly with
    tween(alpha_socket, "default_value", a, b, 1.0, 0.0) instead of popping them off.
    """
    mat = materials.matte(f"{name}_FlakeMat", "#FFFFFF", roughness=0.5, emission="#E8F0FF", emission_strength=0.4)
    mat.surface_render_method = "DITHERED"
    flake_obj = shapes.sphere(f"{name}_Flake", flake, mat, segments=6, rings=4)
    flake_obj.location = (0, 0, -100)

    def plane(bm):
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bmesh.ops.scale(bm, vec=(x[1] - x[0], y[1] - y[0], 1), verts=bm.verts)

    emitter = shapes._mesh_object(f"{name}_Emitter", plane, smooth=False)
    emitter.location = ((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, z_top)
    emitter.show_instancer_for_render = False
    emitter.show_instancer_for_viewport = False
    mod = emitter.modifiers.new("Snow", "PARTICLE_SYSTEM")
    ps = mod.particle_system.settings
    ps.count = count
    ps.frame_start = start - int(30 * preroll)
    ps.frame_end = end
    ps.lifetime = int(30 * preroll * 1.5)
    cache = mod.particle_system.point_cache
    cache.frame_start = int(ps.frame_start)
    cache.frame_end = int(end + 30 * preroll * 2)
    ps.emit_from = "FACE"
    ps.normal_factor = 0.0
    ps.object_align_factor = (wind[0], wind[1], -fall)
    ps.factor_random = 0.15
    ps.brownian_factor = 0.25
    ps.effector_weights.gravity = 0.0
    ps.render_type = "OBJECT"
    ps.instance_object = flake_obj
    ps.particle_size = 1.0
    ps.size_random = 0.7
    ps.use_rotations = True
    ps.rotation_factor_random = 1.0
    return flake_obj, mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"]


def warm_light(name, location, color=(1.0, 0.62, 0.32), energy=0.0, radius=0.3):
    data = bpy.data.lights.new(name, type="POINT")
    data.color = color
    data.energy = energy
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    return obj


def path_highlight(name, points, radius=0.04, color="#FFB347", strength=3.0):
    """A glowing tube along points that can draw itself on.

    tween(obj.data, "bevel_factor_end", start, end, 0.0, 1.0) draws it from the first point.
    """
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    curve.bevel_factor_end = 0.0
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    curve.materials.append(materials.matte(f"{name}_Mat", color, emission=color, emission_strength=strength))
    return obj


def puffs(name, origin, start, end, count=6, rise=1.2, size=0.08, color="#FFFFFF", seed=3):
    """Small soft puffs (breath, warm air) rising from origin, spaced across [start, end]."""
    rng = random.Random(seed)
    mat = materials.translucent(f"{name}_Mat", color, alpha=0.5, roughness=0.9)
    objs = []
    life = 36
    for i in range(count):
        f0 = start + round((end - start - life) * i / max(count - 1, 1))
        puff = shapes.sphere(f"{name}_{i}", size, mat, segments=12, rings=8)
        ox, oy, oz = origin
        a = (ox + rng.uniform(-0.05, 0.05), oy + rng.uniform(-0.05, 0.05), oz)
        b = (a[0] + rng.uniform(-0.15, 0.15), a[1], oz + rise)
        puff.scale = (0, 0, 0)
        anim.tween(puff, "location", f0, f0 + life, a, b, anim.ease_out)
        anim.tween(puff, "scale", f0, f0 + 8, (0, 0, 0), (1, 1, 1), anim.ease_out)
        anim.tween(puff, "scale", f0 + 8, f0 + life, (1, 1, 1), (2.2, 2.2, 2.2), anim.linear)
        anim.tween(puff, "scale", f0 + life, f0 + life + 1, (2.2, 2.2, 2.2), (0, 0, 0), anim.linear)
        objs.append(puff)
    return objs
