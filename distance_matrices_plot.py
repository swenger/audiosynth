#!/usr/bin/env python

import sys

from numpy import load, isfinite
from pylab import figure, axes, draw, show

d = load(sys.argv[1]).item() # .npy file generated using the distance_matrices_filename option of HierarchicalCutsPlot

levels = sorted(set(x[1] - x[0] for x in d))

for l in reversed(levels[-3:]):
    f = figure()
    a = f.add_axes(axes())
    a.hold(True)

    vmin = min(m.min() for (left, right, bottom, top), m in d.items() if right - left == l)
    vmax = max(m[isfinite(m)].max() for (left, right, bottom, top), m in d.items() if right - left == l)
    
    for (left, right, bottom, top), m in d.items():
        if right - left == l:
            a.imshow(m[::-1, ::-1], origin="lower", extent=(left, right, bottom, top), vmin=vmin, vmax=vmax)
    a.set_xlim(min(x[0] for x in d), max(x[1] for x in d))
    a.set_ylim(min(x[2] for x in d), max(x[3] for x in d))
    a.set_xticks([left for (left, right, bottom, top), m in d.items() if right - left == levels[-2]])
    a.set_yticks([bottom for (left, right, bottom, top), m in d.items() if right - left == levels[-2]])

draw()
show()

