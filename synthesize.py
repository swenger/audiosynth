#!/usr/bin/env python

from numpy import concatenate, floor, log, array
from scipy.io import wavfile
from pylab import figure, axes, title, show
from matplotlib.lines import Line2D

from cutsearch import analyze
from pathsearch import Graph
from utilities import make_lookup
from timeplots import FrameTimeLocator, FrameTimeFormatter

def main(infilename, outfilename,
        num_cuts=256, num_keep=40, block_length_shrink=16, num_levels=5, weight_factor=1.2,
        desired_start=0, desired_end=None, desired_duration=None, cost_factor=1.0, duration_factor=1.0, repetition_factor=1e9, num_paths=32):

    # read file
    rate, data = wavfile.read(infilename)

    num_levels = min(int(floor(log(len(data)) / log(block_length_shrink))), float("inf") if num_levels is None else num_levels)
    desired_start = int(round(rate * desired_start))
    desired_end = len(data) if desired_end is None else int(round(rate * desired_end))
    desired_duration = int(round(rate * desired_duration))

    # find good cuts
    best = array(analyze(data, block_length_shrink ** (num_levels - 1), num_cuts, block_length_shrink, weight_factor=weight_factor))
    best = best[:num_keep]

    # perform graph search
    g = Graph(best, (0, desired_start, desired_end, len(data)))
    paths = g.find_paths(start=desired_start, end=desired_end, duration=desired_duration, cost_factor=cost_factor,
            duration_factor=duration_factor / rate, repetition_factor=repetition_factor, num_paths=num_paths)
    segments = paths[0].segments

    # write synthesized sound as wav
    wavfile.write(outfilename, rate, concatenate([data[s.start:s.end] for s in segments]))

    # visualize cuts
    figure()
    ax = axes()
    ax.xaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.xaxis.set_minor_locator(FrameTimeLocator(rate, 100))
    ax.xaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.yaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.yaxis.set_minor_locator(FrameTimeLocator(rate, 100))
    ax.yaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.set_aspect("equal")
    ax.scatter(best[:, 0], best[:, 1], c=best[:, 2])
    title("cut positions")

    # visualize path
    figure()
    ax = axes()
    ax.xaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.xaxis.set_minor_locator(FrameTimeLocator(rate, 100))
    ax.xaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.yaxis.set_major_locator(FrameTimeLocator(rate, 10))
    ax.yaxis.set_minor_locator(FrameTimeLocator(rate, 100))
    ax.yaxis.set_major_formatter(FrameTimeFormatter(rate))
    ax.set_aspect("equal")
    ax.set_xlim(0, len(data))
    ax.set_ylim(0, desired_duration)
    
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
    ax.scatter((desired_start, desired_end), (0, desired_duration), color="red", marker="x")

    title("jumps")

    show()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    
    general_group = parser.add_argument_group("general arguments")
    general_group.add_argument("-i", "--infile", help="input wave file", dest="infilename", required=True)
    general_group.add_argument("-o", "--outfile", help="output wave file", dest="outfilename", required=True)

    cuts_group = parser.add_argument_group("cut search arguments")
    cuts_group.add_argument("-c", "--cuts", type=int, default=256, help="cuts on first level", dest="num_cuts")
    cuts_group.add_argument("-k", "--keep", type=int, default=40, help="cuts to keep", dest="num_keep")
    cuts_group.add_argument("-s", "--shrink", type=int, default=16, help="block shrinkage per level", dest="block_length_shrink")
    cuts_group.add_argument("-l", "--levels", type=make_lookup(int, max=None), default=5, help="number of levels", dest="num_levels")
    cuts_group.add_argument("-w", "--weightfactor", type=float, default=1.2, help="weight factor between levels", dest="weight_factor")

    path_group = parser.add_argument_group("path search arguments")
    path_group.add_argument("-f", "--from", type=int, default=0, help="desired start sample in input in seconds", dest="desired_start")
    path_group.add_argument("-t", "--to", type=make_lookup(int, end=None), help="desired end sample in input in seconds", dest="desired_end")
    path_group.add_argument("-d", "--duration", type=int, help="desired duration of output in seconds", dest="desired_duration", required=True)
    path_group.add_argument("-C", "--costfactor", type=float, default=1.0, help="cost factor", dest="cost_factor")
    path_group.add_argument("-D", "--durationfactor", type=float, default=1.0, help="duration factor", dest="duration_factor")
    path_group.add_argument("-R", "--repetitionfactor", type=float, default=1.0e9, help="repetition factor", dest="repetition_factor")
    path_group.add_argument("-p", "--paths", type=int, default=32, help="number of paths to find", dest="num_paths")

    main(**parser.parse_args().__dict__)

