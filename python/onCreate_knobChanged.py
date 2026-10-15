onCreate_code = """

n = nuke.thisNode()
h_knobs = n.knobs()

n['smooth_strength'].setFlag(0x0000000000000002)
n['smooth_strength'].setRange(1,50)
n['smooth_strength'].setDefaultValue([10])

h_knobs['oflowVectorDetailLocal'].setVisible(True)
h_knobs['oflowSmoothnessLocal'].setVisible(True)
h_knobs['kronosVectorDetailReg'].setVisible(False)
h_knobs['kronosStrengthReg'].setVisible(False)

"""

knobChanged_code = """

n = nuke.thisNode()
k = nuke.thisKnob()
h_knobs = n.knobs()

if k and k.name() == 'retime_engine':
    engine = int(k.getValue())

    if engine == 0:
        h_knobs['oflowVectorDetailLocal'].setVisible(True)
        h_knobs['oflowSmoothnessLocal'].setVisible(True)
        h_knobs['kronosVectorDetailReg'].setVisible(False)
        h_knobs['kronosStrengthReg'].setVisible(False)
            
    elif engine == 1:
        h_knobs['oflowVectorDetailLocal'].setVisible(False)
        h_knobs['oflowSmoothnessLocal'].setVisible(False)
        h_knobs['kronosVectorDetailReg'].setVisible(True)
        h_knobs['kronosStrengthReg'].setVisible(True)

"""

nuke.selectedNode()['knobChanged'].setValue(knobChanged_code)
nuke.selectedNode()['onCreate'].setValue(onCreate_code)