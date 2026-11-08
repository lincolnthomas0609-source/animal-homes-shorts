"""Pipeline test: 8-second vertical shot.

Checks object creation, materials, lighting, camera movement, animation,
a boolean cutaway reveal, and frame output for MP4 encoding.

Beats (seconds):
  0.0-0.8  layered sphere pops in, spinning into place
  0.0-5.0  camera orbits from front-left to front-right and pushes in
  3.0-5.2  a wedge pulls out and flies away, revealing the layers
  5.2-6.4  the core glows
  5.0-8.0  slow final push-in on the cutaway

Run:  tools/render.sh blender/scenes/test_01_cutaway.py preview
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from shorts import anim, core, lighting, materials, shapes  # noqa: E402
from shorts.anim import seconds as S, tween  # noqa: E402
from shorts.camera import OrbitCamera  # noqa: E402

NAME = "test_01_cutaway"
args = core.parse_args()
scene = core.setup_render(core.reset_scene(), seconds=8, quality=args.quality)

lighting.world("background", strength=0.9)
lighting.studio()
shapes.studio_floor(z=-1.4, world_strength=0.9)

core_mat = materials.matte("Core", "yellow", emission="yellow", emission_strength=0.0)
planet = shapes.empty("Planet")
_, _, wedge = shapes.layered_sphere(
    "Planet",
    [
        ("Shell", 1.00, materials.matte("Shell", "teal")),
        ("Layer2", 0.84, materials.matte("Layer2", "cream")),
        ("Layer3", 0.56, materials.matte("Layer3", "orange")),
        ("Core", 0.28, core_mat),
    ],
    parent=planet,
    wedge_size=1.3,
)

# Pop in and spin into place.
tween(planet, "scale", S(0), S(0.8), (0.001,) * 3, (1, 1, 1), anim.ease_out_back)
tween(planet, "rotation_euler", S(0), S(3.0), (0, 0, -1.2), (0, 0, 0), anim.ease_out)

# Wedge pulls out, pauses, then flies off frame.
tween(wedge, "location", S(3.0), S(4.0), (0, 0, 0), (0.75, -0.1, 0.6), anim.ease_out)
tween(wedge, "location", S(4.4), S(5.2), (0.75, -0.1, 0.6), (4.0, 0.8, 4.5), anim.ease_in)
tween(wedge, "scale", S(4.4), S(5.2), (1, 1, 1), (0.4, 0.4, 0.4), anim.ease_in)

# Core lights up. Layers fit flush, so scaling the core would make it clip through Layer3.
tween(materials.emission_socket(core_mat), "default_value", S(5.2), S(6.4), 0.0, 1.8, anim.ease_in_out)

# Camera: wide orbit and push-in, then a slow drift closer.
cam = OrbitCamera(distance=9.5, height=1.0, angle_deg=-25)
tween(cam.rig, "rotation_euler", S(0), S(5.0), cam.angle(-25), cam.angle(40))
tween(cam.camera, "location", S(0), S(5.0), cam.place(9.5, 1.0), cam.place(6.6, 2.4))
tween(cam.rig, "rotation_euler", S(5.0), S(8.0), cam.angle(40), cam.angle(48), anim.ease_out)
tween(cam.camera, "location", S(5.0), S(8.0), cam.place(6.6, 2.4), cam.place(5.4, 1.9), anim.ease_out)
tween(cam.aim, "location", S(0), S(8.0), (0, 0, 0), (0, 0, 0.15))

core.finish(scene, NAME, args)
