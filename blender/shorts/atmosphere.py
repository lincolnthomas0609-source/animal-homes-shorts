"""Skies and motivated outdoor lighting: a twilight gradient world and soft sun lamps."""

import math

import bpy
from mathutils import Vector

from .materials import color
from .matlib import Graph


def twilight_world(zenith="#0D1A33", upper="#1F3A63", horizon="#7F95B5", glow="#E6A88F",
                   glow_azimuth_deg=60.0, glow_width=0.55, stars=0.35, light="#5E79A3", light_strength=0.55):
    """Polar twilight sky: deep zenith, cool horizon, a warm glow band toward the hidden sun.

    The camera sees the painted sky; scene lighting comes from a uniform cool `light` color
    at `light_strength`, so the sky's look and the ambient level can be tuned separately.
    glow_azimuth_deg: compass direction of the glow, measured from +Y toward +X.
    Returns (world, horizon_rgba) so distant materials can be hazed toward the horizon.
    """
    w = bpy.data.worlds.new("TwilightWorld")
    bpy.context.scene.world = w
    g = Graph(w)
    g.nodes.clear()
    out = g.node("ShaderNodeOutputWorld")
    d = g.vmath("NORMALIZE", g.node("ShaderNodeTexCoord").outputs["Generated"])
    dx, dy, dz = g.xyz(d)
    sky = g.ramp(g.map_range(dz, -0.02, 0.9), [
        (0.0, horizon), (0.06, "#6B84A8"), (0.22, upper), (0.6, zenith), (1.0, zenith)])
    az = math.radians(glow_azimuth_deg)
    gdir = (math.sin(az), math.cos(az), 0.0)
    flat = g.vmath("NORMALIZE", g.node("ShaderNodeCombineXYZ", {"X": dx, "Y": dy, "Z": 0.0}))
    toward = g.math("MAXIMUM", g.vmath("DOT_PRODUCT", flat, gdir), 0.0)
    band = g.math("MULTIPLY", g.math("POWER", toward, 1.0 / glow_width),
                  g.map_range(dz, 0.25, -0.01, 0.0, 1.0, interp="SMOOTHSTEP"))
    sky = g.mix(band, sky, glow)
    if stars > 0:
        cells = g.voronoi(g.scale_vec(d, 140.0), scale=1.0, out="Distance")
        rnd = g.voronoi(g.scale_vec(d, 140.0), scale=1.0, out="Color")
        pick = g.math("GREATER_THAN", g.node("ShaderNodeRGBToBW", {"Color": rnd}).outputs[0], 0.82)
        star = g.math("MULTIPLY", g.math("MULTIPLY", g.map_range(cells, 0.045, 0.015), pick),
                      g.map_range(dz, 0.25, 0.55))
        sky = g.mix(g.math("MULTIPLY", star, stars), sky, (1, 1, 1, 1), "ADD")
    below = g.math("LESS_THAN", dz, -0.02)
    sky = g.mix(below, sky, "#55657A")
    seen = g.node("ShaderNodeBackground", {"Strength": 1.0})
    g.set(seen.inputs["Color"], sky)
    lit = g.node("ShaderNodeBackground", {"Color": light, "Strength": light_strength})
    is_cam = g.node("ShaderNodeLightPath").outputs["Is Camera Ray"]
    mix = g.node("ShaderNodeMixShader")
    g.set(mix.inputs[0], is_cam)
    g.links.new(lit.outputs[0], mix.inputs[1])
    g.links.new(seen.outputs[0], mix.inputs[2])
    g.links.new(mix.outputs[0], out.inputs["Surface"])
    return w, color(horizon)


WINTER = dict(zenith="#0D1A33", upper="#1F3A63", band="#6B84A8", horizon="#7F95B5", glow="#E6A88F",
              stars=0.35, light="#5E79A3", light_strength=0.6)
AUTUMN = dict(zenith="#24426E", upper="#4C6E9C", band="#8FA6C2", horizon="#C3CCD8", glow="#F0BE90",
              stars=0.0, light="#8199BB", light_strength=0.75)
SPRING = dict(zenith="#2F65A8", upper="#5D93CF", band="#A9C6E2", horizon="#DCE5EE", glow="#FFE0B5",
              stars=0.0, light="#9DB8D8", light_strength=0.95)


def _sky(g, d, dz, p, glow_azimuth_deg, glow_width):
    dx, dy = g.xyz(d)[0], g.xyz(d)[1]
    sky = g.ramp(g.map_range(dz, -0.02, 0.9), [
        (0.0, p["horizon"]), (0.06, p["band"]), (0.22, p["upper"]), (0.6, p["zenith"]), (1.0, p["zenith"])])
    az = math.radians(glow_azimuth_deg)
    flat = g.vmath("NORMALIZE", g.node("ShaderNodeCombineXYZ", {"X": dx, "Y": dy, "Z": 0.0}))
    toward = g.math("MAXIMUM", g.vmath("DOT_PRODUCT", flat, (math.sin(az), math.cos(az), 0.0)), 0.0)
    band = g.math("MULTIPLY", g.math("POWER", toward, 1.0 / glow_width),
                  g.map_range(dz, 0.25, -0.01, 0.0, 1.0, interp="SMOOTHSTEP"))
    return g.mix(band, sky, p["glow"])


def seasonal_world(palettes=(WINTER, AUTUMN, SPRING), glow_azimuth_deg=35.0, glow_width=0.55):
    """A sky that blends between palettes (first = base). Returns (world, factor_sockets,
    light_color_sockets): animate factor_sockets[i] (0-1) to blend toward palettes[i + 1].
    Like twilight_world, the camera sees the painted sky; lighting uses a flat color."""
    w = bpy.data.worlds.new("SeasonalWorld")
    bpy.context.scene.world = w
    g = Graph(w)
    g.nodes.clear()
    out = g.node("ShaderNodeOutputWorld")
    d = g.vmath("NORMALIZE", g.node("ShaderNodeTexCoord").outputs["Generated"])
    dz = g.xyz(d)[2]
    sky = _sky(g, d, dz, palettes[0], glow_azimuth_deg, glow_width)
    light = color(palettes[0]["light"])
    lit_col = g.node("ShaderNodeRGB")
    lit_col.outputs[0].default_value = light
    lit_col = lit_col.outputs[0]
    strength = palettes[0]["light_strength"]
    star_amount = palettes[0]["stars"]
    factors = []
    for p in palettes[1:]:
        f = g.node("ShaderNodeValue")
        f.outputs[0].default_value = 0.0
        fac = f.outputs[0]
        factors.append(fac)
        sky = g.mix(fac, sky, _sky(g, d, dz, p, glow_azimuth_deg, glow_width))
        lit_col = g.mix(fac, lit_col, p["light"])
        strength = g.mixf(fac, strength, p["light_strength"])
        star_amount = g.mixf(fac, star_amount, p["stars"])
    cells = g.voronoi(g.scale_vec(d, 140.0), scale=1.0, out=None)
    pick = g.math("GREATER_THAN", g.node("ShaderNodeRGBToBW", {"Color": cells.outputs["Color"]}).outputs[0], 0.82)
    star = g.math("MULTIPLY", g.math("MULTIPLY", g.map_range(cells.outputs["Distance"], 0.045, 0.015), pick),
                  g.map_range(dz, 0.25, 0.55))
    sky = g.mix(g.math("MULTIPLY", star, star_amount), sky, (1, 1, 1, 1), "ADD")
    sky = g.mix(g.math("LESS_THAN", dz, -0.02), sky, "#55657A")
    seen = g.node("ShaderNodeBackground", {"Strength": 1.0})
    g.set(seen.inputs["Color"], sky)
    lit = g.node("ShaderNodeBackground")
    g.set(lit.inputs["Color"], lit_col)
    g.set(lit.inputs["Strength"], strength)
    mix = g.node("ShaderNodeMixShader")
    g.set(mix.inputs[0], g.node("ShaderNodeLightPath").outputs["Is Camera Ray"])
    g.links.new(lit.outputs[0], mix.inputs[1])
    g.links.new(seen.outputs[0], mix.inputs[2])
    g.links.new(mix.outputs[0], out.inputs["Surface"])
    return w, factors


def sun_rotation(azimuth_deg, elevation_deg):
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    toward_light = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    return tuple((-toward_light).to_track_quat("-Z", "Y").to_euler())


def sun(name, azimuth_deg, elevation_deg, energy, col=(1, 1, 1), angle_deg=10.0):
    """A sun lamp shining from compass azimuth (0 = from +Y, 90 = from +X) and elevation."""
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.color = col
    data.angle = math.radians(angle_deg)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    toward_light = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    obj.rotation_euler = (-toward_light).to_track_quat("-Z", "Y").to_euler()
    return obj
