def get_tracker_data(tracker_node):
    
    # Reads translate knob data from Tracker node.
    # Returns translate curve, shoothing range and warning messages
    
    # Check tracker input
    if tracker_node is None:
        return None, "", "No Tracker connected to Tracker Input."
    
    node_class = tracker_node.Class()
    if not node_class.startswith('Tracker'):
        return None, "", f"Tracker Input must be a Tracker node, got {node_class}."
    
    if 'translate' not in tracker_node.knobs():
        return None, "", "Tracker node missing <i>translate</i> knob."

    # Define smoothing range
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

    # Get data
    original_curve_data = []
    translate_knob = tracker_node['translate']
    
    for f in range(first_frame, last_frame + 1):
        val = translate_knob.valueAt(f)
        original_curve_data.append((val[0], val[1], f))

    # Smoothing range info string
    smooth_range_info = f"{first_frame}-{last_frame}"

    return original_curve_data, smooth_range_info, warning_msg