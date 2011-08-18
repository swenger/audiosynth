#!/usr/bin/env python

import os
import random

from numpy import concatenate, floor, log
from scipy.io import wavfile
from pylab import figure, axes, title, show
from matplotlib.lines import Line2D

from datafile import read_datafile, write_datafile
from utilities import make_lookup, ptime, frametime
from timeplots import FrameTimeLocator, FrameTimeFormatter

class Algorithm(object):
    """Base class for algorithms that know about their parameters."""

    def get_parameter_names(self):
        """Return the names of the algorithm's parameters."""
        return self.__init__.func_code.co_varnames[1:self.__init__.func_code.co_argcount]

    def get_parameter_defaults(self):
        """Return a dictionary of parameters and their default values."""
        return dict(zip(reversed(self.get_parameter_names()), reversed(self.__init__.func_defaults)))

    def get_parameters(self):
        """Return a dictionary of parameters."""
        return dict((key, getattr(self, key)) for key in self.get_parameter_names())

    def changed_parameters(self, header):
        """Return names of all parameters that have changed with respect to the supplied dictionary."""
        return [name for name in self.get_parameter_names() if name not in header or header[name] != getattr(self, name)]

class CutsAlgorithm(Algorithm):
    pass

class PathAlgorithm(Algorithm):
    pass

class HierarchicalCutsAlgorithm(CutsAlgorithm):
    """Hierarchical algorithm for finding cuts."""
    
    def __init__(self, num_cuts=256, num_keep=40, block_length_shrink=16, num_levels="max", weight_factor=1.2):
        self.num_cuts = int(num_cuts)
        self.num_keep = int(num_keep)
        self.block_length_shrink = int(block_length_shrink)
        self.num_levels = num_levels if num_levels == "max" else int(num_levels)
        self.weight_factor = float(weight_factor)

    def __call__(self, data):
        from cutsearch import analyze
        num_levels = min(int(floor(log(len(data)) / log(self.block_length_shrink))) + 1,
                float("inf") if self.num_levels == "max" else self.num_levels)
        cuts = analyze(data, self.block_length_shrink ** (num_levels - 1), self.num_cuts, self.block_length_shrink, self.weight_factor)
        return cuts[:self.num_keep] if self.num_keep else cuts

class GeneticPathAlgorithm(PathAlgorithm):
    """Genetic algorithm for finding paths."""

    def __init__(self, num_individuals=1000, num_generations=10, num_children=1000, random_seed=None):
        self.num_individuals = int(num_individuals)
        self.num_generations = int(num_generations)
        self.num_children = int(num_children)
        self.random_seed = int(random_seed) if random_seed is not None else random.randint(0, 1 << 32 - 1)

    def __call__(self, source_keypoints, target_keypoints, cuts):
        from geneticpathsearch import path_search
        return path_search(source_keypoints, target_keypoints, cuts,
                self.num_individuals, self.num_generations, self.num_children, self.random_seed)

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
        if os.stat(cutfilename).st_mtime > os.stat(infilename).st_mtime:
            print "Reading cuts from %s." % cutfilename
            header, best = read_datafile(cutfilename)
            best = [(int(start), int(end), float(error)) for (start, start_time, end, end_time, error) in best]
            changed_parameters = cuts_algo.changed_parameters(header)
            if changed_parameters:
                print "Parameters have changed (%s), recomputing cuts." % ", ".join(changed_parameters)
                del best
        else:
            print "Cut file too old, recomputing cuts."""
    else:
        print "No cut file specified, recomputing cuts."""

    # recompute cuts if necessary
    if "best" not in locals():
        best = cuts_algo(data)

        # write cuts to file
        if cutfilename is not None:
            print "Writing cuts to %s." % cutfilename
            d = cuts_algo.get_parameters()
            d["length"] = len(data)
            d["rate"] = rate
            write_datafile(cutfilename, d, ((start, frametime(rate, start), end, frametime(rate, end), error) for (start, end, error) in best),
                    (int, str, int, str, float))

    # perform graph search
    segments = path_algo(source_keypoints, target_keypoints, best)

    # write path to file
    if pathfilename:
        d = path_algo.get_parameters()
        d["length"] = len(data)
        d["rate"] = rate
        d["source_keypoints"] = source_keypoints
        d["target_keypoints"] = target_keypoints
        write_datafile(pathfilename, d, ((s.start, frametime(rate, s.start), s.end, frametime(rate, s.end)) for s in segments),
                (int, str, int, str))

    # write synthesized sound as wav
    if outfilename:
        result = concatenate([data[s.start:s.end] for s in segments])
        wavfile.write(outfilename, rate, result)

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

def longest_common_subsequence(x, y):
    c = [[0] * (len(y) + 1) for i in range(len(x) + 1)]
    for i in range(1, len(x) + 1):
        for j in range(1, len(y) + 1):
            c[i][j] = c[i - 1][j - 1] + 1 if x[i - 1] == y[j - 1] else max(c[i][j - 1], c[i - 1][j])
    return c

def best_match(s, l):
    """Find the item in ``l`` that is most similar to the string ``s``."""
    return max((longest_common_subsequence(s, x), x) for x in l)[1]

if __name__ == "__main__":
    import argparse

    g = globals()
    def is_subclass(a, b):
        try:
            return issubclass(a, b) and not a == b
        except TypeError:
            return False
    cuts_algorithms = dict((key, value) for key, value in g.items() if is_subclass(value, CutsAlgorithm))
    path_algorithms = dict((key, value) for key, value in g.items() if is_subclass(value, PathAlgorithm))

    parser = argparse.ArgumentParser(description=main.__doc__, fromfile_prefix_chars="@")
    parser.add_argument("-i", "--infile", dest="infilename", required=True,
            help="input wave file")
    parser.add_argument("-c", "--cutsfile", dest="cutfilename",
            help="file for caching cuts")
    parser.add_argument("-p", "--pathfile", dest="pathfilename",
            help="output path file")
    parser.add_argument("-o", "--outfile", dest="outfilename",
            help="output wave file")
    parser.add_argument("-s", "--source", dest="source_keypoints", type=make_lookup(ptime, start=0, end=None), nargs="*", required=True,
            help="source key points; special values 'start' and 'end' are allowed")
    parser.add_argument("-t", "--target", dest="target_keypoints", type=make_lookup(ptime, start=0), nargs="*", required=True,
            help="target key points; special value 'start' is allowed")
    parser.add_argument("-C", "--cutsalgo", dest="cuts_algo", default="HierarchicalCutsAlgorithm", nargs="*", #choices=cuts_algorithms.keys(),
            help="cuts algorithm and parameters as key=value list")
    parser.add_argument("-P", "--pathalgo", dest="path_algo", default="GeneticPathAlgorithm", nargs="*", #choices=path_algorithms.keys(),
            help="path algorithm and parameters as key=value list")
    args = parser.parse_args()

    cuts_algo_class = cuts_algorithms[best_match(args.cuts_algo[0], cuts_algorithms)]
    cuts_algo_parameters = dict(x.split("=", 1) for x in args.cuts_algo[1:])
    args.cuts_algo = cuts_algo_class(**cuts_algo_parameters)
    print "Cuts algorithm: %s" % args.cuts_algo.__class__.__name__

    path_algo_class = path_algorithms[best_match(args.path_algo[0], path_algorithms)]
    path_algo_parameters = dict(x.split("=", 1) for x in args.path_algo[1:])
    args.path_algo = path_algo_class(**path_algo_parameters)
    print "Path algorithm: %s" % args.path_algo.__class__.__name__

    main(**args.__dict__)

    # e.g. synthesize.py -i playmateoftheyear.wav -c playmateoftheyear.cuts -p playmateoftheyear.path -o result.wav -s start end -t start 2:40
    #                    -C hierarchical num_cuts=256 num_keep=40 num_levels=max weight_factor=1.5
    #                    -P genetic random_seed=5

