"""Clean, matte stylized materials and a shared color palette."""

import bpy


def hex_rgb(h):
    """'#RRGGBB' -> linear RGBA tuple, so palette hex codes match on screen."""
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)


PALETTE = {
    "background": "#E9E4DA",
    "ink": "#2B2D42",
    "teal": "#2A9D8F",
    "cream": "#F1DCA7",
    "orange": "#F4A261",
    "red": "#E76F51",
    "yellow": "#FFD166",
    "blue": "#457B9D",
    "steel": "#A8B2BD",
    # Environments
    "water": "#5AA9D6",
    "water_deep": "#2F6F9F",
    "soil": "#9A6B45",
    "soil_dark": "#6E4A2F",
    "mud": "#7B5A3C",
    "stick": "#8F7457",
    "stick_dark": "#6A5440",
    "stick_light": "#B29A7C",
    "grass": "#86B86B",
    "snow": "#F3F6FA",
    "ice": "#CDE7F2",
    "bark": "#6F5440",
    "fur_brown": "#4E3424",
    "fur_dark": "#33231A",
}


def color(name_or_hex):
    return hex_rgb(PALETTE.get(name_or_hex, name_or_hex))


def matte(name, col, roughness=0.55, specular=0.3, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color(col)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = specular
    if emission:
        bsdf.inputs["Emission Color"].default_value = color(emission)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def translucent(name, col, alpha=0.45, roughness=0.08):
    """See-through material for water, ice, and glass. Alpha 0 is invisible, 1 is opaque."""
    mat = matte(name, col, roughness=roughness, specular=0.5)
    mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = alpha
    mat.surface_render_method = "DITHERED"
    return mat


def emission_socket(mat):
    """The Emission Strength input, for animating glows with anim.tween."""
    return mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj
