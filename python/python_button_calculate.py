import math

def get_tracker_data(tracker_node):

    if tracker_node is None:
        return None, "", "No Tracker node connected to Tracker Input."
    
    node_class = tracker_node.Class()
    if not node_class.startswith('Tracker'):
        return None, "", f"Tracker Input must be a Tracker node, got {node_class}."
    
    if 'translate' not in tracker_node.knobs():
        return None, "", "Tracker node missing <i>translate</i> knob."

    translate_x = tracker_node['translate'].animation(0)
    translate_y = tracker_node['translate'].animation(1)

    first_frames = []
    last_frames = []

    if translate_x and translate_x.keys():
        keys_x = translate_x.keys()
        first_frames.append(int(keys_x[0].frame))
        last_frames.append(int(keys_x[-1].frame))

    if translate_y and translate_y.keys():
        keys_y = translate_y.keys()
        first_frames.append(int(keys_y[0].frame))
        last_frames.append(int(keys_y[-1].frame))

    if not first_frames:
        return None, "", "Tracker <i>translate</i> knob has no animation keys."

    first_frame = max(first_frames)
    last_frame = min(last_frames)

    if first_frame > last_frame:
        return None, "", "Tracker <i>translate.x</i> and <i>translate.y</i> ranges do not overlap. Cannot smooth."

    warning_msgs = []
    track_length = last_frame - first_frame + 1
    
    if track_length < 10:
        warning_msgs.append("Track < 10 frames. Smoothing may be ineffective.")
        
    if min(first_frames) != max(first_frames) or max(last_frames) != min(last_frames):
        warning_msgs.append("Tracker <i>translate.x</i> and <i>translate.y</i> ranges differ. Using intersection.")
        
    warning_msg = "<br>".join(warning_msgs)

    original_curve_data = []
    translate_knob = tracker_node['translate']
    
    for f in range(first_frame, last_frame + 1):
        val = translate_knob.valueAt(f)
        original_curve_data.append((val[0], val[1], f))

    smooth_range_info = f"{first_frame}-{last_frame}"

    return original_curve_data, smooth_range_info, warning_msg


def smooth_curve(original_curve_data, strength, transition):

    N = len(original_curve_data)
    if N == 0:
        return []

    transition_ratio = max(0.01, min(0.50, transition))
    transition_zone = max(2, int(N * transition_ratio))

    smoothed_curve_data = []

    for i in range(N):
        x, y, frame = original_curve_data[i]

        if transition_zone > 0:
            falloff = min(1.0, min(i, N - 1 - i) / transition_zone)
        else:
            falloff = 0.0

        if falloff == 0.0:
            smoothed_curve_data.append((x, y, frame))
            continue

        window = int(strength * falloff)
        sigma = (strength / 3.0) * falloff

        weighted_x = 0.0
        weighted_y = 0.0
        weight_sum = 0.0

        start_j = max(0, i - window)
        end_j = min(N, i + window + 1)

        for j in range(start_j, end_j):
            dist = abs(i - j)
            weight = math.exp(-(dist ** 2) / (2 * sigma ** 2))
            weighted_x += original_curve_data[j][0] * weight
            weighted_y += original_curve_data[j][1] * weight
            weight_sum += weight

        if weight_sum > 0:
            smoothed_x = weighted_x / weight_sum
            smoothed_y = weighted_y / weight_sum
        else:
            smoothed_x = x
            smoothed_y = y

        smoothed_curve_data.append((smoothed_x, smoothed_y, frame))

    return smoothed_curve_data