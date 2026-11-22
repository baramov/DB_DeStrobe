import nuke
import math
import contextlib

STRENGTH_RANGE = (1, 50)
TRANSITION_RANGE = (0.01, 0.50)
TEMPORAL_RANGE = (0.1, 10.0)
TRANSITION_ZONE_MIN = 2
MOTION_EPS = 1e-6
SHORT_TRACK_WARN = 10
RETIMER_CLASSES = ('Kronos', 'OFlow2')

K_LOOKUP = 'lookup_curve'
K_ORIG = 'original_curve'
K_SMOOTH = 'smoothed_curve'
K_INFO = 'info_text'
K_STRENGTH = 'smooth_strength'
K_TRANS = 'transition_ratio'
K_TEMPORAL = 'temporal_weight'

K_TRACK_TRANSLATE = 'translate'

K_RETIME_TIMING = 'timing2'
K_RETIME_FIRST = 'input.first'
K_RETIME_LAST = 'input.last'
K_RETIME_FRAME = 'timingFrame2'
V_TIMING_FRAME = 'Frame'

REQUIRED_KNOBS = (K_LOOKUP, K_ORIG, K_SMOOTH, K_INFO,
                  K_STRENGTH, K_TRANS, K_TEMPORAL)


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def _motion_scale(original_curve_data):
    steps = []
    for i in range(1, len(original_curve_data)):
        px, py, _ = original_curve_data[i - 1]
        cx, cy, _ = original_curve_data[i]
        steps.append(math.hypot(cx - px, cy - py))
    return _median(steps)


def _missing_knobs(gizmo):
    available = gizmo.knobs()
    return [name for name in REQUIRED_KNOBS if name not in available]


def _join_warnings(messages):
    return "<br>".join([m for m in messages if m])


def _force_linear(knob, indices=None):
    targets = indices if indices is not None else (0,)
    for index in targets:
        curve = knob.animation(index)
        if curve is None:
            continue
        for key in curve.keys():
            key.interpolation = nuke.LINEAR


@contextlib.contextmanager
def _curve_write(knob, first, last, indices=None):
    targets = (None,) if indices is None else indices
    current = nuke.frame()
    stray = not (first <= current <= last)
    can_remove = hasattr(knob, 'removeKeyAt')
    parked = stray and not can_remove

    if parked:
        nuke.frame(first)
    try:
        for index in targets:
            if index is None:
                knob.clearAnimated()
                knob.setAnimated()
            else:
                knob.clearAnimated(index)
                knob.setAnimated(index)

        yield

        _force_linear(knob, indices)

        if stray and can_remove:
            for index in targets:
                if index is None:
                    knob.removeKeyAt(current)
                else:
                    knob.removeKeyAt(current, index)
    finally:
        if parked:
            nuke.frame(current)


def _write_scalar_curve(knob, pairs, first, last):
    with _curve_write(knob, first, last):
        for frame, value in pairs:
            knob.setValueAt(value, frame)


def _write_xy_curve(knob, triples, first, last):
    with _curve_write(knob, first, last, indices=(0, 1)):
        for x, y, frame in triples:
            knob.setValueAt(x, frame, 0)
            knob.setValueAt(y, frame, 1)


def _iter_retimers(gizmo):
    for node in gizmo.nodes():
        if node.Class() in RETIMER_CLASSES:
            yield node


def _format_info(input_range_info, smooth_range_info, warning_msg):
    html = ("<font size=3>Input Range: %s</font><br>"
            "<font size=3>Smooth Range: %s</font>"
            % (input_range_info, smooth_range_info))
    if warning_msg:
        html += ("<br><br><font size=3 color=yellow><b>WARNING: %s</b></font>"
                 % warning_msg)
    return html


def get_sequence_range(gizmo):
    source = gizmo.input(0)
    if source is None:
        return None, None, "No image connected to IMAGE input."

    try:
        first = int(source.firstFrame())
        last = int(source.lastFrame())
    except Exception as exc:
        return None, None, "Cannot read frame range from IMAGE input: %s" % exc

    if first > last:
        return None, None, "IMAGE input frame range is empty."

    return first, last, None


def get_tracker_data(tracker_node):
    if tracker_node is None:
        return None, "", "No tracker connected to TRACKER input."

    node_class = tracker_node.Class()
    if not node_class.startswith('Tracker'):
        return None, "", "TRACKER input must be a Tracker node, got %s." % node_class

    if K_TRACK_TRANSLATE not in tracker_node.knobs():
        return None, "", "Tracker node missing '%s' knob." % K_TRACK_TRANSLATE

    translate_knob = tracker_node[K_TRACK_TRANSLATE]
    if translate_knob.arraySize() != 2:
        return None, "", "Tracker '%s' must have 2 fields." % K_TRACK_TRANSLATE

    first_frames = []
    last_frames = []
    for index in (0, 1):
        curve = translate_knob.animation(index)
        if curve is None:
            continue
        keys = curve.keys()
        if not keys:
            continue
        times = [k.x for k in keys]
        first_frames.append(min(times))
        last_frames.append(max(times))

    if not first_frames:
        return None, "", ("Tracker '%s' has no animation keys "
                          "(expression or link driven?)." % K_TRACK_TRANSLATE)

    first_frame = int(math.ceil(max(first_frames)))
    last_frame = int(math.floor(min(last_frames)))

    if first_frame > last_frame:
        return None, "", "Tracker X and Y ranges do not overlap. Cannot smooth."

    warning_msgs = []
    track_length = last_frame - first_frame + 1

    if track_length < SHORT_TRACK_WARN:
        warning_msgs.append(
            "Track is very short (%d frames). Smoothing may be ineffective."
            % track_length)

    if min(first_frames) != max(first_frames) or max(last_frames) != min(last_frames):
        warning_msgs.append(
            "Tracker X and Y ranges differ. Using intersection.")

    if len(first_frames) < 2:
        warning_msgs.append(
            "Only one axis is animated. Other axis is constant.")

    original_curve_data = []
    for frame in range(first_frame, last_frame + 1):
        value = translate_knob.valueAt(frame)
        original_curve_data.append((value[0], value[1], frame))

    smooth_range_info = "%d-%d" % (first_frame, last_frame)
    return original_curve_data, smooth_range_info, _join_warnings(warning_msgs)


def check_retimers(gizmo):
    problems = []
    retimers = list(_iter_retimers(gizmo))

    if not retimers:
        return ["No Kronos or OFlow2 node found inside the gizmo."]

    for node in retimers:
        knobs = node.knobs()
        label = "%s (%s)" % (node.name(), node.Class())

        for name in (K_RETIME_TIMING, K_RETIME_FIRST, K_RETIME_LAST):
            if name not in knobs:
                problems.append("%s: knob '%s' not found." % (label, name))

        if K_RETIME_FRAME not in knobs:
            problems.append("%s: knob '%s' not found." %
                            (label, K_RETIME_FRAME))
            continue

        script = node[K_RETIME_FRAME].toScript()
        if K_LOOKUP not in script:
            problems.append(
                "%s: '%s' is not linked to parent.%s. Retime will have no effect."
                % (label, K_RETIME_FRAME, K_LOOKUP))

    return problems


def smooth_curve(original_curve_data, strength, transition_ratio):
    count = len(original_curve_data)
    if count == 0:
        return []

    strength = int(_clamp(strength, *STRENGTH_RANGE))
    ratio = _clamp(transition_ratio, *TRANSITION_RANGE)
    transition_zone = max(TRANSITION_ZONE_MIN, int(count * ratio))

    kernel_cache = {}
    smoothed_curve_data = []

    for i in range(count):
        x, y, frame = original_curve_data[i]

        edge_distance = min(i, count - 1 - i)
        falloff = min(1.0, edge_distance / float(transition_zone))

        if falloff == 0.0:
            smoothed_curve_data.append((x, y, frame))
            continue

        kernel = kernel_cache.get(falloff)
        if kernel is None:
            window = int(strength * falloff)
            sigma = (strength / 3.0) * falloff
            inv_two_sigma_sq = 1.0 / (2.0 * sigma * sigma)
            weights = [math.exp(-(d * d) * inv_two_sigma_sq)
                       for d in range(window + 1)]
            kernel = (window, weights)
            kernel_cache[falloff] = kernel

        window, weights = kernel
        start = max(0, i - window)
        end = min(count, i + window + 1)

        weighted_x = 0.0
        weighted_y = 0.0
        weight_sum = 0.0
        for j in range(start, end):
            weight = weights[abs(i - j)]
            weighted_x += original_curve_data[j][0] * weight
            weighted_y += original_curve_data[j][1] * weight
            weight_sum += weight

        smoothed_curve_data.append(
            (weighted_x / weight_sum, weighted_y / weight_sum, frame))

    return smoothed_curve_data


def lookup_curve(original_curve_data, smoothed_curve_data, temporal_weight):
    if not original_curve_data or not smoothed_curve_data:
        return []

    scale = _motion_scale(original_curve_data)
    if scale <= MOTION_EPS:
        return [(frame, float(frame)) for _, _, frame in smoothed_curve_data]

    weight_per_frame = _clamp(temporal_weight, *TEMPORAL_RANGE) * scale
    original_count = len(original_curve_data)

    lookup_data = []
    prev_source_frame = float(original_curve_data[0][2])
    start_index = 0

    for target_x, target_y, target_frame in smoothed_curve_data:
        while (start_index < original_count
               and original_curve_data[start_index][2] < prev_source_frame):
            start_index += 1

        if start_index >= original_count:
            start_index = original_count - 1

        best_score = math.inf
        best_index = start_index
        best_dist = 0.0

        for idx in range(start_index, original_count):
            orig_x, orig_y, orig_frame = original_curve_data[idx]

            if orig_frame > target_frame:
                if (orig_frame - target_frame) * weight_per_frame >= best_score:
                    break

            spatial_dist = math.hypot(orig_x - target_x, orig_y - target_y)
            score = spatial_dist + \
                abs(orig_frame - target_frame) * weight_per_frame

            if score < best_score:
                best_score = score
                best_index = idx
                best_dist = spatial_dist

        best_x, best_y, best_frame = original_curve_data[best_index]
        source_frame = float(best_frame)

        next_index = best_index + 1
        if next_index < original_count:
            next_x, next_y, next_frame = original_curve_data[next_index]
            next_dist = math.hypot(next_x - target_x, next_y - target_y)
            total = best_dist + next_dist
            if total > 0.0:
                blend = best_dist / total
                source_frame = best_frame + blend * (next_frame - best_frame)

        lookup_data.append((target_frame, source_frame))
        prev_source_frame = source_frame
        start_index = best_index

    return lookup_data


def extend_lookup(lookup_data, seq_first, seq_last):
    if not lookup_data:
        return ([(f, float(f)) for f in range(seq_first, seq_last + 1)],
                "No tracker data. Identity retime.")

    track_first = lookup_data[0][0]
    track_last = lookup_data[-1][0]

    if track_last < seq_first or track_first > seq_last:
        return ([(f, float(f)) for f in range(seq_first, seq_last + 1)],
                "Tracker range does not intersect sequence range. Identity retime.")

    warning = None
    if track_first < seq_first or track_last > seq_last:
        warning = "Tracker range exceeds sequence range. Lookup clipped."

    full = []
    for frame in range(seq_first, min(track_first, seq_last + 1)):
        full.append((frame, float(frame)))

    for frame, source in lookup_data:
        if seq_first <= frame <= seq_last:
            full.append((frame, source))

    for frame in range(max(track_last + 1, seq_first), seq_last + 1):
        full.append((frame, float(frame)))

    return full, warning


def write_results(gizmo, lookup_data, original_curve_data,
                  smoothed_curve_data, seq_first, seq_last,
                  input_range_info, smooth_range_info, warning_msg):
    _write_scalar_curve(gizmo[K_LOOKUP], lookup_data, seq_first, seq_last)

    if original_curve_data:
        track_first = original_curve_data[0][2]
        track_last = original_curve_data[-1][2]
        _write_xy_curve(gizmo[K_ORIG], original_curve_data,
                        track_first, track_last)
        _write_xy_curve(gizmo[K_SMOOTH],
                        smoothed_curve_data, track_first, track_last)

    for node in _iter_retimers(gizmo):
        knobs = node.knobs()

        if K_RETIME_TIMING in knobs:
            node[K_RETIME_TIMING].setValue(V_TIMING_FRAME)

        for name, value in ((K_RETIME_FIRST, seq_first),
                            (K_RETIME_LAST, seq_last)):
            if name in knobs:
                node[name].clearAnimated()
                node[name].setValue(value)

    gizmo[K_INFO].setValue(
        _format_info(input_range_info, smooth_range_info, warning_msg))


def calculate():
    gizmo = nuke.thisNode()

    missing = _missing_knobs(gizmo)
    if missing:
        nuke.message("DB_DeStrobe: missing knobs:\n  " + "\n  ".join(missing))
        return

    seq_first, seq_last, range_error = get_sequence_range(gizmo)
    if range_error:
        gizmo[K_INFO].setValue(_format_info("-", "-", range_error))
        return

    input_range_info = "%d-%d" % (seq_first, seq_last)

    original_curve_data, smooth_range_info, warning_msg = \
        get_tracker_data(gizmo.input(1))

    if original_curve_data is None:
        gizmo[K_INFO].setValue(_format_info(
            input_range_info, "-", warning_msg))
        return

    strength = gizmo[K_STRENGTH].value()
    transition_ratio = gizmo[K_TRANS].value()
    temporal_weight = gizmo[K_TEMPORAL].value()

    smoothed_curve_data = smooth_curve(
        original_curve_data, strength, transition_ratio)
    raw_lookup = lookup_curve(
        original_curve_data, smoothed_curve_data, temporal_weight)
    lookup_data, extend_warning = extend_lookup(
        raw_lookup, seq_first, seq_last)

    warnings = [warning_msg]
    warnings.extend(check_retimers(gizmo))
    warnings.append(extend_warning)
    warning_msg = _join_warnings(warnings)

    undo = nuke.Undo()
    undo.begin("DB_DeStrobe Calculate")
    try:
        write_results(gizmo, lookup_data, original_curve_data,
                      smoothed_curve_data, seq_first, seq_last,
                      input_range_info, smooth_range_info, warning_msg)
    finally:
        undo.end()


calculate()
