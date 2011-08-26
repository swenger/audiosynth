#!/usr/bin/env python

import os
import time

from scipy.io import wavfile
from pylab import figure, axes, title, show
from matplotlib.lines import Line2D

from datafile import read_datafile, write_datafile
from utilities import make_lookup, ptime, frametime
from timeplots import FrameTimeLocator, FrameTimeFormatter
from algorithms.algorithm import Cut, Segment, Keypoint, Path

from algorithms.cuts import algorithms as cuts_algorithms
from algorithms.path import algorithms as path_algorithms

def read_cuts(infilename, cutsfilename, cuts_algo):
    best = None
    if cutsfilename is not None:
        try:
            if os.stat(cutsfilename).st_mtime > os.stat(infilename).st_mtime:
                print "Reading cuts from %s." % cutsfilename
                contents = read_datafile(cutsfilename)
                if contents["algorithm"] != cuts_algo.__class__.__name__:
                    print "Algorithm has changed, recomputing cuts."
                else:
                    changed_parameters = cuts_algo.changed_parameters(contents)
                    if changed_parameters:
                        print "Parameters have changed (%s), recomputing cuts." % ", ".join(changed_parameters)
                    else:
                        best = [Cut(int(start), int(end), float(error)) for start, start_time, end, end_time, error in contents["data"]]
            else:
                print "Cut file too old, recomputing cuts."""
        except (OSError, IOError):
            print "Cut file could not be read, recomputing cuts."""
        except (KeyError, SyntaxError):
            print "Cut file could not be parsed, recomputing cuts."""
    else:
        print "No cut file specified, recomputing cuts."""
    return best

def main(infilename, cutsfilename, pathfilename, outfilename, source_keypoints, target_keypoints, cuts_algo, path_algo,
        show_cuts=False, show_path=False, playback=False):

    assert target_keypoints[0] == 0, "first target key point must be 0"
    assert len(source_keypoints) == len(target_keypoints), "there must be equal numbers of source and target key points"
    assert len(source_keypoints) >= 2, "there must be at least two key points"

    rate, data = wavfile.read(infilename)
    source_keypoints = [len(data) if x is None else int(round(rate * x)) for x in source_keypoints]
    target_keypoints = [int(round(rate * x)) for x in target_keypoints]

    print "input file: %s (%s, %s fps)" % (infilename, frametime(len(data), rate), rate)
    print "cuts file: %s" % (cutsfilename or "not specified")
    print "path file: %s" % (pathfilename or "not specified")
    print "output file: %s" % (outfilename or "not specified")
    print "key points: " + ", ".join("%s->%s" % (frametime(s, rate), frametime(t, rate)) for s, t in zip(source_keypoints, target_keypoints))
    print

    # try to load cuts from file
    best = read_cuts(infilename, cutsfilename, cuts_algo)

    # recompute cuts if necessary
    if best == None:
        start_time = time.time()
        best = cuts_algo(data)
        elapsed_time = time.time() - start_time

        # write cuts to file
        if cutsfilename is not None:
            print "Writing cuts to %s." % cutsfilename
            contents = cuts_algo.get_parameters()
            contents["algorithm"] = cuts_algo.__class__.__name__
            contents["elapsed_time"] = elapsed_time
            contents["length"] = len(data)
            contents["rate"] = rate
            contents["data"] = [(start, frametime(start, rate), end, frametime(end, rate), error) for start, end, error in best]
            write_datafile(cutsfilename, contents)

    # try to load path from file TODO check if list of cuts has changed
    if pathfilename is not None:
        try:
            if os.stat(pathfilename).st_mtime > os.stat(infilename).st_mtime:
                print "Reading path from %s." % pathfilename
                contents = read_datafile(pathfilename)
                if contents["algorithm"] != path_algo.__class__.__name__:
                    print "Algorithm has changed, recomputing path."
                else:
                    changed_parameters = path_algo.changed_parameters(contents)
                    if changed_parameters:
                        print "Parameters have changed (%s), recomputing path." % ", ".join(changed_parameters)
                    else:
                        path = Path(
                                [Segment(start, end) for start, start_time, end, end_time in contents["data"]],
                                [Keypoint(source, target) for source, target in zip(contents["source_keypoints"], contents["target_keypoints"])]
                                )
            else:
                print "Path file too old, recomputing path."""
        except (OSError, IOError):
            print "Path file could not be read, recomputing path."""
        except (KeyError, SyntaxError):
            print "Path file could not be parsed, recomputing path."""
    else:
        print "No path file specified, recomputing path."""

    # recompute path if necessary
    if "path" not in locals():
        start_time = time.time()
        path = path_algo(source_keypoints, target_keypoints, best)
        elapsed_time = time.time() - start_time

        # write path to file
        if pathfilename is not None:
            contents = path_algo.get_parameters()
            contents["algorithm"] = path_algo.__class__.__name__
            contents["elapsed_time"] = elapsed_time
            contents["length"] = len(data)
            contents["rate"] = rate
            contents["source_keypoints"] = source_keypoints
            contents["target_keypoints"] = target_keypoints
            contents["data"] = [(s.start, frametime(s.start, rate), s.end, frametime(s.end, rate)) for s in path.segments]
            write_datafile(pathfilename, contents)

    # write synthesized sound as wav
    if outfilename:
        wavfile.write(outfilename, rate, path.synthesize(data))

    if show_cuts:
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

        show()

    if show_path:
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
            ax.add_artist(Line2D((0, len(data)), (start, start), color="green", dashes=(2, 2)))

        # plot keypoints
        ax.scatter(source_keypoints, target_keypoints, color="red", marker="x")

        show()
    
    if playback:
        from audioplayer import play
        play(rate, path.synthesize(data), source_keypoints, target_keypoints, path.segments, len(data))

def format_parameter(pname, defaults):
    return "    %s=%s" % (pname, defaults[pname]) if pname in defaults else "    %s" % pname

def format_algorithm(name, algo):
    defaults = algo.get_parameter_defaults()
    return "  %s\n%s" % (name, "\n".join(format_parameter(pname, defaults) for pname in algo.get_parameter_names()))

def create_parser():
    import argparse

    prolog = "usage example: synthesize.py" \
    "\n  -i music.wav -c music.cuts -p music.path -o result.wav" \
    "\n  -s start end -t start 2:40" \
    "\n  -C hierarchical num_cuts=256 num_keep=40 num_levels=max weight_factor=1.2" \
    "\n  -P genetic random_seed=0"

    cuts_epilog = "Cut search algorithms:\n" + "\n".join(format_algorithm(name, algo) for name, algo in cuts_algorithms.items())
    path_epilog = "Path search algorithms:\n" + "\n".join(format_algorithm(name, algo) for name, algo in path_algorithms.items())

    parser = argparse.ArgumentParser(description=prolog, fromfile_prefix_chars="@", epilog=cuts_epilog+"\n"+path_epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter, prog=os.path.basename(__file__))
    parser.add_argument("-i", "--infile", dest="infilename", required=True,
            help="input wave file")
    parser.add_argument("-c", "--cutsfile", dest="cutsfilename",
            help="file for caching cuts")
    parser.add_argument("-p", "--pathfile", dest="pathfilename",
            help="file for caching path")
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
    parser.add_argument("--show-cuts", dest="show_cuts", action="store_true",
            help="show cuts plot after synthesis")
    parser.add_argument("--show-path", dest="show_path", action="store_true",
            help="show path plot after synthesis")
    parser.add_argument("--playback", dest="playback", action="store_true",
            help="play result after synthesis")

    return parser

def pydoc_format_action(action):
    parameters = (
            "``%s``" % action.dest if action.nargs is None
            else "[``%s`` ...]" % action.dest if action.nargs == "*"
            else ("``%s``" % action.dest) * action.nargs)
    name = ", ".join("``%s`` %s" % (x, parameters) for x in action.option_strings)
    description = action.help
    return "%s\n    %s" % (name, description) # dest, help, nargs, const, default, type, choices, metavar

def pydoc_format_algorithm(name, algo):
    defaults = algo.get_parameter_defaults()
    parameters = [("`%s` = %s" % (key, defaults[key])) if key in defaults else key for key in algo.get_parameter_names()]
    return "\n    | ".join(["  `%s`:" % name] + parameters) + "\n"

def generate_pydoc(parser):
    parameters = "\n".join(map(pydoc_format_action, parser._actions))
    cuts_algos = "\n".join(pydoc_format_algorithm(name, algo) for name, algo in cuts_algorithms.items())
    path_algos = "\n".join(pydoc_format_algorithm(name, algo) for name, algo in path_algorithms.items())
    return """

Run the program from the command line as follows:
  
  ``%s`` *parameters*

Parameters
----------

The following command line parameters are available:

%s

Cuts algorithms
---------------

The following algorithms for finding cut positions are available:

%s

Path algorithms
---------------

The following algorithms for finding paths are available:

%s

""" % (os.path.basename(__file__), parameters, cuts_algos, path_algos)

__doc__ = generate_pydoc(create_parser())

if __name__ == "__main__":
    parser = create_parser()
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

