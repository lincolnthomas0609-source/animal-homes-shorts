"""Cutaway reveal test: a beaver lodge in a pond diorama block.

Illustrative geometry only, not to scale. The pilot's researched version replaces this.

Beats (seconds):
  0.0-2.0  the lodge rises stick by stick out of the pond
  0.0-3.0  camera orbits from front-left toward the front
  3.0-4.4  section cut sweeps down, revealing the dry chamber and underwater tunnel
  4.8-7.6  a beaver swims in through the tunnel and climbs into the chamber
  3.0-8.0  camera pushes in on the chamber and tunnel

Run:  tools/render.sh blender/scenes/test_02_beaver_lodge.py draft
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from shorts import anim, core, creatures, lighting, materials, nature, shapes, terrain  # noqa: E402
from shorts.anim import seconds as S, tween  # noqa: E402
from shorts.camera import OrbitCamera  # noqa: E402
from shorts.cutaway import SectionCut  # noqa: E402

NAME = "test_02_beaver_lodge"
args = core.parse_args()
scene = core.setup_render(core.reset_scene(), seconds=8, quality=args.quality)

WATER_TOP, POND_BED, BLOCK_BOTTOM = 0.0, -1.2, -2.0
BLOCK_X, BLOCK_Y = (-3.0, 3.0), (-2.5, 2.5)
LODGE_RADII = (2.3, 2.3, 2.6)  # centered on the pond bed, so 1.4 above the water
CHAMBER_CENTER, CHAMBER_RADII = (0.0, 0.0, 0.45), (0.95, 0.95, 0.42)
TUNNEL = anim.smooth_path([(0.35, 0, 0.28), (0.8, 0, -0.15), (1.3, 0, -0.6), (2.0, 0, -0.85), (2.8, 0, -0.9)])

lighting.world("background", strength=0.9)
lighting.studio(target=(0, 0, -0.3), scale=2.2)
shapes.studio_floor(z=BLOCK_BOTTOM - 0.8, world_strength=0.9)

# Lodge: a mud mound with a flat base, a hollow chamber, and a tunnel.
mud = materials.matte("Mud", "mud", roughness=0.85)
lodge = shapes.ellipsoid("Lodge", LODGE_RADII, (0, 0, POND_BED), mud)
below = shapes.cutter("BelowBed", size=(10, 10, 4), location=(0, 0, POND_BED - 2))
shapes.boolean(lodge, below)
shapes.bake(lodge)

chamber = shapes.ellipsoid("ChamberCut", CHAMBER_RADII, CHAMBER_CENTER)
tunnel = shapes.tube("TunnelCut", TUNNEL, radius=0.2)
shapes.boolean(lodge, chamber)
shapes.boolean(lodge, tunnel)
shapes.bake(lodge)
shapes.delete(below, chamber, tunnel)

# The water overlaps the lodge: the opaque mud hides it, and wherever the lodge is
# hollow below the surface (the tunnel), the water shows through in the cutaway.
water = terrain.water_block("Pond", BLOCK_X, BLOCK_Y, POND_BED, WATER_TOP)

ground = terrain.strata("Ground", BLOCK_X, BLOCK_Y, [
    ("Subsoil", BLOCK_BOTTOM, POND_BED - 0.25, materials.matte("Subsoil", "soil", roughness=0.9)),
    ("Silt", POND_BED - 0.25, POND_BED, materials.matte("Silt", "soil_dark", roughness=0.9)),
])

sticks = nature.sticks_on_ellipsoid(
    "Stick", (0, 0, POND_BED), LODGE_RADII, count=520, seed=7,
    length=(0.35, 0.8), thickness=(0.03, 0.05), embed=1.2,
)

# Build-up: the mound grows from the pond bed, sticks appear as it reaches their height.
build_end = S(2.0)
tween(lodge, "scale", 1, build_end, (1, 1, 0.02), (1, 1, 1), anim.ease_out)
lodge_height = LODGE_RADII[2]
for stick in sticks:
    u = min(max((stick.location.z - POND_BED) / lodge_height, 0.0), 1.0)
    f = 1 + round((build_end - 1) * (1 - (1 - u) ** (1 / 3)))  # inverse of ease_out
    tween(stick, "scale", f, f + 8, (0, 0, 0), stick["rest_scale"], anim.ease_out_back)

# Section cut reveal.
cut = SectionCut([lodge, *ground], plane_y=0.0, section_colors={
    lodge: materials.matte("MudSection", "#A27B55", roughness=0.9),
})
# Cut the water 1 cm further back so its cut face never fights with the lodge's.
water_cut = SectionCut([water], plane_y=0.01)
for c in (cut, water_cut):
    c.sweep(S(3.0), S(4.4), z_top=1.8, z_bottom=BLOCK_BOTTOM - 0.2)
cut.remove_scattered(sticks)

# Beaver swims in from open water, up the tunnel, into the chamber.
beaver = creatures.beaver(size=0.85)
beaver.scale = (0, 0, 0)
swim = [(2.85, 0, -0.85)] + TUNNEL[::-1] + [(-0.1, 0, 0.2)]
tween(beaver, "scale", S(4.6), S(4.9), (0, 0, 0), (1, 1, 1), anim.ease_out)
anim.follow_path(beaver, anim.smooth_path(swim[::4] + [swim[-1]], 8), S(4.6), S(7.6), anim.ease_in_out)

# Camera.
cam = OrbitCamera(target=(0, 0, -0.3), distance=14, height=4.5, angle_deg=-35, lens=35)
tween(cam.rig, "rotation_euler", 1, S(3.0), cam.angle(-35), cam.angle(-8), anim.ease_out)
tween(cam.camera, "location", 1, S(3.0), cam.place(14, 4.5), cam.place(12, 3.2), anim.ease_out)
tween(cam.rig, "rotation_euler", S(3.0), S(8.0), cam.angle(-8), cam.angle(12), anim.ease_in_out)
tween(cam.camera, "location", S(3.0), S(8.0), cam.place(12, 3.2), cam.place(9.0, 1.8), anim.ease_in_out)
tween(cam.aim, "location", S(3.0), S(8.0), (0, 0, -0.3), (0.6, 0, -0.1), anim.ease_in_out)

core.finish(scene, NAME, args)
