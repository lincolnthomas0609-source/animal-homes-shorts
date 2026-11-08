"""Scene reset, render settings, and the preview/final render entry point."""

import argparse
import os
import sys

import bpy

ROOT = os.environ.get(
    "SHORTS_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

QUALITY = {
    # percentage of 1080x1920, EEVEE samples, motion blur
    "draft": dict(percent=25, samples=4, motion_blur=False),
    "preview": dict(percent=50, samples=16, motion_blur=False),
    "final": dict(percent=100, samples=64, motion_blur=True),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--quality", choices=QUALITY, default="preview")
    p.add_argument("--render", action="store_true", help="render frames after building")
    p.add_argument("--frames", help="start:end subset, e.g. 120:120 for a still")
    p.add_argument("--out", help="frame output directory (default renders/<name>_<quality>)")
    p.add_argument("--stills", help="comma-separated frames to render individually after one build")
    p.add_argument("--resume", action="store_true",
                   help="skip frames that already exist in the output folder (restart an interrupted render)")
    return p.parse_args(argv)


def eevee_quality(scene, raytracing=True, fast_gi=True, shadow_rays=2, shadow_steps=8, exposure=0.0,
                  look="AgX - Medium High Contrast"):
    """Opt-in EEVEE Next features for environment scenes: screen-traced reflections and
    ambient occlusion / short-range bounce light, soft ray-marched shadows."""
    e = scene.eevee
    e.use_shadows = True
    e.shadow_ray_count = shadow_rays
    e.shadow_step_count = shadow_steps
    e.use_raytracing = raytracing
    if raytracing:
        e.ray_tracing_method = "SCREEN"
        e.ray_tracing_options.resolution_scale = "2"
        e.ray_tracing_options.use_denoise = True
        e.use_fast_gi = fast_gi
        e.fast_gi_method = "GLOBAL_ILLUMINATION"
        e.fast_gi_distance = 2.0
    scene.view_settings.exposure = exposure
    try:
        scene.view_settings.look = look
    except TypeError:
        pass
    return scene


def reset_scene():
    for collection in (
        bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights,
        bpy.data.cameras, bpy.data.curves, bpy.data.worlds, bpy.data.actions,
    ):
        for block in list(collection):
            collection.remove(block)
    return bpy.context.scene


def setup_render(scene, seconds, fps=30, quality="preview"):
    q = QUALITY[quality]
    r = scene.render
    r.engine = "BLENDER_EEVEE"
    r.resolution_x, r.resolution_y = 1080, 1920
    r.resolution_percentage = q["percent"]
    r.fps = fps
    r.use_motion_blur = q["motion_blur"]
    scene.frame_start = 1
    scene.frame_end = int(round(seconds * fps))
    scene.eevee.taa_render_samples = q["samples"]
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.film_transparent = False

    vs = scene.view_settings
    try:
        vs.view_transform = "AgX"
        vs.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    return scene


def finish(scene, name, args):
    """Save a .blend for inspection in the Blender UI, then optionally render frames."""
    os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "renders", f"{name}.blend"))

    if args.frames:
        start, end = (int(x) for x in args.frames.split(":"))
        scene.frame_start, scene.frame_end = start, end

    out = args.out or os.path.join(ROOT, "renders", f"{name}_{args.quality}")
    os.makedirs(out, exist_ok=True)
    if getattr(args, "stills", None):
        import time
        for frame in (int(x) for x in args.stills.split(",")):
            t = time.time()
            scene.frame_set(frame)
            scene.render.filepath = os.path.join(out, f"frame_{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[shorts] {name}: still {frame} in {time.time() - t:.1f}s -> {scene.render.filepath}")
        return
    scene.render.filepath = os.path.join(out, "frame_")
    if getattr(args, "resume", False):
        for f in os.listdir(out):
            path = os.path.join(out, f)
            if f.startswith("frame_") and os.path.getsize(path) == 0:  # placeholder of an interrupted frame
                os.remove(path)
        scene.render.use_overwrite = False
        scene.render.use_placeholder = True
    print(f"[shorts] {name}: frames {scene.frame_start}-{scene.frame_end} -> {out}")
    if args.render:
        bpy.ops.render.render(animation=True)
