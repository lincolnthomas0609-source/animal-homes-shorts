"""Ep 02 look-development sample (v2): narration line 6, "Snow traps heat... a den can be
around forty degrees Fahrenheit warmer than outside." Frames 559-790, matching the same
frames of ep02_polar_bear_den so before/after pairs line up.

What it shows: a coastal Arctic landscape in winter twilight; a snowdrift on the lee slope
of a low ridge holds the den. A section cut sweeps down through the landscape, revealing
the layered snowpack and frozen ground, the narrow entrance tunnel (rising toward the
room, entrance sealed by blown-in snow) and the room with the sleeping mother; a warm
glow builds while the camera moves from the establishing view into the room.

Den geometry follows Harington (1968) averages: tunnel ~2 m long and ~0.6 m wide, room
~2 x 1.5 x 1 m. Animals and dimensions are illustrative.

Run:  tools/stills.sh blender/scenes/ep02_sample_v2.py preview 600 700 790
      tools/render.sh blender/scenes/ep02_sample_v2.py preview 559:790
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bpy  # noqa: E402

from shorts import anim, atmosphere, bears, core, effects, landscape, lighting, matlib, shapes  # noqa: E402
from shorts.camera import OrbitCamera  # noqa: E402
from shorts.landscape import fbm, smoothstep  # noqa: E402
from shorts.section import ShaderSection  # noqa: E402

NAME = "ep02_sample_v2"
F0, F1 = 559, 790  # narration line 6 in the current timing
args = core.parse_args()
scene = core.setup_render(core.reset_scene(), seconds=F1 / 30, quality=args.quality)
core.eevee_quality(scene, exposure=0.15)
scene.frame_start, scene.frame_end = F0, F1

# ---------------------------------------------------------------- landform
# Wind blows from -X over a low ridge; snow piles up on the lee slope (the drift), where
# the den is dug. Land falls away toward the frozen coast in +Y.
PLANE_Y = -0.12  # section plane, a little in front of the room's center
SEA_Z = -3.6


def ground(x, y):
    """Frozen ground surface (no snow)."""
    ridge = 1.25 * (1 - smoothstep(-6.0, 2.8, x + 0.6 * math.sin(y * 0.25)))
    plain = -0.35 * smoothstep(2.5, 9.0, x)
    knoll = 1.3 * math.exp(-(((x - 1.5) / 3.2) ** 2 + ((y - 9.0) / 2.6) ** 2))
    back = 0.5 * smoothstep(3, 12, y) * (1 - smoothstep(14, 26, y))
    coast = -4.4 * smoothstep(16, 42, y + 6 * math.sin(x * 0.05))
    calm = 0.35 + 0.65 * smoothstep(2.0, 5.0, math.hypot(x - 0.3, (y - 0.3) * 1.3))
    n = (0.22 * fbm(x, y, 7, 3, seed=1) + 0.05 * fbm(x, y, 1.6, 3, seed=2)) * calm
    return ridge + plain + knoll + back + coast + n


def drift_height(x, y):
    """The lee-slope snowdrift, above the base snow cover."""
    xs = x - 0.5 * math.sin(y * 0.33)
    across = smoothstep(-5.8, -2.2, xs) * (1 - smoothstep(0.0, 4.6, xs))
    along = smoothstep(-5.5, -1.8, y) * (1 - smoothstep(2.5, 6.0, y))
    return 1.8 * across * along * (1 + 0.04 * fbm(x, y, 2.5, 2, seed=4))


def snow_depth(x, y):
    """Wind-scoured thin snow over the tundra (with bare patches), deep only in the drift."""
    base = 0.12 + 0.06 * fbm(x, y, 3, 2, seed=5)
    ridge = smoothstep(-3.0, -5.5, x)
    knoll = smoothstep(1.4, 0.5, math.hypot((x - 1.5) / 3.2, (y - 9.0) / 2.6))
    patchy = smoothstep(0.05, -0.25, fbm(x, y, 1.4, 3, seed=6))
    drift = drift_height(x, y)
    scour = max(ridge, knoll, 0.55 * patchy) * (1 - smoothstep(0.05, 0.4, drift))
    base *= 1 - scour * (0.7 + 0.3 * patchy)
    ripple = 0.025 * fbm(x * 0.35, y * 2.0, 0.5, 2, seed=7)  # sastrugi, elongated along the wind
    return max(base + drift + ripple * (1 - 0.8 * scour), 0.0)


ENTRANCE_Y = -0.04  # tunnel axis
ENTRANCE = (3.05, ENTRANCE_Y, 0.45)  # snow plug that seals the entrance (fresh snow)


def surface(x, y):
    dip = 0.07 * math.exp(-(((x - 3.15) / 0.5) ** 2 + ((y - ENTRANCE_Y) / 0.45) ** 2))
    return ground(x, y) + snow_depth(x, y) - dip


# ---------------------------------------------------------------- den geometry
ROOM_X, ROOM_Y = -0.5, 0.13
ROOM_R = (1.0, 0.75, 0.55)
ROOM_FLOOR = ground(ROOM_X, ROOM_Y) + 0.25
ROOM_Z = ROOM_FLOOR + 0.45
TUNNEL_R = 0.31
t_start = (0.15, ENTRANCE_Y, ROOM_FLOOR + TUNNEL_R + 0.02)
t_end_x = 2.75
TUNNEL = anim.smooth_path([
    t_start,
    (0.9, ENTRANCE_Y, ROOM_FLOOR + TUNNEL_R - 0.05),
    (1.7, ENTRANCE_Y, 0.5 * (ROOM_FLOOR + ground(2.6, 0) + 0.12) + TUNNEL_R),
    (t_end_x, ENTRANCE_Y, ground(t_end_x, ENTRANCE_Y) + 0.12 + TUNNEL_R),
], 10)

# ---------------------------------------------------------------- materials
world, HORIZON = atmosphere.twilight_world(glow_azimuth_deg=35, light_strength=0.6)
HAZE = "#7F95B5"
m_snow = matlib.snow("Snow")
m_section = matlib.snow_section("SnowSection", entrance=ENTRANCE, entrance_radius=0.42)
m_wall = matlib.den_wall("DenWall", entrance=ENTRANCE, entrance_radius=0.42)
m_rock = matlib.rock("Rock")
m_grass = matlib.grass("DrySedge")
m_seaice = matlib.sea_ice("SeaIce")
m_ice = matlib.ice_blocks("IceBlocks")
m_mount = matlib.mountain("Mountains")
for m in (m_snow, m_rock, m_grass):
    matlib.add_haze(m, HAZE, start=18, distance=120, max_amount=0.85)
matlib.add_haze(m_seaice, HAZE, start=25, distance=260, max_amount=0.9)
matlib.add_haze(m_ice, HAZE, start=15, distance=160, max_amount=0.9)
matlib.add_haze(m_mount, HAZE, start=200, distance=900, max_amount=0.75)

section = ShaderSection(PLANE_Y, z_closed=4.5)
section.clip(m_snow, m_wall, m_rock, m_grass)
glint = section.face(m_section)

# ---------------------------------------------------------------- terrain
xs = landscape.spaced([(-120, -40, 2.0), (-40, -12, 0.8), (-12, -4, 0.15), (-4, 4.5, 0.035),
                       (4.5, 14, 0.15), (14, 40, 0.8), (40, 80, 2.0)])
ys = landscape.spaced([(-25, -9, 0.6), (-9, -2, 0.1), (-2, 2.5, 0.035), (2.5, 14, 0.12),
                       (14, 30, 0.6), (30, 60, 2.0)])
ys = landscape.with_exact(ys, PLANE_Y)
terrain = landscape.heightfield("Terrain", xs, ys, surface, m_snow,
                                attrs={"sdepth": lambda x, y, z: snow_depth(x, y)})

# Cut face: exactly matches the terrain's row at the section plane.
face_xs = [x for x in xs if -14 <= x <= 16]
face = landscape.section_face("SectionFace", face_xs, PLANE_Y, lambda x: surface(x, PLANE_Y), z_bottom=-14.0,
                              rows=130)

# Den cavity: flat-floored room joined to the rising tunnel, sealed at the entrance end.
room = shapes.ellipsoid("Room", ROOM_R, (ROOM_X, ROOM_Y, ROOM_Z), segments=72, rings=36)
for v in room.data.vertices:
    v.co.z = max(v.co.z, -0.45)  # local coords: flatten the floor 0.45 below the center
tunnel = shapes.tube("Tunnel", TUNNEL, TUNNEL_R, resolution=6)
shapes.boolean(room, tunnel, "UNION")
shapes.bake(room)
shapes.delete(tunnel)
# Dug, not machined: an even remesh, a little irregularity, and a softened junction.
remesh = room.modifiers.new("Remesh", "REMESH")
remesh.mode, remesh.voxel_size = "VOXEL", 0.03
dig = bpy.data.textures.new("DigMarks", "CLOUDS")
dig.noise_scale, dig.noise_depth = 0.22, 2
displace = room.modifiers.new("Irregular", "DISPLACE")
displace.texture, displace.strength, displace.mid_level = dig, 0.07, 0.5
smooth = room.modifiers.new("Soften", "SMOOTH")
smooth.factor, smooth.iterations = 0.7, 6
shapes.bake(room)
shapes.boolean(face, room)
shapes.bake(face)
landscape.set_point_attrs(face, {
    "hag": lambda x, y, z: z - ground(x, PLANE_Y),
    "sdepth": lambda x, y, z: surface(x, PLANE_Y) - ground(x, PLANE_Y),
})
materials_face = face.data.materials
materials_face.clear()
materials_face.append(m_section)
lining = room
lining.name = "DenLining"
landscape.flip_normals(lining)
lining.data.materials.clear()
lining.data.materials.append(m_wall)
m_wall.use_transparent_shadow = False  # the cut-away half still shades the cavity: open space reads darker

# Horizontal cut face riding on the cut's lower edge: the top of the solid block that
# remains in front of the plane while the cut sweeps down (hidden above the snow surface
# and inside the den cavity, read from a baked height image).
CAP_X, CAP_Y = (-7.0, 9.0), (-13.0, PLANE_Y)
cap_img = landscape.height_image("CapHeights", CAP_X, CAP_Y, (640, 520), ground, surface,
                                 cavity=lining, cavity_box=((-1.7, 3.3), (-0.75, PLANE_Y)))
m_cap = matlib.snow_section("CapSection", entrance=ENTRANCE, entrance_radius=0.42,
                            fields=matlib.heightmap_fields(cap_img, CAP_X, CAP_Y))
cap = shapes._mesh_object("SectionCap", lambda bm: None, m_cap, smooth=False)
cap.data.from_pydata([(CAP_X[0], CAP_Y[0] - PLANE_Y, 0), (CAP_X[1], CAP_Y[0] - PLANE_Y, 0),
                      (CAP_X[1], 0, 0), (CAP_X[0], 0, 0)], [], [(0, 1, 2, 3)])
cap.parent = section.ctl

# ---------------------------------------------------------------- props: rocks and dry sedge
rock_meshes = [landscape.rock_mesh(f"RockMesh{i}", seed=i, size=(1.0, 0.85, 0.55 + 0.1 * (i % 3))) for i in range(6)]
tuft_meshes = [landscape.tuft_mesh(f"TuftMesh{i}", seed=i, blades=16 + 4 * i) for i in range(4)]


def thin_snow(x, y, rng):
    return snow_depth(x, y) < 0.09 and abs(y - PLANE_Y) > 0.8


rock_pts = landscape.poisson_points(((-14, 12), (-13, 16)), 110, thin_snow, seed=3, min_dist=1.0)
rock_pts += landscape.poisson_points(((3.8, 12), (-8, 14)), 14,
                                     lambda x, y, r: r.random() < 0.15 and abs(y - PLANE_Y) > 0.8, seed=4,
                                     min_dist=2.0)
# A few boulders through the snow on the open slope in front of the drift (foreground of the
# establishing view; the cut removes them along with everything else in front of the plane).
rock_pts += landscape.poisson_points(((2.5, 9.0), (-11.0, -3.5)), 9,
                                     lambda x, y, r: drift_height(x, y) < 0.05, seed=12, min_dist=1.6)
rocks = landscape.scatter("Rock", rock_meshes, [(x, y, surface(x, y)) for x, y in rock_pts], m_rock, seed=5,
                          scale=(0.25, 0.9), sink=0.35)
tuft_pts = landscape.poisson_points(((-14, 12), (-13, 16)), 420, thin_snow, seed=8, min_dist=0.3)
tufts = landscape.scatter("Sedge", tuft_meshes, [(x, y, surface(x, y)) for x, y in tuft_pts], m_grass, seed=9,
                          scale=(0.7, 1.4), sink=0.15, tilt=0.15)
for t in tufts:
    t.rotation_euler.z = 0.0  # keep blades leaning downwind (+X)

# ---------------------------------------------------------------- far background
sea = shapes.box("SeaIce", (3000, 3000, 0.2), (0, 1500 + 15, SEA_Z - 0.1), m_seaice)
for i, (y0, amp, seed) in enumerate(((70, 6, 1), (115, 10, 2), (190, 14, 3), (300, 20, 4))):
    pts = [(x, y0 + amp * math.sin(x * 0.03 + seed) + 4 * fbm(x, 0, 20, 2, seed=seed)) for x in range(-260, 261, 20)]
    landscape.pressure_ridge(f"PressureRidge{i}", pts, m_ice, seed=seed, base_z=SEA_Z,
                             height=(0.3, 1.2 + i * 0.4), block=(0.5, 1.3 + i * 0.3), density=2.6 + 0.6 * i)


def mountains(x, y):
    """Low, worn coastal mountains far across the sea ice."""
    env = smoothstep(1300, 1600, y) * (0.45 + 0.55 * math.sin(x * 0.0025 + 1.3) ** 2)
    ridged = max(1 - abs(fbm(x, y, 260, 5, seed=11)), 0.0)
    return SEA_Z - 8 + env * (25 + 75 * ridged ** 1.5)


landscape.heightfield("Mountains", landscape.spaced([(-3200, 3200, 20)]), landscape.spaced([(1250, 2200, 20)]),
                      mountains, m_mount)

# ---------------------------------------------------------------- the mother
mom, mom_body = bears.polar_bear_resting("Mom", size=0.92, pose="sternal", curl_radius=1.1, head_turn=-18)
mom.location = (ROOM_X - 0.05, 0.38, ROOM_FLOOR)
bears.breathe(mom_body, 1, F1 + 10)

# ---------------------------------------------------------------- lights
# Cool skylight from the open sky behind the camera, a low warm rim from the twilight glow
# on the horizon, and (once the den is open) her body warmth shown as a soft warm glow.
sky_key = atmosphere.sun("SkyKey", -140, 16, 2.6, (0.78, 0.86, 1.0), angle_deg=18)
glow_rim = atmosphere.sun("HorizonRim", 35, 7, 1.4, (1.0, 0.72, 0.55), angle_deg=6)
den_light = effects.warm_light("DenGlow", (ROOM_X + 0.1, ROOM_Y - 0.3, ROOM_FLOOR + 0.5), color=(1.0, 0.46, 0.17),
                               energy=0.0, radius=0.2)

# ---------------------------------------------------------------- motion
# Light snow settles out as the cut begins (fades, no popping).
flake, flake_alpha = effects.windblown_snow("Snowfall", (-14, 8), (-12, 4), 6.0, F0, F0 + 60, count=900,
                                            flake=0.012, wind=(1.1, 0.25), fall=0.7)
anim.tween(flake_alpha, "default_value", F0 + 20, F0 + 75, 1.0, 0.0, anim.ease_in_out)

# The section sweeps down: slow over the den, faster through the deep ground, eased at both ends.
CUT_A, CUT_B = F0 + 16, F0 + 96
section.sweep([(CUT_A, 3.0), (F0 + 62, ROOM_FLOOR - 0.4), (CUT_B, -14.0)], glint=(3.0, 14))

# Warmth: the den glow builds once the room is open, peaking mid-line.
anim.smooth_keys(den_light.data, "energy", [(F0 + 70, 0.0), (F0 + 130, 85.0), (F1, 95.0)])

# ---------------------------------------------------------------- camera
cam = OrbitCamera(target=(0.4, PLANE_Y, 0.0), distance=12.5, height=3.6, angle_deg=26, lens=30)
cam.camera.data.clip_end = 4000
dof = cam.camera.data.dof
dof.use_dof = True
focus = shapes.empty("Focus", (0.6, PLANE_Y, 1.2))
dof.focus_object = focus
dof.aperture_fstop = 9.0
# A soft, dim fill from the camera side so the open cavities read (cutaway convention).
fill = lighting.area_light("CamFill", (0, 0, 0), energy=35, size=4.0, color=(0.8, 0.87, 1.0))
fill.parent = cam.camera
fill.location, fill.rotation_euler = (1.2, 1.5, 0.0), (0.0, 0.0, 0.0)
SHOTS = [
    # frame, orbit angle, distance, height, aim
    (F0, 42, 12.5, 3.4, (1.1, 0.0, 1.0)),
    (F0 + 50, 18, 10.8, 4.8, (0.8, 0.0, 1.0)),
    (F0 + 120, 3, 7.8, 2.4, (0.4, 0.0, 0.75)),
    (F1, 0, 5.0, 1.45, (-0.25, 0.0, 0.95)),
]
anim.smooth_keys(cam.rig, "rotation_euler", [(f, cam.angle(a)) for f, a, *_ in SHOTS])
anim.smooth_keys(cam.camera, "location", [(f, cam.place(d, h)) for f, _, d, h, _ in SHOTS])
anim.smooth_keys(cam.aim, "location", [(f, aim) for f, *_, aim in SHOTS])
anim.smooth_keys(focus, "location", [(F0, (0.6, PLANE_Y, 1.2)), (F0 + 120, (0.3, PLANE_Y + 0.3, 1.0)),
                                     (F1, (ROOM_X + 0.3, 0.2, ROOM_Z - 0.1))])

core.finish(scene, NAME, args)
