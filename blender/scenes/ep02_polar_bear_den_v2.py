"""Episode 02 (v2 look, 8-line / ~35 s script): How a polar bear maternity den works.

One beat per narration line (scripts/ep02_polar_bear_den.txt), timed from
audio/narration/ep02_polar_bear_den.timing.json:
  1  inside the cut-open den: a newborn cub against its sleeping mother
  2  pull back to the coastal tundra; the cut closes, leaving just the snowdrift
  3  autumn: she walks to the drift's lee side, digs in, crawls in; blown snow seals the entrance
  4  winter: the cut opens on her curled up inside; a warm glow builds
  5  a cool line traces the tunnel dipping toward the entrance; the one air hole opens
  6  two cubs appear against her and grow; she slims; the light slowly lengthens
  7  spring: low sun; the cut closes and the entrance breaks open
  8  the family walks out into the sun; pull back; a male walks far off (others stay active)

Landscape and den are the look-dev sample (ep02_sample_v2.py). Den geometry follows
Harington (1968) averages: tunnel ~2 m long, ~0.6 m wide, rising toward a ~2 x 1.5 x 1 m
room. Animals and dimensions are illustrative.

Run:  tools/render.sh blender/scenes/ep02_polar_bear_den_v2.py preview
      tools/render.sh blender/scenes/ep02_polar_bear_den_v2.py final
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bmesh  # noqa: E402
import bpy  # noqa: E402

from shorts import anim, atmosphere, bears, core, effects, landscape, lighting, materials, matlib, shapes  # noqa: E402
from shorts.anim import tween  # noqa: E402
from shorts.camera import OrbitCamera  # noqa: E402
from shorts.landscape import fbm, smoothstep  # noqa: E402
from shorts.section import ShaderSection  # noqa: E402

NAME = "ep02_polar_bear_den_v2"
TIMING = os.path.join(core.ROOT, "audio", "narration", "ep02_polar_bear_den.timing.json")
TAIL_SECONDS = 1.4

args = core.parse_args()
L = anim.load_timing(TIMING)
assert len(L) == 8, f"scene expects 8 narration lines, got {len(L)}"
f0 = lambda i: L[i - 1]["f0"]  # first frame of narration line i (1-based)
f1 = lambda i: L[i - 1]["f1"]
END = anim.seconds(L[-1]["end"] + TAIL_SECONDS)
scene = core.setup_render(core.reset_scene(), seconds=L[-1]["end"] + TAIL_SECONDS, quality=args.quality)
core.eevee_quality(scene, exposure=0.15)
scene.frame_end = END
cues = []  # sound effect cues
cue = lambda name, frame, gain=0.0: cues.append({"name": name, "time": round((frame - 1) / 30, 3), "gain": gain})
sec = lambda frame: round((frame - 1) / 30, 3)

# ---------------------------------------------------------------- landform (as in the sample)
PLANE_Y = -0.12
SEA_Z = -3.6


def ground(x, y):
    ridge = 1.25 * (1 - smoothstep(-6.0, 2.8, x + 0.6 * math.sin(y * 0.25)))
    plain = -0.35 * smoothstep(2.5, 9.0, x)
    knoll = 1.3 * math.exp(-(((x - 1.5) / 3.2) ** 2 + ((y - 9.0) / 2.6) ** 2))
    back = 0.5 * smoothstep(3, 12, y) * (1 - smoothstep(14, 26, y))
    coast = -4.4 * smoothstep(16, 42, y + 6 * math.sin(x * 0.05))
    calm = 0.35 + 0.65 * smoothstep(2.0, 5.0, math.hypot(x - 0.3, (y - 0.3) * 1.3))
    n = (0.22 * fbm(x, y, 7, 3, seed=1) + 0.05 * fbm(x, y, 1.6, 3, seed=2)) * calm
    return ridge + plain + knoll + back + coast + n


def drift_height(x, y):
    xs = x - 0.5 * math.sin(y * 0.33)
    across = smoothstep(-5.8, -2.2, xs) * (1 - smoothstep(0.0, 4.6, xs))
    along = smoothstep(-5.5, -1.8, y) * (1 - smoothstep(2.5, 6.0, y))
    return 1.8 * across * along * (1 + 0.04 * fbm(x, y, 2.5, 2, seed=4))


def snow_depth(x, y):
    base = 0.12 + 0.06 * fbm(x, y, 3, 2, seed=5)
    ridge = smoothstep(-3.0, -5.5, x)
    knoll = smoothstep(1.4, 0.5, math.hypot((x - 1.5) / 3.2, (y - 9.0) / 2.6))
    patchy = smoothstep(0.05, -0.25, fbm(x, y, 1.4, 3, seed=6))
    drift = drift_height(x, y)
    scour = max(ridge, knoll, 0.55 * patchy) * (1 - smoothstep(0.05, 0.4, drift))
    base *= 1 - scour * (0.7 + 0.3 * patchy)
    ripple = 0.025 * fbm(x * 0.35, y * 2.0, 0.5, 2, seed=7)
    return max(base + drift + ripple * (1 - 0.8 * scour), 0.0)


ENTRANCE_Y = -0.04
ENTRANCE = (3.05, ENTRANCE_Y, 0.45)


def surface(x, y):
    dip = 0.07 * math.exp(-(((x - 3.15) / 0.5) ** 2 + ((y - ENTRANCE_Y) / 0.45) ** 2))
    return ground(x, y) + snow_depth(x, y) - dip


# ---------------------------------------------------------------- den geometry
ROOM_X, ROOM_Y = -0.5, 0.13
ROOM_R = (1.0, 0.75, 0.55)
ROOM_FLOOR = ground(ROOM_X, ROOM_Y) + 0.25
ROOM_Z = ROOM_FLOOR + 0.45
TUNNEL_R = 0.31
T_END_X = 2.75
tunnel_floor = lambda x: (ROOM_FLOOR + (ground(T_END_X, ENTRANCE_Y) + 0.12 - ROOM_FLOOR)
                          * smoothstep(0.4, T_END_X, x))
TUNNEL = anim.smooth_path([
    (0.15, ENTRANCE_Y, ROOM_FLOOR + TUNNEL_R + 0.02),
    (0.9, ENTRANCE_Y, ROOM_FLOOR + TUNNEL_R - 0.05),
    (1.7, ENTRANCE_Y, 0.5 * (ROOM_FLOOR + ground(2.6, 0) + 0.12) + TUNNEL_R),
    (T_END_X, ENTRANCE_Y, ground(T_END_X, ENTRANCE_Y) + 0.12 + TUNNEL_R),
], 10)
MOUTH_Z = ground(T_END_X, ENTRANCE_Y) + 0.12 + TUNNEL_R
MOUTH = (T_END_X + 0.22, ENTRANCE_Y, MOUTH_Z)
HOLE_R = max(0.5, surface(*MOUTH[:2]) - MOUTH_Z + 0.15)
AIR = (-0.75, PLANE_Y + 0.02)  # the air hole: through the roof above the room, at the cut
print(f"[den] floor {ROOM_FLOOR:.2f} mouth z {MOUTH_Z:.2f} surface {surface(*MOUTH[:2]):.2f} hole r {HOLE_R:.2f}")

# ---------------------------------------------------------------- sky, materials, controllers
world, (autumn_f, spring_f) = atmosphere.seasonal_world(glow_azimuth_deg=35)
HAZE = {"winter": "#7F95B5", "autumn": "#B8C4D2", "spring": "#C9D6E2"}
m_snow = matlib.snow("Snow")
m_section = matlib.snow_section("SnowSection", entrance=ENTRANCE, entrance_radius=0.42)
m_wall = matlib.den_wall("DenWall", entrance=ENTRANCE, entrance_radius=0.42)
m_rock = matlib.rock("Rock")
m_grass = matlib.grass("DrySedge")
m_seaice = matlib.sea_ice("SeaIce")
m_ice = matlib.ice_blocks("IceBlocks")
m_mount = matlib.mountain("Mountains")
haze_sockets = [matlib.add_haze(m, HAZE["winter"], start=18, distance=120, max_amount=0.85)
                for m in (m_snow, m_rock, m_grass)]
haze_sockets += [matlib.add_haze(m_seaice, HAZE["winter"], start=25, distance=260, max_amount=0.9),
                 matlib.add_haze(m_ice, HAZE["winter"], start=15, distance=160, max_amount=0.9),
                 matlib.add_haze(m_mount, HAZE["winter"], start=200, distance=900, max_amount=0.75)]

section = ShaderSection(PLANE_Y, z_closed=-14.0)  # starts open (line 1 is inside the den)
section.clip(m_snow, m_wall, m_rock, m_grass)
section.face(m_section)

# Entrance hole (dug in autumn, drifted shut, broken open in spring) and the air hole.
entrance_ctl = shapes.empty("EntranceCtl", MOUTH)
entrance_ctl.scale = (0.001,) * 3
air_ctl = shapes.empty("AirCtl", (AIR[0], AIR[1], 0.0))  # z set once the roof height is known
air_ctl.scale = (0.09, 0.09, 0.001)
matlib.add_hole(m_snow, entrance_ctl, "sphere")
matlib.add_hole(m_snow, air_ctl, "shaft")
matlib.add_hole(m_wall, entrance_ctl, "sphere", transparent_shadow=False)
matlib.add_hole(m_wall, air_ctl, "shaft", transparent_shadow=False)
matlib.add_hole(m_section, air_ctl, "shaft")
m_wall.use_transparent_shadow = False  # the cut-away half still shades the cavity

# ---------------------------------------------------------------- terrain and section
xs = landscape.spaced([(-120, -40, 2.0), (-40, -12, 0.8), (-12, -4, 0.15), (-4, 4.5, 0.035),
                       (4.5, 14, 0.15), (14, 40, 0.8), (40, 80, 2.0)])
ys = landscape.spaced([(-25, -9, 0.6), (-9, -2, 0.1), (-2, 2.5, 0.035), (2.5, 14, 0.12),
                       (14, 30, 0.6), (30, 60, 2.0)])
ys = landscape.with_exact(ys, PLANE_Y)
terrain = landscape.heightfield("Terrain", xs, ys, surface, m_snow,
                                attrs={"sdepth": lambda x, y, z: snow_depth(x, y)})
face_xs = [x for x in xs if -14 <= x <= 16]
face = landscape.section_face("SectionFace", face_xs, PLANE_Y, lambda x: surface(x, PLANE_Y), z_bottom=-14.0,
                              rows=130)

room = shapes.ellipsoid("Room", ROOM_R, (ROOM_X, ROOM_Y, ROOM_Z), segments=72, rings=36)
for v in room.data.vertices:
    v.co.z = max(v.co.z, -0.45)
tunnel = shapes.tube("Tunnel", TUNNEL, TUNNEL_R, resolution=6)
shapes.boolean(room, tunnel, "UNION")
shapes.bake(room)
shapes.delete(tunnel)
remesh = room.modifiers.new("Remesh", "REMESH")
remesh.mode, remesh.voxel_size = "VOXEL", 0.03
dig_tex = bpy.data.textures.new("DigMarks", "CLOUDS")
dig_tex.noise_scale, dig_tex.noise_depth = 0.22, 2
displace = room.modifiers.new("Irregular", "DISPLACE")
displace.texture, displace.strength, displace.mid_level = dig_tex, 0.07, 0.5
soften = room.modifiers.new("Soften", "SMOOTH")
soften.factor, soften.iterations = 0.7, 6
shapes.bake(room)
shapes.boolean(face, room)
shapes.bake(face)
landscape.set_point_attrs(face, {
    "hag": lambda x, y, z: z - ground(x, PLANE_Y),
    "sdepth": lambda x, y, z: surface(x, PLANE_Y) - ground(x, PLANE_Y),
})
face.data.materials.clear()
face.data.materials.append(m_section)
lining = room
lining.name = "DenLining"
landscape.flip_normals(lining)
lining.data.materials.clear()
lining.data.materials.append(m_wall)

IMG_X, IMG_Y = (-7.0, 9.0), (-13.0, 1.2)
heights = landscape.height_image("DenHeights", IMG_X, IMG_Y, (640, 570), ground, surface,
                                 cavity=lining, cavity_box=((-1.7, 3.3), (-0.8, 1.0)))
m_cap = matlib.snow_section("CapSection", entrance=ENTRANCE, entrance_radius=0.42,
                            fields=matlib.heightmap_fields(heights, IMG_X, IMG_Y))
cap = shapes._mesh_object("SectionCap", lambda bm: None, m_cap, smooth=False)
cap.data.from_pydata([(IMG_X[0], IMG_Y[0] - PLANE_Y, 0), (IMG_X[1], IMG_Y[0] - PLANE_Y, 0),
                      (IMG_X[1], 0, 0), (IMG_X[0], 0, 0)], [], [(0, 1, 2, 3)])
cap.parent = section.ctl

# Roof above the air hole (cavity top from the lining) and the shaft/mouth walls.
from mathutils.bvhtree import BVHTree  # noqa: E402
from mathutils import Vector  # noqa: E402
_tree = BVHTree.FromPolygons([v.co for v in lining.data.vertices], [p.vertices for p in lining.data.polygons])
_hit = _tree.ray_cast(Vector((AIR[0], AIR[1], ROOM_Z)), Vector((0, 0, 1)))[0]
AIR_CEIL = _hit.z if _hit is not None else ROOM_Z + 0.5
AIR_BASE = AIR_CEIL - 0.12
AIR_H = surface(*AIR) - AIR_BASE + 0.06
air_ctl.location.z = AIR_BASE


def _wall_mesh(name, build):
    obj = shapes._mesh_object(name, build, smooth=True)
    landscape.flip_normals(obj)
    return obj


def _shaft(bm):
    bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=1.0, radius2=1.0, depth=1.0)
    bmesh.ops.translate(bm, vec=(0, 0, 0.5), verts=bm.verts)


m_shaft = matlib.den_wall("ShaftWall")
section.clip(m_shaft)
matlib.add_solid_only(m_shaft, heights, IMG_X, IMG_Y)
shaft = _wall_mesh("AirShaftWall", _shaft)
materials.assign(shaft, m_shaft)
shaft.parent = air_ctl
m_mouth = matlib.den_wall("MouthWall", colors=("#7D8FA3", "#5F7186"))  # dug hole walls sit in shade
matlib.add_solid_only(m_mouth, heights, IMG_X, IMG_Y)
mouth = _wall_mesh("EntranceWall", lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0))
materials.assign(mouth, m_mouth)
mouth.parent = entrance_ctl

# ---------------------------------------------------------------- props and far background
rock_meshes = [landscape.rock_mesh(f"RockMesh{i}", seed=i, size=(1.0, 0.85, 0.55 + 0.1 * (i % 3))) for i in range(6)]
tuft_meshes = [landscape.tuft_mesh(f"TuftMesh{i}", seed=i, blades=16 + 4 * i) for i in range(4)]
WALK_ZONE = lambda x, y: 2.6 < x < 7.6 and -3.8 < y < 0.6  # keep her walking line clear


def thin_snow(x, y, rng):
    return snow_depth(x, y) < 0.09 and abs(y - PLANE_Y) > 0.8 and not WALK_ZONE(x, y)


rock_pts = landscape.poisson_points(((-14, 12), (-13, 16)), 110, thin_snow, seed=3, min_dist=1.0)
rock_pts += landscape.poisson_points(((3.8, 12), (-8, 14)), 14,
                                     lambda x, y, r: r.random() < 0.15 and abs(y - PLANE_Y) > 0.8
                                     and not WALK_ZONE(x, y), seed=4, min_dist=2.0)
rock_pts += landscape.poisson_points(((2.5, 9.0), (-11.0, -3.5)), 9,
                                     lambda x, y, r: drift_height(x, y) < 0.05 and not WALK_ZONE(x, y),
                                     seed=12, min_dist=1.6)
landscape.scatter("Rock", rock_meshes, [(x, y, surface(x, y)) for x, y in rock_pts], m_rock, seed=5,
                  scale=(0.25, 0.9), sink=0.35)
tuft_pts = landscape.poisson_points(((-14, 12), (-13, 16)), 420, thin_snow, seed=8, min_dist=0.3)
for t in landscape.scatter("Sedge", tuft_meshes, [(x, y, surface(x, y)) for x, y in tuft_pts], m_grass, seed=9,
                           scale=(0.7, 1.4), sink=0.15, tilt=0.15):
    t.rotation_euler.z = 0.0

shapes.box("SeaIce", (3000, 3000, 0.2), (0, 1500 + 15, SEA_Z - 0.1), m_seaice)
for i, (y0, amp, seed) in enumerate(((70, 6, 1), (115, 10, 2), (190, 14, 3), (300, 20, 4))):
    pts = [(x, y0 + amp * math.sin(x * 0.03 + seed) + 4 * fbm(x, 0, 20, 2, seed=seed)) for x in range(-260, 261, 20)]
    landscape.pressure_ridge(f"PressureRidge{i}", pts, m_ice, seed=seed, base_z=SEA_Z,
                             height=(0.3, 1.2 + i * 0.4), block=(0.5, 1.3 + i * 0.3), density=2.6 + 0.6 * i)


def mountains(x, y):
    env = smoothstep(1300, 1600, y) * (0.45 + 0.55 * math.sin(x * 0.0025 + 1.3) ** 2)
    ridged = max(1 - abs(fbm(x, y, 260, 5, seed=11)), 0.0)
    return SEA_Z - 8 + env * (25 + 75 * ridged ** 1.5)


landscape.heightfield("Mountains", landscape.spaced([(-3200, 3200, 20)]), landscape.spaced([(1250, 2200, 20)]),
                      mountains, m_mount)

# ---------------------------------------------------------------- lights and seasons
sky_key = atmosphere.sun("SkyKey", -140, 16, 2.6, (0.78, 0.86, 1.0), angle_deg=18)
glow_rim = atmosphere.sun("HorizonRim", 35, 7, 1.4, (1.0, 0.72, 0.55), angle_deg=6)
den_light = effects.warm_light("DenGlow", (ROOM_X + 0.1, ROOM_Y - 0.3, ROOM_FLOOR + 0.5), color=(1.0, 0.46, 0.17),
                               energy=85.0, radius=0.2)
SEASONS = {
    # sky factors (autumn, spring), key (azimuth, elevation, energy, color), rim energy, haze
    "winter": dict(f=(0.0, 0.0), key=(-140, 16, 2.6, (0.78, 0.86, 1.0)), rim=1.4, haze=HAZE["winter"]),
    "late": dict(f=(0.0, 0.3), key=(-135, 14, 2.9, (0.86, 0.88, 0.96)), rim=1.3, haze="#94A8C2"),
    "autumn": dict(f=(1.0, 0.0), key=(-118, 9, 3.4, (1.0, 0.84, 0.66)), rim=0.7, haze=HAZE["autumn"]),
    "spring": dict(f=(0.0, 1.0), key=(-125, 13, 4.2, (1.0, 0.88, 0.72)), rim=0.6, haze=HAZE["spring"]),
}


def season(a, b, frm, to):
    s, t = SEASONS[frm], SEASONS[to]
    tween(autumn_f, "default_value", a, b, s["f"][0], t["f"][0])
    tween(spring_f, "default_value", a, b, s["f"][1], t["f"][1])
    tween(sky_key, "rotation_euler", a, b, atmosphere.sun_rotation(*s["key"][:2]), atmosphere.sun_rotation(*t["key"][:2]))
    tween(sky_key.data, "energy", a, b, s["key"][2], t["key"][2])
    tween(sky_key.data, "color", a, b, s["key"][3], t["key"][3])
    tween(glow_rim.data, "energy", a, b, s["rim"], t["rim"])
    for sock in haze_sockets:
        tween(sock, "default_value", a, b, materials.color(s["haze"]), materials.color(t["haze"]))


# ---------------------------------------------------------------- animals
mom_rest, mom_body = bears.polar_bear_resting("Mom", size=0.92, pose="sternal", curl_radius=1.1, head_turn=-18)
mom_rest.location = (ROOM_X - 0.05, 0.45, ROOM_FLOOR)
bears.breathe(mom_body, 1, END)
CUB_BIRTH, CUB_SPRING = 0.18, 0.32
cub_rest = []
CUB_SPOTS = [((-0.62, 0.04, ROOM_FLOOR), -0.3), ((-0.02, 0.05, ROOM_FLOOR), math.pi - 0.3)]
for i, (pos, yaw) in enumerate(CUB_SPOTS):
    # Newborn fur is whiter than the mother's creamy coat, which helps them read against her.
    root, body = bears.polar_bear_resting(f"Cub{i}", size=CUB_BIRTH, pose="sternal", curl_radius=0.9,
                                          head_turn=-45 if i == 0 else 40, juvenile=True,
                                          fur=matlib.fur(f"Cub{i}_Fur", col="#FAFAF7", shade="#ECE8DE"))
    root.location, root.rotation_euler = pos, (0, 0, yaw)
    body.data.materials[0].surface_render_method = "DITHERED"
    cub_rest.append((root, body))
mom = bears.WalkingBear("MomWalk", size=0.92)
cub_walk = [bears.WalkingBear(f"CubWalk{i}", size=0.33) for i in range(2)]
male = bears.WalkingBear("Male", size=1.05)


def ground_path(points, samples=10):
    """Smooth path over the snow surface through (x, y) points."""
    return [(x, y, surface(x, y)) for x, y, _ in anim.smooth_path([(x, y, 0.0) for x, y in points], samples)]


def path_length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


def walk_along(bear, path, a, b, amp=0.4, ease=anim.linear):
    anim.follow_path(bear.root, path, a, b, ease)
    bear.walk(a, b, cadence=bear.stride_cadence(path_length(path), b - a, amp), amp=amp)


# ---------------------------------------------------------------- beats
# 1. Inside the open den: a newborn cub against its sleeping mother.
cub0_fur = cub_rest[0][1].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Alpha"]
cub1_fur = cub_rest[1][1].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Alpha"]
bears.visibility(bears.resting_parts(cub_rest[1][0]), [(1, False)])

# 2. Pull back; the cut closes ("rewind") and we are back in autumn.
cue("whoosh", f0(2) + 20, -4)
close_a, close_b = f0(2) + 33, f1(2) - 8
section.sweep([(close_a, -14.0), ((close_a + close_b) // 2 - 4, ROOM_FLOOR - 0.4), (close_b, 3.0)], glint=(2.5, 10))
cue("close", close_a)
tween(den_light.data, "energy", close_a, close_b, 85.0, 0.0)
hidden = close_b + 1
bears.visibility(bears.resting_parts(mom_rest), [(1, True), (hidden, False)])
bears.visibility(bears.resting_parts(cub_rest[0][0]), [(1, True), (hidden, False)])
season(close_b - 6, f0(3) + 6, "winter", "autumn")
flake, flake_alpha = effects.windblown_snow("Snowfall", (-16, 12), (-14, 8), 7.0, 1, f0(4), count=1400,
                                            flake=0.012, wind=(1.2, 0.25), fall=0.8)
anim.key(flake_alpha, "default_value", 1, 0.0)
tween(flake_alpha, "default_value", f0(2) + 15, f0(2) + 40, 0.0, 1.0)
tween(flake_alpha, "default_value", close_b, f0(3) + 15, 1.0, 0.0)

# 3. Autumn: she walks to the drift's lee side, digs in, and crawls in; snow drifts over the entrance.
DIG_SPOT = (MOUTH[0] + 0.95, ENTRANCE_Y)
walk_a, walk_b = close_b - 2, f0(3) + 62
outside_path = ground_path([(6.9, -3.3), (5.6, -1.6), (4.6, -0.35), DIG_SPOT])
mom.root.location = outside_path[0]
mom.visible([(1, False), (walk_a, True)])
walk_along(mom, outside_path, walk_a, walk_b, ease=lambda t: anim.ease_out(t) * 0.35 + t * 0.65)
cue("steps", walk_a + 6, -8)
dig_a, dig_b = walk_b + 2, walk_b + 30
mom.dig(dig_a, dig_b)
tween(entrance_ctl, "scale", dig_a + 2, dig_b - 2, (0.001,) * 3, (HOLE_R,) * 3, anim.ease_out)
effects.puffs("DigSpray", (MOUTH[0] + 0.45, ENTRANCE_Y - 0.25, surface(*MOUTH[:2]) - 0.05), dig_a + 2, dig_b + 16,
              count=10, rise=0.45, size=0.05, color="#F4F7FA", seed=5)
cue("dig", dig_a)
crawl_a, crawl_b = dig_b + 2, dig_b + 34
mom.crouch(dig_b - 4, crawl_a, 0.55)
inside = [(x, y, tunnel_floor(x)) for x in (2.6, 2.2, 1.8, 1.5) for y in (ENTRANCE_Y,)]
crawl_path = anim.smooth_path([(DIG_SPOT[0], DIG_SPOT[1], surface(*DIG_SPOT)), (MOUTH[0] + 0.2, ENTRANCE_Y, MOUTH_Z - 0.2)]
                              + inside, 8)
anim.follow_path(mom.root, crawl_path, crawl_a, crawl_b, anim.linear)
mom.walk(crawl_a, crawl_b, cadence=1.6, amp=0.3)
in_frame = crawl_a + round((crawl_b - crawl_a) * 0.8)
mom.visible([(in_frame, False)])
bears.visibility(bears.resting_parts(mom_rest), [(in_frame, True)])
seal_a, seal_b = crawl_b - 10, f1(3) - 2
tween(entrance_ctl, "scale", seal_a, seal_b, (HOLE_R,) * 3, (0.001,) * 3, anim.ease_in_out)
tween(flake_alpha, "default_value", seal_a - 20, seal_a - 5, 0.0, 1.0)
effects.puffs("Drifting", (MOUTH[0] + 0.3, ENTRANCE_Y - 0.2, surface(*MOUTH[:2])), seal_a, seal_b + 20,
              count=5, rise=0.25, size=0.11, color="#EEF3F8", seed=8)
cue("wind", seal_a, -6)

# 4. Winter: the cut opens on her curled up inside; a warm glow builds.
season(f0(4) - 4, f0(4) + 24, "autumn", "winter")
tween(flake_alpha, "default_value", f0(4) - 8, f0(4) + 12, 1.0, 0.0)
open_a, open_b = f0(4) + 4, f0(4) + 80
section.sweep([(open_a, 3.0), (open_a + 42, ROOM_FLOOR - 0.4), (open_b, -14.0)], glint=(3.0, 14))
cue("open", open_a)
glow_a = open_a + 46
anim.smooth_keys(den_light.data, "energy", [(glow_a, 0.0), (glow_a + 55, 85.0)])
cue("warm", glow_a, -6)

# 5. The tunnel dips toward the entrance (cool line); warm air stays in; the air hole opens.
line_pts = [(x, PLANE_Y + 0.06, z - TUNNEL_R * 0.55) for x, _, z in TUNNEL]
highlight = effects.path_highlight("TunnelLine", line_pts, radius=0.028, color="#9FDCFF", strength=3.5)
hl_a = f0(5) + 6
tween(highlight.data, "bevel_factor_end", hl_a, hl_a + 45, 0.0, 1.0)
cue("chime", hl_a, -4)
effects.puffs("WarmAir", (ROOM_X + 0.1, ROOM_Y - 0.35, ROOM_Z + 0.05), hl_a + 30, hl_a + 105, count=4, rise=0.3,
              size=0.05, color="#FFB070", seed=4)
anim.smooth_keys(den_light.data, "energy", [(hl_a + 40, 85.0), (hl_a + 70, 105.0), (hl_a + 110, 92.0)])
tween(highlight.data, "bevel_factor_start", hl_a + 110, hl_a + 125, 0.0, 1.0)
air_a = f0(5) + 120
air_b = air_a + 32
tween(air_ctl, "scale", air_a, air_b, (0.09, 0.09, 0.001), (0.09, 0.09, AIR_H), anim.ease_in_out)
cue("dig", air_a, -6)
effects.puffs("Breath", (AIR[0], AIR[1] + 0.05, surface(*AIR) + 0.02), air_b + 4, f1(5) + 10, count=5, rise=0.7,
              size=0.05, seed=6)

# 6. Two cubs appear against her and grow while she slims; the light slowly lengthens.
cubs_a = f0(6) + 4
for i, ((root, body), alpha) in enumerate(((cub_rest[0], cub0_fur), (cub_rest[1], cub1_fur))):
    a = cubs_a + 10 * i
    bears.visibility(bears.resting_parts(root), [(a, True)])
    anim.key(alpha, "default_value", 1, 1.0 if i == 0 else 0.0)
    tween(alpha, "default_value", a - 1, a, 1.0 if i == 0 else 0.0, 0.0, anim.linear)
    tween(alpha, "default_value", a, a + 20, 0.0, 1.0, anim.ease_out)
    s0 = (CUB_BIRTH,) * 3
    tween(root, "scale", a, a + 20, tuple(x * 0.8 for x in s0), s0, anim.ease_out)
    tween(root, "scale", a + 24, f1(6), s0, (CUB_SPRING,) * 3, anim.ease_in_out)
cue("warm", cubs_a, -9)
tween(mom_rest, "scale", cubs_a + 24, f1(6), (0.92,) * 3, (0.92, 0.92 * 0.93, 0.92 * 0.95), anim.ease_in_out)
season(cubs_a, f1(6), "winter", "late")

# 7. Spring: low sun; the cut closes and the entrance breaks open.
spring_a = f0(7)
season(spring_a - 2, spring_a + 24, "late", "spring")
cue("chime", spring_a, -2)
tween(den_light.data, "energy", spring_a, spring_a + 30, 92.0, 0.0)
close2_a, close2_b = spring_a + 4, spring_a + 46
section.sweep([(close2_a, -14.0), (close2_a + 21, ROOM_FLOOR - 0.4), (close2_b, 3.0)], glint=(2.5, 8))
cue("close", close2_a)
swap = close2_b + 1
bears.visibility(bears.resting_parts(mom_rest), [(swap, False)])
for root, _ in cub_rest:
    bears.visibility(bears.resting_parts(root), [(swap, False)])
mom.visible([(swap, True)])
for c in cub_walk:
    c.visible([(1, False), (swap, True)])
break_a = swap + 1
tween(entrance_ctl, "scale", break_a, break_a + 16, (0.001,) * 3, (HOLE_R,) * 3, anim.ease_out)
effects.puffs("BreakOut", (MOUTH[0] + 0.45, ENTRANCE_Y - 0.25, surface(*MOUTH[:2]) - 0.05), break_a, break_a + 26,
              count=10, rise=0.45, size=0.045, color="#F7F9FB", seed=11)
cue("dig", break_a)

# 8. The family walks out into the sun; pull back; a male walks far off.
out_tunnel = anim.smooth_path([(x, ENTRANCE_Y, tunnel_floor(x)) for x in (1.6, 2.1, 2.6)]
                              + [(MOUTH[0] + 0.25, ENTRANCE_Y, MOUTH_Z - 0.15),
                                 (DIG_SPOT[0] - 0.2, ENTRANCE_Y, surface(DIG_SPOT[0] - 0.2, ENTRANCE_Y))], 8)
exit_a, exit_b = break_a + 4, break_a + 30
anim.follow_path(mom.root, out_tunnel, exit_a, exit_b, anim.ease_in)
mom.walk(exit_a, exit_b, cadence=1.6, amp=0.3)
mom.crouch(exit_b, exit_b + 8, 0.0)
family_path = ground_path([(DIG_SPOT[0] - 0.2, ENTRANCE_Y), (4.6, -0.5), (5.5, -1.5), (6.3, -2.4)])
walk2_a, walk2_b = exit_b + 8, END - 12
walk_along(mom, family_path, walk2_a, walk2_b, amp=0.32, ease=lambda t: anim.ease_out(t) * 0.5 + t * 0.5)
cue("steps", walk2_a, -8)
for i, c in enumerate(cub_walk):
    delay = 22 + 14 * i
    cpath = anim.smooth_path([(x, ENTRANCE_Y, tunnel_floor(x)) for x in (1.8, 2.4)]
                             + [(MOUTH[0] + 0.25, ENTRANCE_Y, MOUTH_Z - 0.2)], 8)
    cpath += ground_path([(DIG_SPOT[0] - 0.5, ENTRANCE_Y), (4.3, -0.55 + 0.3 * i), (5.0 - 0.4 * i, -1.4 + 0.5 * i)])
    ca = exit_a + delay
    cb = min(ca + 125, END - 4)
    c.root.location = cpath[0]
    walk_along(c, cpath, ca, cb, amp=0.45, ease=lambda t: anim.ease_out(t) * 0.5 + t * 0.5)
cue("steps", exit_a + 30, -12)
male_path = ground_path([(-13.0, 19.0), (-6.0, 20.0), (1.0, 20.8)])  # far off on the coastal flats
male.root.location = male_path[0]
male.visible([(1, False), (f0(7), True)])
walk_along(male, male_path, f0(7), END, amp=0.38)
cue("whoosh", f0(8) + 10, -8)

# ---------------------------------------------------------------- camera
P = (0.4, PLANE_Y, 0.0)


def orbit(angle, dist, height, pivot=P):
    a = math.radians(angle)
    return (pivot[0] + dist * math.sin(a), pivot[1] - dist * math.cos(a), pivot[2] + height)


cam = OrbitCamera(target=(0, 0, 0), distance=0, height=0, angle_deg=0, lens=30)
cam.camera.data.clip_end = 4000
dof = cam.camera.data.dof
dof.use_dof = True
focus = shapes.empty("Focus", (-0.75, 0.0, ROOM_FLOOR + 0.12))
dof.focus_object = focus
fill = lighting.area_light("CamFill", (0, 0, 0), energy=35, size=4.0, color=(0.8, 0.87, 1.0))
fill.parent = cam.camera
fill.location, fill.rotation_euler = (1.2, 1.5, 0.0), (0.0, 0.0, 0.0)
CUB0 = (CUB_SPOTS[0][0][0], CUB_SPOTS[0][0][1], ROOM_FLOOR + 0.08)
SHOTS = [
    # frame, camera position, aim
    (1, (-0.45, -2.55, ROOM_FLOOR + 0.5), (-0.5, 0.1, ROOM_FLOOR + 0.2)),
    (f1(1), (-0.38, -2.95, ROOM_FLOOR + 0.62), (-0.45, 0.1, ROOM_FLOOR + 0.24)),
    (f0(2) + 45, orbit(4, 6.5, 1.9), (0.2, 0.0, 0.85)),
    (f1(2) - 4, orbit(30, 13.5, 5.0), (0.9, 0.0, 0.9)),
    (f0(3) + 20, orbit(44, 11.5, 3.4), (3.4, -0.9, 0.6)),
    (f0(3) + 80, orbit(52, 8.2, 2.3), (3.3, -0.3, 0.65)),
    (f1(3), orbit(50, 7.8, 2.4), (3.0, -0.2, 0.65)),
    (f0(4) + 34, orbit(22, 10.5, 4.6), (0.8, 0.0, 1.0)),
    (f0(4) + 90, orbit(4, 7.6, 2.3), (0.4, 0.0, 0.75)),
    (f1(4), orbit(1, 5.8, 1.5), (-0.3, 0.0, 0.9)),
    (f0(5) + 40, orbit(0, 6.6, 1.6), (1.1, 0.0, 0.7)),
    (air_a + 10, orbit(0, 6.9, 2.3), (-0.45, 0.0, 1.45)),
    (f1(5), orbit(0, 6.5, 2.0), (-0.45, 0.0, 1.3)),
    (f0(6) + 40, (-0.35, -3.4, ROOM_FLOOR + 0.75), (-0.4, 0.05, ROOM_FLOOR + 0.25)),
    (f1(6), (-0.35, -3.1, ROOM_FLOOR + 0.7), (-0.4, 0.05, ROOM_FLOOR + 0.25)),
    (close2_a + 24, orbit(24, 10.5, 4.6), (2.4, -0.2, 0.8)),
    (swap + 10, orbit(48, 8.6, 2.6), (3.3, -0.4, 0.6)),
    (walk2_a + 30, orbit(52, 9.4, 2.8), (4.2, -1.0, 0.6)),
    (END, orbit(42, 13.0, 4.6), (3.8, -1.0, 0.7)),
]
anim.smooth_keys(cam.camera, "location", [(f, p) for f, p, _ in SHOTS])
anim.smooth_keys(cam.aim, "location", [(f, a) for f, _, a in SHOTS])
anim.smooth_keys(dof, "aperture_fstop", [(1, 2.2), (f1(1), 2.8), (f0(2) + 40, 9.0)])
anim.smooth_keys(focus, "location", [(1, CUB0), (f1(1), CUB0), (f0(2) + 45, (0.6, PLANE_Y, 1.0)),
                                     (f0(3) + 20, (3.6, -0.6, 0.6)), (f1(3), (3.2, -0.1, 0.6)),
                                     (f0(4) + 90, (0.2, PLANE_Y + 0.3, 0.9)), (f1(4), (ROOM_X + 0.3, 0.2, ROOM_Z - 0.1)),
                                     (f0(5) + 40, (1.0, PLANE_Y, 0.7)), (f1(5), (-0.5, PLANE_Y, 1.2)),
                                     (f0(6) + 40, (-0.4, 0.05, ROOM_FLOOR + 0.1)), (swap + 10, (3.6, -0.3, 0.6)),
                                     (END, (4.5, -1.5, 0.6))])

# ---------------------------------------------------------------- output
labels = [
    {"text": "POLAR BEAR MATERNITY DEN", "start": sec(1), "end": sec(f1(2))},
    {"text": "AUTUMN", "start": sec(f0(3)), "end": sec(f1(3))},
    {"text": "WINTER", "start": sec(f0(4)), "end": sec(f1(6))},
    {"text": "SPRING", "start": sec(f0(7)), "end": sec(f1(7))},
    {"text": "Illustrative, not to scale", "start": sec(1), "end": sec(close_b), "style": "Note"},
    {"text": "Illustrative, not to scale", "start": sec(open_a), "end": sec(close2_b), "style": "Note"},
]
os.makedirs(os.path.join(core.ROOT, "renders"), exist_ok=True)
with open(os.path.join(core.ROOT, "renders", f"{NAME}_cues.json"), "w") as f:
    json.dump({"duration": round(END / 30, 3), "spring_start": sec(spring_a), "cues": sorted(cues, key=lambda c: c["time"]),
               "labels": labels}, f, indent=1)
core.finish(scene, NAME, args)
