"""Section cuts: slice away everything in front of a vertical plane to show the inside."""

import bpy

from . import anim, shapes


def section_material(mat, darken=0.78):
    """A darker copy of mat for cut faces, so cross-sections read clearly against outer surfaces."""
    sec = mat.copy()
    sec.name = mat.name + "_Section"
    bsdf = sec.node_tree.nodes["Principled BSDF"]
    r, g, b, a = bsdf.inputs["Base Color"].default_value
    bsdf.inputs["Base Color"].default_value = (r * darken, g * darken, b * darken, a)
    return sec


class SectionCut:
    """Removes the camera side (y < plane_y) of every target, sweeping from top to bottom.

    Solid targets are cut with a boolean, so their cut faces show as solid cross-sections.
    Cut faces use material slot 1 of each target; if a target has no slot 1, a darker copy
    of its material is added (pass section_colors={obj: material} to choose your own).
    Scattered pieces (sticks, leaves) are too numerous for booleans; remove_scattered()
    shrinks the ones in front of the plane as the cut passes their height.

    Don't put plane_y exactly on a symmetry plane of the targets (e.g. y=0 through a
    sphere's poles): coplanar edges make the exact boolean produce broken cut faces.
    Offset it by a few millimeters instead.
    """

    def __init__(self, targets, plane_y=0.0, extent=30.0, height=12.0, section_colors=None):
        self.plane_y = plane_y
        self.height = height
        self._cy = plane_y - extent / 2
        self.cutter = shapes.cutter("SectionCutter", size=(extent, extent, height),
                                    location=(0, self._cy, 1000))
        # Boolean "index" material mode maps the cutter's material index onto the target's slots.
        self.cutter.data.materials.append(None)
        self.cutter.data.materials.append(None)
        for poly in self.cutter.data.polygons:
            poly.material_index = 1

        section_colors = section_colors or {}
        for target in targets:
            mats = target.data.materials
            # Earlier booleans can leave an empty slot 1, so fill it rather than only appending.
            if len(mats) < 2 or mats[1] is None:
                sec = section_colors.get(target) or section_material(mats[0])
                if len(mats) < 2:
                    mats.append(sec)
                else:
                    mats[1] = sec
            mod = shapes.boolean(target, self.cutter)
            mod.material_mode = "INDEX"
        self._bottom = {}

    def move(self, start, end, z_from, z_to, ease=anim.ease_in_out):
        """Move the cut's lower edge from z_from to z_to.

        Above everything = closed (nothing removed); below everything = fully open.
        Moving down opens the cut from the top; moving up closes it from the bottom.
        """
        h = self.height
        anim.tween(self.cutter, "location", start, end,
                   (0, self._cy, z_from + h / 2), (0, self._cy, z_to + h / 2), ease)
        span = max(end - start, 1)
        self._bottom = {f: z_from + (z_to - z_from) * ease((f - start) / span) for f in range(start, end + 1)}

    def sweep(self, start, end, z_top, z_bottom, ease=anim.ease_in_out):
        """Open the cut from the top down: lower edge goes from z_top (above everything) to z_bottom."""
        self.move(start, end, z_top, z_bottom, ease)

    def remove_scattered(self, objs, shrink_frames=6):
        bpy.context.view_layer.update()
        for obj in objs:
            if obj.matrix_world.translation.y >= self.plane_y:
                continue
            z = obj.matrix_world.translation.z
            hit = next((f for f, bottom in sorted(self._bottom.items()) if bottom <= z), None)
            if hit is None:
                continue
            rest = tuple(obj.get("rest_scale", obj.scale[:]))
            anim.tween(obj, "scale", hit, hit + shrink_frames, rest, (0.0, 0.0, 0.0), anim.ease_in)
