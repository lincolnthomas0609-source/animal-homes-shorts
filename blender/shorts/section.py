"""Shader-driven section cuts for large environments.

cutaway.SectionCut recomputes exact booleans on every frame, which is slow on dense
terrain. ShaderSection instead clips materials against a controller empty and pairs it
with a static, pre-built cut-face mesh (see landscape.section_face), so the cut can sweep
through a whole landscape at render speed.

    sec = ShaderSection(plane_y=-0.12, z_closed=4.0)
    sec.clip(snow_mat, den_wall_mat, rock_mat)        # hidden in front of the plane once cut
    glint = sec.face(section_mat)                      # cut face, visible only where cut
    sec.sweep([(575, 4.0), (620, -0.5), (650, -9.0)])  # lower edge height over time
"""

import bpy

from . import anim, matlib, shapes


class ShaderSection:
    def __init__(self, plane_y, z_closed, name="SectionCtl"):
        self.plane_y = plane_y
        self.ctl = shapes.empty(name, (0.0, plane_y, z_closed))
        self.ctl.empty_display_type = "ARROWS"
        self.glints = []

    def clip(self, *mats):
        for mat in mats:
            matlib.add_section_clip(mat, self.ctl, "keep_back")

    def face(self, mat):
        glint = matlib.add_section_clip(mat, self.ctl, "face")
        self.glints.append(glint)
        return glint

    def sweep(self, keys, glint=(0.0, 0.0)):
        """keys: [(frame, lower_edge_z), ...]; smooth through the keys (no stops in between).

        glint: (peak strength, fade frames) of the glowing line at the moving edge.
        """
        anim.smooth_keys(self.ctl, "location", [(f, (0.0, self.plane_y, z)) for f, z in keys])
        peak, fade = glint
        if peak > 0:
            a, b = keys[0][0], keys[-1][0]
            for socket in self.glints:
                anim.smooth_keys(socket, "default_value",
                                 [(a, 0.0), (a + 8, peak), (b - fade, peak * 0.8), (b, 0.0)])
