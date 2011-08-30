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

def read_cuts(cutsfilename, cuts_algo=None, infilename=None):
    if cutsfilename is not None:
        try:
            if infilename is None or os.stat(cutsfilename).st_mtime > os.stat(infilename).st_mtime:
                contents = read_datafile(cutsfilename)
                if cuts_algo is not None and contents["algorithm"] != cuts_algo.__class__.__name__:
                    raise ValueError("Algorithm has changed")
                else:
                    changed_parameters = cuts_algo.changed_parameters(contents) if cuts_algo is not None else []
                    if changed_parameters:
                        raise ValueError("Parameters have changed (%s)" % ", ".join(changed_parameters))
                    else:
                        return (
                                contents["rate"],
                                contents["length"],
                                [Cut(int(start), int(end), float(error)) for start, start_time, end, end_time, error in contents["data"]],
                                )
            else:
                raise ValueError("Cut file too old")
        except (OSError, IOError):
            raise ValueError("Cut file could not be read")
        except (KeyError, SyntaxError):
            raise ValueError("Cut file could not be parsed")
    else:
        raise TypeError("No cut file specified")

def compute_cuts(rate, data, cuts_algo, cutsfilename=None):
    start_time = time.time()
    cuts = cuts_algo(data)
    elapsed_time = time.time() - start_time

    # write cuts to file
    if cutsfilename is not None:
        print "Writing cuts to %s." % cutsfilename
        contents = cuts_algo.get_parameters()
        contents["algorithm"] = cuts_algo.__class__.__name__
        contents["elapsed_time"] = elapsed_time
        contents["length"] = len(data)
        contents["rate"] = rate
        contents["data"] = [(start, frametime(start, rate), end, frametime(end, rate), error) for start, end, error in cuts]
        write_datafile(cutsfilename, contents)

    return cuts

def read_path(pathfilename, path_algo=None, infilename=None, source_keypoints=None, target_keypoints=None):
    # TODO check if list of cuts has changed
    if pathfilename is not None:
        try:
            if infilename is None or os.stat(pathfilename).st_mtime > os.stat(infilename).st_mtime:
                contents = read_datafile(pathfilename)
                if path_algo is not None and contents["algorithm"] != path_algo.__class__.__name__:
                    raise ValueError("Algorithm has changed")
                else:
                    changed_parameters = path_algo.changed_parameters(contents) if path_algo is not None else []
                    if changed_parameters:
                        raise ValueError("Parameters have changed (%s)" % ", ".join(changed_parameters))
                    else:
                        return (
                                contents["rate"],
                                contents["length"],
                                Path(
                                [Segment(start, end) for start, start_time, end, end_time in contents["data"]],
                                [Keypoint(source, target) for source, target in zip(contents["source_keypoints"], contents["target_keypoints"])]
                                ),
                                contents["source_keypoints"],
                                contents["target_keypoints"],
                                )
            else:
                raise ValueError("Path file too old")
        except (OSError, IOError):
            raise ValueError("Path file could not be read")
        except (KeyError, SyntaxError):
            raise ValueError("Path file could not be parsed")
    else:
        raise TypeError("No path file specified")

def compute_path(rate, length, cuts, path_algo, source_keypoints, target_keypoints, pathfilename=None):
    start_time = time.time()
    path = path_algo(source_keypoints, target_keypoints, cuts)
    elapsed_time = time.time() - start_time

    # write path to file
    if pathfilename is not None:
        contents = path_algo.get_parameters()
        contents["algorithm"] = path_algo.__class__.__name__
        contents["elapsed_time"] = elapsed_time
        contents["length"] = length
        contents["rate"] = rate
        contents["source_keypoints"] = source_keypoints
        contents["target_keypoints"] = target_keypoints
        contents["data"] = [(s.start, frametime(s.start, rate), s.end, frametime(s.end, rate)) for s in path.segments]
        write_datafile(pathfilename, contents)

    return path

def show_cuts_plot(rate, length, cuts):
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
    ax.scatter([x[0] for x in cuts], [x[1] for x in cuts], c=[x[2] for x in cuts])
    ax.set_xlim(0, length)
    ax.set_ylim(0, length)

def show_path_plot(rate, length, path, source_keypoints, target_keypoints):
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
    ax.set_xlim(0, length)
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
        ax.add_artist(Line2D((0, length), (start, start), color="green", dashes=(2, 2)))

    # plot keypoints
    ax.scatter(source_keypoints, target_keypoints, color="red", marker="x")

def main(infilename, cutsfilename, pathfilename, outfilename, source_keypoints, target_keypoints, cuts_algo, path_algo,
        show_cuts=False, show_path=False, playback=False):

    # try to read cuts from file
    try:
        rate, length, cuts = read_cuts(cutsfilename, cuts_algo, infilename)
        has_cached_cuts = True
    except ValueError, e:
        print "%s, cuts file will not be used." % e
        has_cached_cuts = False
    except TypeError:
        pass

    # try to read path from file
    try:
        rate, length, path, source_keypoints, target_keypoints = read_path(pathfilename, path_algo, infilename)
        has_cached_path = True
    except ValueError, e:
        print "%s, path file will not be used." % e
        has_cached_path = False
    except TypeError:
        pass

    can_compute_cuts = infilename and cuts_algo
    can_compute_path = (can_compute_cuts or has_cached_cuts) and path_algo and source_keypoints and target_keypoints
    must_compute_path = (show_path or playback or outfilename or (can_compute_path and pathfilename)) and not has_cached_path
    must_compute_cuts = (must_compute_path or show_cuts or (can_compute_cuts and cutsfilename)) and not has_cached_cuts
    must_read_data = must_compute_path or playback or outfilename

    if must_read_data:
        if infilename is not None:
            rate, data = wavfile.read(infilename)
            length = len(data)
            if source_keypoints is not None and target_keypoints is not None:
                if not has_cached_path:
                    assert target_keypoints[0] == 0, "first target key point must be 0"
                    assert len(source_keypoints) == len(target_keypoints), "number of source and target key points must be equal"
                    assert len(source_keypoints) >= 2, "there must be at least two key points"
                    source_keypoints = [length if x is None else int(round(rate * x)) for x in source_keypoints]
                    target_keypoints = [int(round(rate * x)) for x in target_keypoints] if target_keypoints is not None else None
            else:
                source_keypoints = target_keypoints = None
        else:
            raise RuntimeError("--infilename necessary but not specified")

    if must_compute_cuts:
        if can_compute_cuts:
            cuts = compute_cuts(rate, data, cuts_algo, cutsfilename)
        else:
            raise RuntimeError("insufficient information to compute cuts")

    if must_compute_path:
        if can_compute_path:
            path = compute_path(rate, length, cuts, path_algo, source_keypoints, target_keypoints, pathfilename)
        else:
            raise RuntimeError("insufficient information to compute path")

    if outfilename:
        wavfile.write(outfilename, rate, path.synthesize(data))

    if show_cuts:
        show_cuts_plot(rate, length, cuts)

    if show_path:
        show_path_plot(rate, length, path, source_keypoints, target_keypoints)

    if show_cuts or show_path:
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
    parser.add_argument("-i", "--infile", dest="infilename",
            help="input wave file")
    parser.add_argument("-c", "--cutsfile", dest="cutsfilename",
            help="file for caching cuts")
    parser.add_argument("-p", "--pathfile", dest="pathfilename",
            help="file for caching path")
    parser.add_argument("-o", "--outfile", dest="outfilename",
            help="output wave file")
    parser.add_argument("-s", "--source", dest="source_keypoints", type=make_lookup(ptime, start=0, end=None), nargs="*", default=[0, None],
            help="source key points (in seconds, or hh:mm:ss.sss); special values 'start' and 'end' are allowed")
    parser.add_argument("-t", "--target", dest="target_keypoints", type=make_lookup(ptime, start=0), nargs="*",
            help="target key points (in seconds, or hh:mm:ss.sss); special value 'start' is allowed")
    parser.add_argument("-C", "--cutsalgo", dest="cuts_algo", nargs="*",
            help="cuts algorithm and parameters as key=value list")
    parser.add_argument("-P", "--pathalgo", dest="path_algo", nargs="*",
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
    import sys

    parser = create_parser()
    args = parser.parse_args()

    if args.cuts_algo is not None:
        try:
            cuts_algo_class = cuts_algorithms[args.cuts_algo[0]]
        except KeyError:
            print >> sys.stderr, "Cuts algorithm '%s' not found. Use --help for a list of valid choices." % args.cuts_algo[0]
            sys.exit(1)
        try:
            args.cuts_algo = cuts_algo_class(**dict(x.split("=", 1) for x in args.cuts_algo[1:]))
        except TypeError, e:
            print >> sys.stderr, "Error in cuts algorithm parameters: %s" % e
            sys.exit(1)
        except ValueError:
            print >> sys.stderr, "Cuts algorithm parameters could not be parsed"
            sys.exit(1)

    if args.path_algo is not None:
        try:
            path_algo_class = path_algorithms[args.path_algo[0]]
        except KeyError:
            print >> sys.stderr, "Path algorithm '%s' not found. Use --help for a list of valid choices." % args.path_algo[0]
            sys.exit(1)
        try:
            args.path_algo = path_algo_class(**dict(x.split("=", 1) for x in args.path_algo[1:]))
        except TypeError, e:
            print >> sys.stderr, "Error in path algorithm parameters: %s" % e
            sys.exit(1)
        except ValueError:
            print >> sys.stderr, "Path algorithm parameters could not be parsed"
            sys.exit(1)

    try:
        main(**args.__dict__)
    except (RuntimeError, AssertionError), e:
        print >> sys.stderr, "Error: %s" % e
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)

