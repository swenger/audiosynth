#!/usr/bin/env python

import os

from scipy.io import wavfile
from pylab import figure, axes, title, show
from matplotlib.lines import Line2D

from datafile import read_datafile, write_datafile
from utilities import make_lookup, ptime, frametime
from timeplots import FrameTimeLocator, FrameTimeFormatter
from algorithms.algorithm import Cut

from algorithms.cuts import algorithms as cuts_algorithms
from algorithms.path import algorithms as path_algorithms

def main(infilename, cutfilename, pathfilename, outfilename, source_keypoints, target_keypoints, cuts_algo, path_algo):
    assert target_keypoints[0] == 0, "first target key point must be 0"
    assert len(source_keypoints) == len(target_keypoints), "there must be equal numbers of source and target key points"
    assert len(source_keypoints) >= 2, "there must be at least two key points"

    rate, data = wavfile.read(infilename)
    source_keypoints = [len(data) if x is None else int(round(rate * x)) for x in source_keypoints]
    target_keypoints = [int(round(rate * x)) for x in target_keypoints]

    print "input file: %s (%s, %s fps)" % (infilename, frametime(rate, len(data)), rate)
    print "output file: %s" % outfilename
    print "key points: " + ", ".join("%s->%s" % (frametime(rate, s), frametime(rate, t)) for s, t in zip(source_keypoints, target_keypoints))
    print

    # try to load cuts from file
    if cutfilename:
        try:
            if os.stat(cutfilename).st_mtime > os.stat(infilename).st_mtime:
                print "Reading cuts from %s." % cutfilename
                contents = read_datafile(cutfilename)
                if contents["algorithm"] != cuts_algo.__class__.__name__:
                    print "Algorithm has changed, recomputing cuts."
                else:
                    changed_parameters = cuts_algo.changed_parameters(contents)
                    if changed_parameters:
                        print "Parameters have changed (%s), recomputing cuts." % ", ".join(changed_parameters)
                    else:
                        best = [Cut(int(start), int(end), float(error)) for (start, start_time, end, end_time, error) in contents["data"]]
            else:
                print "Cut file too old, recomputing cuts."""
        except (OSError, IOError):
            print "Cut file could not be read, recomputing cuts."""
        except (KeyError, SyntaxError):
            print "Cut file could not be parsed, recomputing cuts."""
    else:
        print "No cut file specified, recomputing cuts."""

    # recompute cuts if necessary
    if "best" not in locals():
        best = cuts_algo(data)

        # write cuts to file
        if cutfilename is not None:
            print "Writing cuts to %s." % cutfilename
            contents = cuts_algo.get_parameters()
            contents["algorithm"] = cuts_algo.__class__.__name__
            contents["length"] = len(data)
            contents["rate"] = rate
            contents["data"] = [(start, frametime(rate, start), end, frametime(rate, end), error) for (start, end, error) in best]
            write_datafile(cutfilename, contents)

    # perform graph search
    path = path_algo(source_keypoints, target_keypoints, best)

    # write path to file
    if pathfilename:
        contents = path_algo.get_parameters()
        contents["algorithm"] = path_algo.__class__.__name__
        contents["length"] = len(data)
        contents["rate"] = rate
        contents["source_keypoints"] = source_keypoints
        contents["target_keypoints"] = target_keypoints
        contents["data"] = [(s.start, frametime(rate, s.start), s.end, frametime(rate, s.end)) for s in path.segments]
        write_datafile(pathfilename, contents)

    # write synthesized sound as wav
    if outfilename:
        wavfile.write(outfilename, rate, path.synthesize(data))

    # visualize cuts
    figure()
    title("cut positions")
    ax = axes()
    ax.xaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.xaxis.set_minor_locator(FrameTimeLocator(rate, 100))
    ax.xaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.yaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.yaxis.set_minor_locator(FrameTimeLocator(rate, 100))
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
    ax.set_ylim(0, path.duration)
    
    # plot playback segments
    start = 0
    for segment in path.segments:
        ax.add_artist(Line2D((segment.start, segment.end), (start, start + segment.duration)))
        start += segment.duration

    # plot jumps
    start = 0
    for a, b in zip(path.segments, path.segments[1:]):
        start += a.duration
        ax.add_artist(Line2D((a.end, b.start), (start, start), color="green"))

    # plot keypoints
    ax.scatter(source_keypoints, target_keypoints, color="red", marker="x")

    show()

def format_parameter(pname, defaults):
    return "%s=%s" % (pname, defaults[pname]) if pname in defaults else "%s" % pname

def format_algorithm(name, algo):
    defaults = algo.get_parameter_defaults()
    return "  %s %s" % (name, " ".join(format_parameter(pname, defaults) for pname in algo.get_parameter_names()))

if __name__ == "__main__":
    import argparse

    cuts_epilog = "Cut search algorithms:\n" + "\n".join(format_algorithm(name, algo) for name, algo in cuts_algorithms.items())
    path_epilog = "Path search algorithms:\n" + "\n".join(format_algorithm(name, algo) for name, algo in path_algorithms.items())

    parser = argparse.ArgumentParser(description=main.__doc__, fromfile_prefix_chars="@", epilog=cuts_epilog+"\n"+path_epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--infile", dest="infilename", required=True,
            help="input wave file")
    parser.add_argument("-c", "--cutsfile", dest="cutfilename",
            help="file for caching cuts")
    parser.add_argument("-p", "--pathfile", dest="pathfilename",
            help="output path file")
    parser.add_argument("-o", "--outfile", dest="outfilename",
            help="output wave file")
    parser.add_argument("-s", "--source", dest="source_keypoints", type=make_lookup(ptime, start=0, end=None), nargs="*", required=True,
            help="source key points (in seconds, or hh:mm:ss.sss); special values 'start' and 'end' are allowed")
    parser.add_argument("-t", "--target", dest="target_keypoints", type=make_lookup(ptime, start=0), nargs="*", required=True,
            help="target key points (in seconds, or hh:mm:ss.sss); special value 'start' is allowed")
    parser.add_argument("-C", "--cutsalgo", dest="cuts_algo", default= ["HierarchicalCutsAlgorithm"], nargs="*",
            help="cuts algorithm and parameters as key=value list")
    parser.add_argument("-P", "--pathalgo", dest="path_algo", default=["GeneticPathAlgorithm"], nargs="*",
            help="path algorithm and parameters as key=value list")
    args = parser.parse_args()

    cuts_algo_class = cuts_algorithms[args.cuts_algo[0]]
    cuts_algo_parameters = dict(x.split("=", 1) for x in args.cuts_algo[1:])
    args.cuts_algo = cuts_algo_class(**cuts_algo_parameters)
    print "Cuts algorithm: %s" % args.cuts_algo.__class__.__name__

    path_algo_class = path_algorithms[args.path_algo[0]]
    path_algo_parameters = dict(x.split("=", 1) for x in args.path_algo[1:])
    args.path_algo = path_algo_class(**path_algo_parameters)
    print "Path algorithm: %s" % args.path_algo.__class__.__name__

    main(**args.__dict__)

    # e.g. synthesize.py -i playmateoftheyear.wav -c playmateoftheyear.cuts -p playmateoftheyear.path -o result.wav -s start end -t start 2:40
    #                    -C hierarchical num_cuts=256 num_keep=40 num_levels=max weight_factor=1.2 -P genetic random_seed=0

