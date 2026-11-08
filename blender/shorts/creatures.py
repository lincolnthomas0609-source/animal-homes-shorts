"""Simple stylized stand-in animals built from primitives.

Each faces +X with its root at ground level under the body, ready for anim.follow_path.
"""

import math

from . import anim, materials, shapes


def beaver(name="Beaver", size=1.0, parent=None):
    """Stylized beaver, about 1.1 * size long including the tail."""
    s = size
    fur = materials.matte(f"{name}_Fur", "fur_brown", roughness=0.7)
    dark = materials.matte(f"{name}_Dark", "fur_dark", roughness=0.6)
    eye = materials.matte(f"{name}_Eye", "#151515", roughness=0.2, specular=0.6)
    teeth = materials.matte(f"{name}_Teeth", "#E08A3C", roughness=0.4)

    root = shapes.empty(name, parent=parent)
    shapes.ellipsoid(f"{name}_Body", (0.40 * s, 0.21 * s, 0.18 * s), (0, 0, 0), fur, root)
    shapes.ellipsoid(f"{name}_Head", (0.16 * s, 0.14 * s, 0.13 * s), (0.40 * s, 0, 0.05 * s), fur, root)
    shapes.ellipsoid(f"{name}_Nose", (0.035 * s, 0.04 * s, 0.03 * s), (0.555 * s, 0, 0.07 * s), eye, root)
    shapes.box(f"{name}_Teeth", (0.02 * s, 0.05 * s, 0.05 * s), (0.545 * s, 0, 0.0), teeth, root)
    for side in (-1, 1):
        shapes.ellipsoid(f"{name}_Eye{side}", (0.025 * s,) * 3, (0.50 * s, side * 0.085 * s, 0.12 * s), eye, root)
        shapes.ellipsoid(f"{name}_Ear{side}", (0.03 * s, 0.03 * s, 0.03 * s), (0.34 * s, side * 0.11 * s, 0.16 * s), dark, root)
    shapes.ellipsoid(f"{name}_Tail", (0.26 * s, 0.12 * s, 0.03 * s), (-0.56 * s, 0, -0.05 * s), dark, root)
    return root


class Quadruped:
    """A four-legged animal with a root (move it along paths), a rig (pose offsets), and hip pivots.

    Poses are animated with tweens on rig.location, hip rotations, and hip scales, so
    don't overlap walk(), crouch(), lie() and stand() calls in time on the same animal.
    """

    def __init__(self, root, rig, hips, body_height):
        self.root, self.rig, self.hips = root, rig, hips
        self.body_height = body_height  # body center height above the ground when standing
        self._lying = False

    def hide_until(self, frame, pop=6):
        """Invisible until frame, then pops in."""
        anim.tween(self.root, "scale", 1, frame, (0, 0, 0), (0, 0, 0), anim.linear)
        anim.tween(self.root, "scale", frame, frame + pop, (0, 0, 0), (1, 1, 1), anim.ease_out_back)

    def walk(self, start, end, cadence=1.6, amp=0.45):
        """Swing the legs in diagonal pairs. cadence = strides per second."""
        phases = [0.0, math.pi, math.pi, 0.0]  # front-left, front-right, hind-left, hind-right
        base_z = self.rig.location.z  # keep any crouch offset
        for hip in self.hips:
            anim.hold_before(hip, "rotation_euler", start)
        anim.hold_before(self.rig, "location", start)
        for f in range(start, end + 1):
            t = (f - start) / 30.0
            fade = min(1.0, (f - start) / 6, (end - f) / 6)
            for hip, phase in zip(self.hips, phases):
                anim.key(hip, "rotation_euler", f, (0, amp * fade * math.sin(2 * math.pi * cadence * t + phase), 0))
            bob = 0.03 * self.body_height * abs(math.sin(2 * math.pi * cadence * t)) * fade
            anim.key(self.rig, "location", f, (0, 0, base_z + bob))

    def crouch(self, start, end, amount):
        """Shorten the legs and lower the body (0 = standing, 1 = belly on the ground)."""
        legs = 1 - 0.7 * amount
        for hip in self.hips:
            cur = tuple(hip.scale)
            anim.tween(hip, "scale", start, end, cur, (1, 1, legs))
        cur = tuple(self.rig.location)
        anim.tween(self.rig, "location", start, end, cur, (0, 0, -self.body_height * 0.7 * amount))

    def lie(self, start, end):
        """Lie down on the belly with the legs folded flat."""
        for i, hip in enumerate(self.hips):
            fold = -1.3 if i < 2 else 1.3
            anim.tween(hip, "rotation_euler", start, end, tuple(hip.rotation_euler), (0, fold, 0))
            anim.tween(hip, "scale", start, end, tuple(hip.scale), (1, 1, 0.8))
        anim.tween(self.rig, "location", start, end, tuple(self.rig.location),
                   (0, 0, -self.body_height * 0.62))

    def stand(self, start, end):
        for hip in self.hips:
            anim.tween(hip, "rotation_euler", start, end, tuple(hip.rotation_euler), (0, 0, 0))
            anim.tween(hip, "scale", start, end, tuple(hip.scale), (1, 1, 1))
        anim.tween(self.rig, "location", start, end, tuple(self.rig.location), (0, 0, 0))

    def set_pose_lying(self):
        """Start lying (call before any animation)."""
        for i, hip in enumerate(self.hips):
            hip.rotation_euler = (0, -1.3 if i < 2 else 1.3, 0)
            hip.scale = (1, 1, 0.8)
        self.rig.location = (0, 0, -self.body_height * 0.62)


def polar_bear(name="PolarBear", size=1.0, parent=None, fur_color="#F1ECDF"):
    """Stylized polar bear, about 2.6 * size long nose to tail (size 0.75 is roughly an adult female)."""
    s = size
    fur = materials.matte(f"{name}_Fur", fur_color, roughness=0.8, specular=0.2)
    dark = materials.matte(f"{name}_Dark", "#1A1A1E", roughness=0.3, specular=0.5)

    root = shapes.empty(name, parent=parent)
    rig = shapes.empty(f"{name}_Rig", parent=root)
    body_h = 0.70 * s
    E = lambda n, r, loc, m=fur, p=rig: shapes.ellipsoid(f"{name}_{n}", tuple(x * s for x in r),
                                                         tuple(x * s for x in loc), m, p)
    E("Body", (0.85, 0.34, 0.37), (0, 0, 0.70))
    E("Chest", (0.45, 0.33, 0.40), (0.42, 0, 0.74))
    E("Rump", (0.40, 0.33, 0.36), (-0.45, 0, 0.72))
    E("Neck", (0.32, 0.22, 0.24), (0.88, 0, 0.82))
    E("Head", (0.21, 0.17, 0.17), (1.13, 0, 0.86))
    E("Snout", (0.13, 0.095, 0.085), (1.31, 0, 0.82))
    E("Nose", (0.035, 0.045, 0.03), (1.43, 0, 0.84), dark)
    E("Tail", (0.07, 0.06, 0.06), (-0.86, 0, 0.80))
    for side in (-1, 1):
        E(f"Eye{side}", (0.024, 0.024, 0.024), (1.24, side * 0.095, 0.92), dark)
        E(f"Ear{side}", (0.045, 0.05, 0.055), (1.04, side * 0.12, 1.00))

    hips = []
    for x, label in ((0.48, "Front"), (-0.48, "Hind")):
        for side in (1, -1):
            hip = shapes.empty(f"{name}_{label}Hip{side}", (x * s, side * 0.18 * s, 0.55 * s), rig)
            shapes.ellipsoid(f"{name}_{label}Leg{side}", (0.13 * s, 0.12 * s, 0.30 * s), (0, 0, -0.25 * s), fur, hip)
            shapes.ellipsoid(f"{name}_{label}Paw{side}", (0.17 * s, 0.12 * s, 0.065 * s), (0.04 * s, 0, -0.50 * s), fur, hip)
            hips.append(hip)
    # Order: front-left, front-right, hind-left, hind-right (matches Quadruped.walk phases).
    hips = [hips[1], hips[0], hips[3], hips[2]]
    return Quadruped(root, rig, hips, body_h)
