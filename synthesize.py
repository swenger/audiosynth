#!/usr/bin/env python

import os
from numpy import concatenate, floor, log
from scipy.io import wavfile
from pylab import figure, axes, title, show
from matplotlib.lines import Line2D

from cutsearch import analyze
from geneticpathsearch import path_search
from utilities import make_lookup, ptime, frametime
from timeplots import FrameTimeLocator, FrameTimeFormatter

def main(infilename, outfilename, pathfilename,
        num_cuts, num_keep, block_length_shrink, num_levels, weight_factor, cutfilename,
        source_keypoints, target_keypoints, cost_factor, duration_factor, repetition_factor, num_paths):
    assert target_keypoints[0] == 0, "first target key point must be 0"
    assert len(source_keypoints) == len(target_keypoints), "there must be equal numbers of source and target key points"
    assert len(source_keypoints) >= 2, "there must be at least two key points"

    cut_parameter_names = ["num_levels", "num_cuts", "num_keep", "block_length_shrink", "weight_factor"]

    class CutFileError(Exception):
        def __init__(self, message):
            super(Exception, self).__init__(message)

    # read file
    rate, data = wavfile.read(infilename)

    num_levels = min(int(floor(log(len(data)) / log(block_length_shrink))) + 1, float("inf") if num_levels is None else num_levels)
    assert block_length_shrink ** (num_levels - 1) <= len(data)
    source_keypoints = [len(data) if x is None else rate * x for x in source_keypoints]
    target_keypoints = [rate * x for x in target_keypoints]

    print "input file: %s (%s, %s fps)" % (infilename, frametime(rate, len(data)), rate)
    print "output file: %s" % outfilename
    print
    print "%d levels" % num_levels
    print "finding %d cuts" % num_cuts
    print "keeping %s cuts" % (num_keep or "all")
    print "shrinking by factor %d" % block_length_shrink
    print "weight factor: %s" % weight_factor
    print
    print "key points: " + ", ".join("%s->%s" % (frametime(rate, s), frametime(rate, t)) for s, t in zip(source_keypoints, target_keypoints))
    print "cost factor: %s" % cost_factor
    print "duration factor: %s" % duration_factor
    print "repetition factor: %s" % repetition_factor
    print "finding %d complete paths" % num_paths
    print

    # find good cuts
    try: # try to read best from cutfilename
        if cutfilename is None:
            raise CutFileError("cut file not specified")
        if os.stat(cutfilename).st_mtime <= os.stat(infilename).st_mtime: # check if cutfile is newer than infile
            raise CutFileError("cut file too old")
        with open(cutfilename) as f:
            print "Loading cuts from %s." % cutfilename
            header = dict()
            best = []
            for line in f.xreadlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    header[key.strip()] = eval(value.strip())
                else:
                    a, b, c = line.split()
                    best.append((int(a), int(b), float(c)))
            # check if parameters are the same
            for name in cut_parameter_names:
                if name not in header or header[name] != locals()[name]:
                    raise CutFileError("cut parameter %s has changed" % name)
    except (OSError, IOError, CutFileError): # cutfile is unreadable
        print "Computing cuts."
        best = analyze(data, block_length_shrink ** (num_levels - 1), num_cuts, block_length_shrink, weight_factor=weight_factor)
        if num_keep:
            best = best[:num_keep]

        # write cuts to file
        if cutfilename is not None:
            with open(cutfilename, "w") as f:
                print "Writing cuts to %s." % cutfilename
                for name in cut_parameter_names:
                    print >> f, "%s = %s" % (name, repr(locals()[name]))
                for x in best:
                    print >> f, "%d %d %e" % x

    # perform graph search TODO find a globally optimal path through all keypoints at once
    segments = path_search(source_keypoints, target_keypoints, best, random_seed=0) # TODO pass algorithm parameters on command line

    # synthesize
    result = concatenate([data[s.start:s.end] for s in segments])

    # write synthesized sound as wav
    wavfile.write(outfilename, rate, result)

    # write path as text file
    if pathfilename:
        with open(pathfilename, "w") as f:
            for s in segments:
                print >> f, s.start, s.end, frametime(rate, s.start), frametime(rate, s.end)

    # visualize cuts
    figure()
    title("cut positions")
    ax = axes()
    ax.xaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.xaxis.set_minor_locator(FrameTimeLocator(rate, step_size=block_length_shrink ** (num_levels - 1) / rate))
    ax.xaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.yaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.yaxis.set_minor_locator(FrameTimeLocator(rate, step_size=block_length_shrink ** (num_levels - 1) / rate))
    ax.yaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.grid(True, which="minor")
    ax.set_aspect("equal")
    ax.scatter([x[0] for x in best], [x[1] for x in best], c=[x[2] for x in best])
    ax.set_xlim(0, len(data))
    ax.set_ylim(0, len(data))

    # visualize path
    figure()
    title("jumps")
    ax = axes()
    ax.xaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.xaxis.set_minor_locator(FrameTimeLocator(rate, 100))
    ax.xaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.yaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.yaxis.set_minor_locator(FrameTimeLocator(rate, 100))
    ax.yaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.set_aspect("equal")
    ax.set_xlim(0, len(data))
    ax.set_ylim(0, len(result))
    
    # plot playback segments
    start = 0
    for segment in segments:
        ax.add_artist(Line2D((segment.start, segment.end), (start, start + segment.duration)))
        start += segment.duration

    # plot jumps
    start = 0
    for a, b in zip(segments, segments[1:]):
        start += a.duration
        ax.add_artist(Line2D((a.end, b.start), (start, start), color="green"))

    # plot keypoints
    ax.scatter(source_keypoints, target_keypoints, color="red", marker="x")

    show()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    
    general_group = parser.add_argument_group("general arguments")
    general_group.add_argument("-i", "--infile", help="input wave file", dest="infilename", required=True)
    general_group.add_argument("-o", "--outfile", help="output wave file", dest="outfilename", required=True)
    general_group.add_argument("-p", "--pathfile", help="output path file", dest="pathfilename", required=False)

    cuts_group = parser.add_argument_group("cut search arguments")
    cuts_group.add_argument("-f", "--cachefile", type=str, help="file for caching cuts", dest="cutfilename")
    cuts_group.add_argument("-c", "--cuts", type=int, default=256, help="cuts on first level", dest="num_cuts")
    cuts_group.add_argument("-k", "--keep", type=make_lookup(int, all=0), default=40, help="cuts to keep", dest="num_keep")
    cuts_group.add_argument("-s", "--shrink", type=int, default=16, help="block shrinkage per level", dest="block_length_shrink")
    cuts_group.add_argument("-l", "--levels", type=make_lookup(int, max=None), default=5, help="number of levels", dest="num_levels")
    cuts_group.add_argument("-w", "--weightfactor", type=float, default=1.2, help="weight factor between levels", dest="weight_factor")

    path_group = parser.add_argument_group("path search arguments")
    path_group.add_argument("-S", "--source", type=make_lookup(ptime, start=0, end=None), nargs="*", help="source key points", dest="source_keypoints", required=True)
    path_group.add_argument("-T", "--target", type=make_lookup(ptime, start=0), nargs="*", help="target key points", dest="target_keypoints", required=True)
    path_group.add_argument("-C", "--costfactor", type=float, default=1.0, help="cost factor", dest="cost_factor")
    path_group.add_argument("-D", "--durationfactor", type=float, default=1.0, help="duration factor", dest="duration_factor")
    path_group.add_argument("-R", "--repetitionfactor", type=float, default=1.0e9, help="repetition factor", dest="repetition_factor")
    path_group.add_argument("-P", "--paths", type=int, default=32, help="number of paths to find", dest="num_paths")

    main(**parser.parse_args().__dict__)

    # e.g. synthesize.py -i playmateoftheyear.wav -o result.wav -P 10 -l max -S start end -T start 2:40 -f playmateoftheyear.cuts

