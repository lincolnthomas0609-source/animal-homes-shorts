"""Easing curves and tweens.

Tweens are baked as one keyframe per frame, so the motion is defined entirely by
the easing function here and doesn't depend on Blender's F-curve API.
"""

import math


def linear(t):
    return t


def ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in(t):
    return t ** 3


def ease_out_back(t, overshoot=1.7):
    c3 = overshoot + 1
    return 1 + c3 * (t - 1) ** 3 + overshoot * (t - 1) ** 2


def smooth_pulse(t):
    """0 -> 1 -> 0 over t in [0, 1]."""
    return math.sin(math.pi * t) ** 2


def _lerp(a, b, e):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * e for x, y in zip(a, b))
    return a + (b - a) * e


# Last keyed (frame, value) per animated property, so gaps between animations hold still.
_last_key = {}


def _snapshot(value):
    return tuple(value) if hasattr(value, "__len__") and not isinstance(value, str) else value


def hold_before(target, prop, start):
    """Pin target.<prop> to its previous value up to frame start - 1.

    Without this, Blender interpolates across the gap between two animations of the
    same property (an animal would slowly turn toward its next walk months early).
    Before the first animation of a property, its current (set-up) value is keyed at
    frame 1. Called automatically by tween, follow_path, and key.
    Build animations of a property in chronological order for this to work.
    """
    k = (target.as_pointer(), prop)
    if k not in _last_key:
        if start > 1:
            target.keyframe_insert(prop, frame=1)
            _last_key[k] = (1, _snapshot(getattr(target, prop)))
        return
    frame, value = _last_key[k]
    if start > frame + 1:
        current = _snapshot(getattr(target, prop))
        setattr(target, prop, value)
        target.keyframe_insert(prop, frame=start - 1)
        setattr(target, prop, current)


def key(target, prop, frame, value=None):
    """Keyframe target.<prop> at frame (optionally setting value first), tracking holds."""
    if value is not None:
        setattr(target, prop, value)
    target.keyframe_insert(prop, frame=frame)
    k = (target.as_pointer(), prop)
    prev = _last_key.get(k)
    if prev is None or frame >= prev[0]:
        _last_key[k] = (frame, _snapshot(getattr(target, prop)))


def tween(target, prop, start, end, a, b, ease=ease_in_out):
    """Animate target.<prop> from a to b between frames start and end (inclusive).

    target can be any animatable datablock or struct: an object, a light,
    a node socket (prop="default_value"), etc. a and b may be numbers or tuples.
    """
    hold_before(target, prop, start)
    span = max(end - start, 1)
    for f in range(start, end + 1):
        key(target, prop, f, _lerp(a, b, ease((f - start) / span)))


def _monotone_slopes(xs, ys):
    """Fritsch-Carlson slopes: a smooth curve through the keys that never overshoots them."""
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [0.0] * n  # zero slope at the first and last key = ease in and out
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        if a * a + b * b > 9:
            tau = 3 / math.sqrt(a * a + b * b)
            m[i], m[i + 1] = tau * a * d[i], tau * b * d[i]
    return m


def smooth_keys(target, prop, keys):
    """Animate target.<prop> through [(frame, value), ...] with continuous velocity.

    Unlike chained tweens (which stop at every key), motion only eases at the first and
    last key, so a camera or cut can pass through intermediate poses without halting.
    Values may be numbers or tuples (each component is interpolated separately).
    """
    keys = sorted(keys, key=lambda k: k[0])
    frames = [k[0] for k in keys]
    vec = isinstance(keys[0][1], (tuple, list))
    comps = list(zip(*[k[1] for k in keys])) if vec else [[k[1] for k in keys]]
    slopes = [_monotone_slopes(frames, list(c)) for c in comps]
    hold_before(target, prop, frames[0])
    seg = 0
    for f in range(frames[0], frames[-1] + 1):
        while seg < len(frames) - 2 and f > frames[seg + 1]:
            seg += 1
        x0, x1 = frames[seg], frames[seg + 1]
        h = x1 - x0
        t = (f - x0) / h
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        val = [h00 * c[seg] + h10 * h * m[seg] + h01 * c[seg + 1] + h11 * h * m[seg + 1]
               for c, m in zip(comps, slopes)]
        key(target, prop, f, tuple(val) if vec else val[0])


def seconds(t, fps=30):
    """Convert seconds to a 1-based frame number."""
    return int(round(t * fps)) + 1


def load_timing(path, fps=30):
    """Narration line timings from voiceover.py / import_lines.py, with frame numbers added.

    Returns a list of dicts: text, start, end (seconds), f0, f1 (frames).
    """
    import json
    with open(path) as f:
        lines = json.load(f)
    for line in lines:
        line["f0"] = seconds(line["start"], fps)
        line["f1"] = seconds(line["end"], fps)
    return lines


def stagger(items, start, end, duration, key=None):
    """Spread item start frames across [start, end - duration], ordered by key.

    Returns a list of (item, first_frame) pairs. Pair with tween() for build-ups:
        for obj, f in stagger(sticks, 1, 60, 8, key=lambda o: o.location.z):
            tween(obj, "scale", f, f + 8, (0, 0, 0), obj.scale[:], ease_out_back)
    """
    ordered = sorted(items, key=key) if key else list(items)
    span = max(end - duration - start, 0)
    n = max(len(ordered) - 1, 1)
    return [(item, start + round(span * i / n)) for i, item in enumerate(ordered)]


def smooth_path(points, samples_per_segment=12):
    """Catmull-Rom spline through points, returned as a dense list of 3D tuples."""
    pts = [tuple(p) for p in points]
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(samples_per_segment):
            t = s / samples_per_segment
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                for a, b, c, d in zip(p0, p1, p2, p3)
            ))
    out.append(pts[-1])
    return out


def _point_at(path, cumulative, dist):
    for i in range(1, len(path)):
        if cumulative[i] >= dist or i == len(path) - 1:
            seg = cumulative[i] - cumulative[i - 1] or 1e-9
            t = min(max((dist - cumulative[i - 1]) / seg, 0.0), 1.0)
            a, b = path[i - 1], path[i]
            pos = tuple(x + (y - x) * t for x, y in zip(a, b))
            tangent = tuple(y - x for x, y in zip(a, b))
            return pos, tangent


def follow_path(obj, path, start, end, ease=ease_in_out, orient=True):
    """Move obj along a dense path (see smooth_path) at constant speed shaped by ease.

    With orient=True the object's +X axis points along the direction of travel.
    """
    cumulative = [0.0]
    for a, b in zip(path, path[1:]):
        cumulative.append(cumulative[-1] + math.dist(a, b))
    total = cumulative[-1]
    obj.rotation_mode = "XYZ"
    span = max(end - start, 1)
    prev_yaw = obj.rotation_euler.z
    hold_before(obj, "location", start)
    if orient:
        hold_before(obj, "rotation_euler", start)
    for f in range(start, end + 1):
        pos, (tx, ty, tz) = _point_at(path, cumulative, total * ease((f - start) / span))
        key(obj, "location", f, pos)
        if orient:
            yaw = math.atan2(ty, tx)
            # Unwrap so the angle never jumps by a full turn (that would spin under motion blur).
            yaw += 2 * math.pi * round((prev_yaw - yaw) / (2 * math.pi))
            prev_yaw = yaw
            pitch = math.atan2(tz, math.hypot(tx, ty))
            key(obj, "rotation_euler", f, (0.0, -pitch, yaw))
