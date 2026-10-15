import nuke

onCreate_code = """

n = nuke.thisNode()
h_knobs = n.knobs()
autolabel_string = f"nuke.thisNode().name() + chr(10) + '(' + nuke.thisNode()['retime_engine'].value() + ')'"

n['autolabel'].setValue(autolabel_string)

n['smooth_strength'].setFlag(0x0000000000000002)
n['smooth_strength'].setRange(1,50)
n['smooth_strength'].setDefaultValue([10])

h_knobs['oflowVectorDetailLocal'].setVisible(True)
h_knobs['oflowSmoothnessLocal'].setVisible(True)
h_knobs['oflowResampleType'].setVisible(True)
h_knobs['kronosVectorDetailReg'].setVisible(False)
h_knobs['kronosStrengthReg'].setVisible(False)
h_knobs['kronosResampleType'].setVisible(False)

"""

knobChanged_code = """

n = nuke.thisNode()
k = nuke.thisKnob()

if k and k.name() == 'retime_engine':
    engine = int(k.getValue())
    h_knobs = n.knobs()
    autolabel_string = f"nuke.thisNode().name() + chr(10) + '(' + nuke.thisNode()['retime_engine'].value() + ')'"

    start_ops = 'n = nuke.thisNode()\\nh_knobs = n.knobs()'

    integer_slider = "n['smooth_strength'].setFlag(0x0000000000000002)\\nn['smooth_strength'].setRange(1,50)\\nn['smooth_strength'].setDefaultValue([10])"

    def toggle_engine_knobs(oflow):
        h_knobs['oflowVectorDetailLocal'].setVisible(oflow)
        h_knobs['oflowSmoothnessLocal'].setVisible(oflow)
        h_knobs['oflowResampleType'].setVisible(oflow)
        h_knobs['kronosVectorDetailReg'].setVisible(not oflow)
        h_knobs['kronosStrengthReg'].setVisible(not oflow)
        h_knobs['kronosResampleType'].setVisible(not oflow)

        return f"h_knobs['oflowVectorDetailLocal'].setVisible({oflow})\\nh_knobs['oflowSmoothnessLocal'].setVisible({oflow})\\nh_knobs['oflowResampleType'].setVisible({oflow})\\nh_knobs['kronosVectorDetailReg'].setVisible({not oflow})\\nh_knobs['kronosStrengthReg'].setVisible({not oflow})\\nh_knobs['kronosResampleType'].setVisible({not oflow})".strip()

    if engine == 0:
        engine_knob_pos = toggle_engine_knobs(oflow=True)
            
    elif engine == 1:
        engine_knob_pos = toggle_engine_knobs(oflow=False)

    n['onCreate'].setValue(f'{start_ops}\\n{integer_slider}\\n{engine_knob_pos}')
    n['autolabel'].setValue(autolabel_string)

"""

nuke.selectedNode()['knobChanged'].setValue(knobChanged_code.strip())
nuke.selectedNode()['onCreate'].setValue(onCreate_code.strip())