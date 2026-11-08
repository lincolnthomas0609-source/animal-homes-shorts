"""Episode: How a polar bear maternity den works.

Animation beats are keyed to the narration timing file, one beat per script line
(see scripts/ep02_polar_bear_den.txt). Re-voice the script and re-render; the
animation follows the new timing.

Geometry is illustrative: proportions follow Harington (1968) averages loosely
(entrance ~2 m long, room ~2 x 1.5 x 1 m) but are simplified.

Run:  tools/render.sh blender/scenes/ep02_polar_bear_den.py preview
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bpy  # noqa: E402

from shorts import anim, core, creatures, effects, lighting, materials, shapes, terrain  # noqa: E402
from shorts.anim import tween  # noqa: E402
from shorts.camera import OrbitCamera  # noqa: E402
from shorts.cutaway import SectionCut  # noqa: E402

NAME = "ep02_polar_bear_den"
TIMING = os.path.join(core.ROOT, "audio", "narration", f"{NAME}.timing.json")
TAIL_SECONDS = 2.0

args = core.parse_args()
L = anim.load_timing(TIMING)
assert len(L) == 12, f"scene expects 12 narration lines, got {len(L)}"
f0 = lambda i: L[i - 1]["f0"]  # first frame of narration line i (1-based)
f1 = lambda i: L[i - 1]["f1"]
END = anim.seconds(L[-1]["end"] + TAIL_SECONDS)
scene = core.setup_render(core.reset_scene(), seconds=L[-1]["end"] + TAIL_SECONDS, quality=args.quality)
cues = []  # sound effect cues: (name, seconds, gain_db)
cue = lambda name, frame, gain=0.0: cues.append({"name": name, "time": round((frame - 1) / 30, 3), "gain": gain})

# ---------------------------------------------------------------- layout
BLOCK_X, BLOCK_Y = (-3.6, 4.6), (-2.6, 2.6)
BLOCK_BOTTOM, GROUND_TOP, SNOW_TOP = -2.3, -1.6, -1.45
DRIFT_CENTER, DRIFT_RADII = (0.0, 0.4, GROUND_TOP), (3.0, 2.4, 2.25)
ROOM_CENTER, ROOM_RADII = (-0.5, 0.0, -0.78), (1.05, 0.78, 0.52)
ROOM_FLOOR = ROOM_CENTER[2] - ROOM_RADII[2]
TUNNEL_R = 0.37
TUNNEL = anim.smooth_path([(0.3, 0, -0.95), (0.9, 0, -1.05), (1.6, 0, -1.12), (2.3, 0, -1.16), (3.25, 0, -1.18)])
ENTRANCE = (2.95, 0.0, -1.18)
AIRHOLE_BASE = (-0.75, 0.0, -0.31)  # just below the ceiling, so the short cutter already touches it

# Winter is the polar night: a deep blue backdrop that brightens in spring.
WINTER_SKY, SPRING_SKY = "#2B405C", "#8DB6D8"
world = lighting.world(WINTER_SKY, strength=1.0)
key, fill, rim = lighting.studio(target=(0.4, 0, -1.0), scale=2.4)
floor = shapes.studio_floor(z=BLOCK_BOTTOM - 0.9, color=WINTER_SKY, world_strength=1.0)
sky_sockets = [
    world.node_tree.nodes["Background"].inputs["Color"],
    floor.active_material.node_tree.nodes["Emission"].inputs["Color"],
    floor.active_material.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
]

snow = materials.matte("Snow", "#EEF3F8", roughness=0.5, specular=0.35)
snow_section = materials.matte("SnowSection", "#A8C1DA", roughness=0.7)
ground_mat = materials.matte("FrozenGround", "#5E4B3C", roughness=0.9)

# Snowdrift: an ellipsoid dome sitting on the ground, trimmed to the block.
drift = shapes.ellipsoid("Drift", DRIFT_RADII, DRIFT_CENTER, snow, segments=96, rings=48)
below = shapes.cutter("BelowGround", (20, 20, 4), (0, 0, GROUND_TOP - 2))
back = shapes.cutter("BehindBlock", (20, 4, 10), (0, BLOCK_Y[1] + 2, 0))
for c in (below, back):
    shapes.boolean(drift, c)
shapes.bake(drift)

room = shapes.ellipsoid("RoomCut", ROOM_RADII, ROOM_CENTER)
tunnel = shapes.tube("TunnelCut", TUNNEL, TUNNEL_R)
shapes.boolean(drift, room)
shapes.boolean(drift, tunnel)
shapes.bake(drift)
shapes.delete(below, back, room, tunnel)

# The air hole cutter starts hidden inside the room and grows up through the roof.
airhole = shapes.shaft("AirHoleCut", 0.09, 1.4)
airhole.location = AIRHOLE_BASE
airhole.scale = (1, 1, 0.05)
airhole.hide_render = True
airhole.display_type = "WIRE"
# A cutter floating inside the empty room breaks the exact boolean, so the modifier stays
# off until the hole is dug (see beat 8).
airhole_mod = shapes.boolean(drift, airhole)

ground = terrain.strata("Ground", BLOCK_X, BLOCK_Y, [
    ("Frozen", BLOCK_BOTTOM, GROUND_TOP, ground_mat),
    ("SnowLayer", GROUND_TOP, SNOW_TOP, snow),
])
plug = shapes.ellipsoid("EntrancePlug", (0.42, 0.55, 0.45), ENTRANCE, snow)

cut = SectionCut([drift, *ground, plug], plane_y=-0.007, section_colors={
    drift: snow_section, ground[1]: snow_section, plug: snow_section,
})
Z_OPEN, Z_CLOSED = BLOCK_BOTTOM - 0.3, 1.2

den_light = effects.warm_light("DenGlow", (-0.3, -0.35, -0.75), color=(1.0, 0.5, 0.2), energy=0.0, radius=0.5)
sun_data = bpy.data.lights.new("SpringSun", "SUN")
sun_data.energy = 0.0
sun_data.color = (1.0, 0.9, 0.75)
sun_data.angle = math.radians(8)
sun = bpy.data.objects.new("SpringSun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), 0, math.radians(35))

# ---------------------------------------------------------------- animals
FUR = "#F2E6CC"  # polar bear fur reads creamy against snow
mom = creatures.polar_bear("Mom", size=0.78, fur_color=FUR)
cubs = [creatures.polar_bear(f"Cub{i}", size=0.14, fur_color=FUR) for i in (1, 2)]
male = creatures.polar_bear("Male", size=0.95, fur_color=FUR)

MOM_LIE = (-0.35, 0.15, ROOM_FLOOR)
CUB_SPOTS = [(-0.62, -0.3, ROOM_FLOOR), (-0.25, -0.3, ROOM_FLOOR)]  # in front of her chest and belly
for bear in (mom, *cubs):
    bear.set_pose_lying()
    bear.root.rotation_euler = (0, 0, math.pi)
mom.root.location = MOM_LIE
# Key the starting placement at frame 1; otherwise the first keys set later (spring walk-out)
# would be held for every earlier frame.
tween(mom.root, "rotation_euler", 1, 2, (0, 0, math.pi), (0, 0, math.pi), anim.linear)
for cub, spot in zip(cubs, CUB_SPOTS):
    tween(cub.root, "location", 1, 2, spot, spot, anim.linear)
    tween(cub.root, "rotation_euler", 1, 2, (0, 0, -math.pi * 0.35), (0, 0, -math.pi * 0.35), anim.linear)

# ---------------------------------------------------------------- beats
# 1-2. Hook: inside the open den, a tiny cub beside its mother. Pull back to the blizzard.
cut.move(1, 2, Z_OPEN, Z_OPEN)
tween(den_light.data, "energy", 1, 2, 60.0, 60.0)
cubs[0].hide_until(8)
tween(cubs[1].root, "scale", 1, 2, (0, 0, 0), (0, 0, 0))
cue("pop", 8)
flake = effects.snowfall("Snow", (BLOCK_X[0], BLOCK_X[1]), (-2.6, -0.45), 3.5, 1, f0(6), count=2200, flake=0.014)
cue("whoosh", f0(2))

# 3. "So its first home is a snowdrift": the cut closes, rewinding to autumn.
close_a, close_b = f0(3) + 4, f1(3)
cut.move(close_a, close_b, Z_OPEN, Z_CLOSED)
tween(den_light.data, "energy", close_a, close_b, 60.0, 0.0)
cue("close", close_a)
hidden = close_b + 1
tween(mom.root, "location", hidden - 1, hidden, MOM_LIE, MOM_LIE, anim.linear)
tween(mom.root, "scale", hidden, hidden + 1, (1, 1, 1), (0, 0, 0), anim.linear)
tween(cubs[0].root, "scale", hidden, hidden + 1, (1, 1, 1), (0, 0, 0), anim.linear)
mom.stand(hidden + 1, hidden + 3)

# 4. Autumn: she walks to the drift, digs in, and crawls through the tunnel.
outside = (4.3, 0.3, SNOW_TOP)
at_door = (ENTRANCE[0] + 0.55, 0.0, SNOW_TOP)
walk_a, walk_b = f0(4), f0(4) + 60
tween(mom.root, "scale", walk_a - 1, walk_a + 6, (0, 0, 0), (1, 1, 1), anim.ease_out_back)
anim.follow_path(mom.root, [outside, at_door], walk_a, walk_b, anim.linear)
mom.walk(walk_a, walk_b)
dig_a, dig_b = walk_b + 4, walk_b + 28
tween(plug, "scale", dig_a, dig_b, (1, 1, 1), (0.001, 0.001, 0.001), anim.ease_in)
effects.puffs("DigSpray", (ENTRANCE[0] + 0.3, -0.3, -1.1), dig_a, dig_b + 20, count=7, rise=0.6, size=0.1)
cue("dig", dig_a)
mom.crouch(dig_b, dig_b + 8, 0.5)
tunnel_in = [at_door] + [(x, 0, z - (TUNNEL_R - 0.02)) for x, _, z in TUNNEL[::-1]] + [(MOM_LIE[0], MOM_LIE[1], ROOM_FLOOR)]
in_a, in_b = dig_b + 9, f1(4)
anim.follow_path(mom.root, anim.smooth_path(tunnel_in[::3] + [tunnel_in[-1]], 6), in_a, in_b, anim.linear)
mom.walk(in_a, in_b, cadence=1.4, amp=0.3)
mom.lie(in_b + 1, in_b + 12)

# 5. Falling snow seals the entrance.
tween(plug, "scale", f0(5) + 6, f1(5), (0.001, 0.001, 0.001), (1, 1, 1), anim.ease_in_out)

# 6. The cut opens: the den is warm inside.
open_a, open_b = f0(6), f0(6) + 45
cut.move(open_a, open_b, Z_CLOSED, Z_OPEN)
tween(flake, "scale", open_a, open_a + 10, (1, 1, 1), (0, 0, 0), anim.ease_in)
cue("open", open_a)
warm_a = (f0(6) + f1(6)) // 2
tween(den_light.data, "energy", warm_a - 20, warm_a + 20, 0.0, 70.0)
cue("warm", warm_a - 20, -6)

# 7. The tunnel dips toward the entrance; warm air stays up in the room.
glow_path = [(x, y, z - 0.18) for x, y, z in TUNNEL]
highlight = effects.path_highlight("TunnelGlow", glow_path, radius=0.035, color="#7FC4FF", strength=4.0)
tween(highlight.data, "bevel_factor_end", f0(7) + 4, f0(7) + 40, 0.0, 1.0)
cue("chime", f0(7) + 4, -4)
effects.puffs("WarmAir", (-0.6, -0.25, -0.95), f0(7) + 30, f1(7) + 20, count=6, rise=0.45, size=0.06,
              color="#FFB070")
tween(highlight.data, "bevel_factor_end", f1(7) + 10, f1(7) + 20, 1.0, 0.0)

# 8. A small air hole through the roof.
hole_a = (f0(8) + f1(8)) // 2
for frame, on in ((1, False), (hole_a - 11, False), (hole_a - 10, True)):
    airhole_mod.show_render = airhole_mod.show_viewport = on
    airhole_mod.keyframe_insert("show_render", frame=frame)
    airhole_mod.keyframe_insert("show_viewport", frame=frame)
tween(airhole, "scale", hole_a - 10, hole_a + 20, (1, 1, 0.05), (1, 1, 1), anim.ease_in_out)
cue("dig", hole_a - 10, -6)
effects.puffs("Breath", (-0.75, 0.0, 0.55), hole_a + 15, f1(8) + 40, count=7, rise=0.9, size=0.07)

# 9. The cubs arrive; she nurses them for months without eating. Cubs grow, she slims down.
for i, cub in enumerate(cubs):
    tween(cub.root, "scale", f0(9) + 2 + 8 * i, f0(9) + 10 + 8 * i, (0, 0, 0), (1, 1, 1), anim.ease_out_back)
    cue("pop", f0(9) + 2 + 8 * i, -3)
grow_a, grow_b = f0(9) + 30, f1(9)
for cub in cubs:
    tween(cub.root, "scale", grow_a, grow_b, (1, 1, 1), (1.9, 1.9, 1.9), anim.ease_in_out)
tween(mom.rig, "scale", grow_a, grow_b, (1, 1, 1), (1, 0.9, 0.9), anim.ease_in_out)

# 10. Spring: light floods in, she breaks out, the cubs follow into the sunlight.
spring_a = f0(10)
for socket in sky_sockets:
    tween(socket, "default_value", spring_a, spring_a + 30,
          materials.color(WINTER_SKY), materials.color(SPRING_SKY))
tween(sun_data, "energy", spring_a, spring_a + 30, 0.0, 3.5)
tween(key.data, "color", spring_a, spring_a + 30, tuple(key.data.color), (1.0, 0.9, 0.75))
tween(den_light.data, "energy", spring_a + 30, spring_a + 60, 70.0, 15.0)
cue("chime", spring_a, -2)
tween(plug, "scale", spring_a + 6, spring_a + 20, (1, 1, 1), (0.001, 0.001, 0.001), anim.ease_in)
mom.stand(spring_a, spring_a + 8)
mom.crouch(spring_a + 8, spring_a + 14, 0.5)
exit_path = tunnel_in[::-1][:-1] + [(4.0, 0.45, SNOW_TOP)]
exit_path = anim.smooth_path(exit_path[::3] + [exit_path[-1]], 6)
out_a, out_b = spring_a + 15, f1(10) + 6
anim.follow_path(mom.root, exit_path, out_a, out_b, anim.linear)
mom.walk(out_a, out_b, cadence=1.4, amp=0.3)
mom.crouch(out_b - 10, out_b, 0.0)
cue("whoosh", out_a, -8)
for i, cub in enumerate(cubs):
    delay = 14 + 12 * i
    cub.stand(spring_a + 4, spring_a + 10)
    cub_path = [(x, y - 0.35 * (i - 0.5) * 0.6, z) for x, y, z in exit_path]
    cub_path[-1] = (3.35 - 0.45 * i, 0.15 + 0.5 * i, SNOW_TOP)
    anim.follow_path(cub.root, cub_path, out_a + delay, out_b + delay, anim.linear)
    cub.walk(out_a + delay, out_b + delay, cadence=2.6, amp=0.5)

# 11. The twist: the cut closes on the empty den, camera pulls back.
close2_a, close2_b = f0(11) + 6, f0(11) + 40
cut.move(close2_a, close2_b, Z_OPEN, Z_CLOSED)
tween(den_light.data, "energy", close2_a, close2_b, 15.0, 0.0)
cue("close", close2_a)

# 12. Every other polar bear stays active all winter: a male strolls past.
male_a, male_b = f0(12) - 10, END
male.hide_until(male_a)
anim.follow_path(male.root, [(-3.0, -1.75, SNOW_TOP), (1.6, -1.75, SNOW_TOP)], male_a, male_b, anim.linear)
male.walk(male_a, male_b, cadence=1.3, amp=0.45)
cue("steps", male_a, -10)

# ---------------------------------------------------------------- camera
cam = OrbitCamera(target=(-0.62, -0.3, -1.25), distance=1.2, height=0.12, angle_deg=-12, lens=35)
# Hook: shallow depth of field keeps the tiny cub sharp against its blurred mother.
dof = cam.camera.data.dof
dof.use_dof = True
dof.focus_object = cubs[0].root
tween(dof, "aperture_fstop", 1, f1(1), 1.2, 2.0, anim.linear)
tween(dof, "aperture_fstop", f0(2), f0(2) + 40, 2.0, 64.0, anim.ease_in)
shots = [
    # (frame, angle, distance, height, aim)
    (1, -12, 1.2, 0.12, (-0.62, -0.3, -1.25)),
    (f1(1), -6, 1.6, 0.2, (-0.55, -0.25, -1.2)),
    (f0(2) + 50, -20, 13.0, 3.6, (0.4, 0, -0.8)),
    (f1(3), -5, 12.5, 3.2, (0.4, 0, -0.8)),
    (f0(4) + 30, 28, 10.0, 2.2, (2.0, 0, -1.0)),
    (f1(5), 22, 7.5, 1.4, (2.4, 0, -1.1)),
    (f0(6) + 50, 2, 9.0, 1.4, (0.3, 0, -0.85)),
    (f0(7) + 20, 8, 6.4, 0.9, (1.2, 0, -1.05)),
    (f0(8) + 25, 4, 6.4, 1.6, (-0.5, 0, -0.35)),
    (f0(9) + 15, 8, 4.4, 0.5, (-0.45, -0.1, -1.1)),
    (f1(9), 4, 4.0, 0.45, (-0.45, -0.1, -1.1)),
    (f0(10) + 40, 18, 8.0, 1.2, (2.0, 0, -1.1)),
    (f0(11) + 45, -12, 14.0, 4.0, (0.6, 0, -0.9)),
    (END, -18, 14.5, 4.2, (0.4, 0, -0.9)),
]
for (fa, aa, da, ha, ta), (fb, ab, db, hb, tb) in zip(shots, shots[1:]):
    tween(cam.rig, "rotation_euler", fa, fb, cam.angle(aa), cam.angle(ab))
    tween(cam.camera, "location", fa, fb, cam.place(da, ha), cam.place(db, hb))
    tween(cam.aim, "location", fa, fb, ta, tb)

# ---------------------------------------------------------------- output
sec = lambda frame: round((frame - 1) / 30, 3)
labels = [
    {"text": "POLAR BEAR MATERNITY DEN", "start": sec(1), "end": sec(f1(3))},
    {"text": "AUTUMN", "start": sec(f0(4)), "end": sec(f1(5))},
    {"text": "WINTER", "start": sec(f0(6)), "end": sec(f1(9))},
    {"text": "SPRING", "start": sec(f0(10)), "end": sec(f1(10))},
    {"text": "Illustrative, not to scale", "start": sec(1), "end": sec(close_b), "style": "Note"},
    {"text": "Illustrative, not to scale", "start": sec(open_a), "end": sec(close2_b), "style": "Note"},
]
scene.frame_end = END
os.makedirs(os.path.join(core.ROOT, "renders"), exist_ok=True)
with open(os.path.join(core.ROOT, "renders", f"{NAME}_cues.json"), "w") as f:
    json.dump({"duration": round(END / 30, 3), "cues": cues, "labels": labels}, f, indent=1)
core.finish(scene, NAME, args)
