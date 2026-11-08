"""Orbit camera rig for vertical framing.

Rig structure:
    rig (empty at the target, rotate Z to orbit)
      └─ camera (local Y = -distance, local Z = height), always aimed at `aim`

Animate with anim.tween:
    tween(cam.rig, "rotation_euler", ...)  orbit (radians, use the Z component)
    tween(cam.camera, "location", ...)     dolly in/out and raise/lower, as (0, -dist, height)
    tween(cam.aim, "location", ...)        shift what the camera looks at
"""

import math

import bpy


class OrbitCamera:
    def __init__(self, target=(0, 0, 0), distance=8.0, height=1.5, angle_deg=0.0, lens=50):
        scene = bpy.context.scene

        self.rig = bpy.data.objects.new("CamRig", None)
        self.rig.location = target
        self.rig.rotation_euler = (0, 0, math.radians(angle_deg))
        scene.collection.objects.link(self.rig)

        self.aim = bpy.data.objects.new("CamAim", None)
        self.aim.location = target
        scene.collection.objects.link(self.aim)

        data = bpy.data.cameras.new("Camera")
        data.lens = lens
        data.sensor_fit = "AUTO"
        data.clip_end = 500
        self.camera = bpy.data.objects.new("Camera", data)
        scene.collection.objects.link(self.camera)
        self.camera.parent = self.rig
        self.camera.location = (0, -distance, height)

        track = self.camera.constraints.new("TRACK_TO")
        track.target = self.aim
        track.track_axis = "TRACK_NEGATIVE_Z"
        track.up_axis = "UP_Y"

        scene.camera = self.camera

    def place(self, distance, height):
        """Camera local position tuple for tween(cam.camera, 'location', ...)."""
        return (0.0, -distance, height)

    @staticmethod
    def angle(deg):
        """Rig rotation tuple for tween(cam.rig, 'rotation_euler', ...)."""
        return (0.0, 0.0, math.radians(deg))
