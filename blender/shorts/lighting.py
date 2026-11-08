"""Soft studio lighting: a flat-colored world plus key, fill, and rim area lights."""

import math

import bpy
from mathutils import Vector

from . import materials


def world(color="background", strength=1.0):
    w = bpy.data.worlds.new("World")
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = materials.color(color)
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = w
    return w


def area_light(name, location, target=(0, 0, 0), energy=300, size=3.0, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.size = size
    data.shape = "DISK"
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    direction = Vector(target) - Vector(location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def studio(target=(0, 0, 0), scale=1.0):
    """Three-point lighting sized for a subject roughly 2 units across.

    scale multiplies light distances; energy is adjusted to keep brightness constant.
    """
    s = scale
    tx, ty, tz = target
    key = area_light("Key", (tx - 4 * s, ty - 4 * s, tz + 5 * s), target, energy=900 * s * s, size=5 * s,
                     color=(1.0, 0.96, 0.9))
    fill = area_light("Fill", (tx + 5 * s, ty - 3 * s, tz + 1.5 * s), target, energy=250 * s * s, size=6 * s,
                      color=(0.88, 0.93, 1.0))
    rim = area_light("Rim", (tx + 1 * s, ty + 5 * s, tz + 4 * s), target, energy=600 * s * s, size=3 * s)
    return key, fill, rim
