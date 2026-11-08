"""Diorama blocks: stacked ground layers and water, cut as a rectangular slab.

The series look: each home sits inside a floating block of its environment,
which a SectionCut (see cutaway.py) slices open to reveal the inside.
"""

from . import materials, shapes


def strata(name, x, y, layers, parent=None, bevel=0.02):
    """Stacked horizontal layers (soil, rock, snow...).

    x, y: (min, max) extents. layers: list of (layer_name, z_bottom, z_top, material).
    Returns the layer objects, bottom to top as given.
    """
    objs = []
    cx, cy = (x[0] + x[1]) / 2, (y[0] + y[1]) / 2
    for layer_name, z0, z1, mat in layers:
        objs.append(shapes.box(
            f"{name}_{layer_name}",
            size=(x[1] - x[0], y[1] - y[0], z1 - z0),
            location=(cx, cy, (z0 + z1) / 2),
            mat=mat, parent=parent, bevel=bevel,
        ))
    return objs


def water_block(name, x, y, z_bottom, z_top, mat=None, parent=None, exclude=(), gap=1.01):
    """A translucent water volume with solid objects (lodges, rocks) hollowed out of it.

    Each object in exclude is subtracted using a copy scaled by gap, so the water's
    inner surface never sits exactly on the object's surface (which would flicker).
    """
    mat = mat or materials.translucent(f"{name}_Water", "water", alpha=0.42)
    water = shapes.box(
        name,
        size=(x[1] - x[0], y[1] - y[0], z_top - z_bottom),
        location=((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (z_bottom + z_top) / 2),
        mat=mat, parent=parent,
    )
    copies = []
    for solid in exclude:
        copy = solid.copy()
        copy.modifiers.clear()
        shapes._link(copy)
        copy.scale = [s * gap for s in solid.scale]
        copy.hide_render = True
        shapes.boolean(water, copy)
        copies.append(copy)
    if copies:
        shapes.bake(water)
        shapes.delete(*copies)
    return water
