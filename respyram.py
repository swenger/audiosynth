#!/usr/bin/env python

from numpy import isnan, inf, eye, unravel_index, asarray, isinf, concatenate, floor, log
from numpy.fft import fft
from scipy.spatial.distance import cdist
import heapq

def frametime(rate, frame, minute_digits=2, decimals=2):
    """Convert a frame number to a time signature."""
    minutes, seconds = divmod(frame / float(rate), 60)
    return "%0*d:%0*.*f" % (minute_digits, minutes, 3 + decimals, decimals, seconds)

class AnalysisLayer(object):
    def __init__(self, data1, data2, block_length, num_keep, block_length_shrink=16, num_skip_print=3):
        self.block_length = block_length
        if block_length >= block_length_shrink ** num_skip_print: # do not print innermost num_skip_print layers
            print "len(data1) = %d, len(data2) = %d, block_length = %d, num_keep = %d" % (len(data1), len(data2), block_length, num_keep)

        # split data into non-overlapping blocks of length block_length
        num_blocks1 = len(data1) // block_length
        num_blocks2 = len(data2) // block_length
        blocks1 = data1.reshape((num_blocks1, block_length) + data1.shape[1:])
        blocks2 = data2.reshape((num_blocks2, block_length) + data2.shape[1:])

        # reduce block size
        new_block_length = max(block_length / block_length_shrink, 1)

        # compute spectrum of each block (could also be mel analysis or the like)
        if new_block_length <= 1: # innermost layer: use raw sample data
            feature_vectors1 = blocks1.reshape(num_blocks1, -1)
            feature_vectors2 = blocks2.reshape(num_blocks2, -1)
        else:
            feature_vectors1 = abs(fft(blocks1, axis=1)).reshape(num_blocks1, -1) # TODO MFCCs
            feature_vectors2 = abs(fft(blocks2, axis=1)).reshape(num_blocks2, -1) # TODO MFCCs
        
        # compute distances between feature vectors
        distances = cdist(feature_vectors1, feature_vectors2, "sqeuclidean") # (u - v) ** 2
        normalization = cdist(feature_vectors1, -feature_vectors2, "sqeuclidean") # (u + v) ** 2
        distances /= normalization # (u - v) ** 2 / (u + v) ** 2
        distances[isnan(distances)] = 0.0 # both feature vectors are zero => cut okay
        if data1 is data2: # data arrays are identical => do not cut on diagonal (would be equivalent to a jump to the same location)
            distances[eye(len(distances)).astype(bool)] = inf

        # find best num_keep off-diagonal child indices and their respective distances
        best = heapq.nsmallest(num_keep, zip(distances.ravel(), range(distances.size)))
        self.i, self.j, self.d = zip(*[unravel_index(i, distances.shape) + (d,) for d, i in best])
        self.i = asarray(self.i, int) # block index of cut within data1
        self.j = asarray(self.j, int) # block index of cut within data2
        self.d = asarray(self.d, float) # quality of cut
        
        # keep at least one cut per child
        new_num_keep = max(num_keep / distances.size, 1)

        # if children are not empty, initialize them
        if block_length > 1:
            self.children = []
            for i, j, d in zip(self.i, self.j, self.d):
                if not isinf(d):
                    self.children.append(AnalysisLayer(blocks1[i], blocks2[j], new_block_length, new_num_keep))

    def get_cuts(self, weight_factor=2.0, weight=1.0):
        """Return a list of all branches of the tree with their respective weighted length."""
        l = []
        new_weight = weight * weight_factor # lower levels get different weight
        if hasattr(self, "children"):
            for child, si, sj, sd in zip(self.children, self.i, self.j, weight * self.d):
                l += [(si * self.block_length + i, sj * self.block_length + j, sd + d) for i, j, d in child.get_cuts(weight_factor, new_weight)]
        else:
            l += zip(self.i, self.j, weight * self.d)
        return l

def analyze(data, block_length, num_keep, block_length_shrink=16, num_skip_print=3, weight_factor=2.0):
    data = data[:block_length * (len(data) // block_length)]
    root = AnalysisLayer(data, data, block_length, num_keep, block_length_shrink, num_skip_print)
    cuts = root.get_cuts(weight_factor)
    cuts.sort(key=lambda x: x[2]) # TODO maybe remove duplicates
    return cuts

def main(infilename, outfilename,
        num_cuts=256, num_keep=40, block_length_shrink=16, num_levels=5, weight_factor=1.2,
        desired_start=0, desired_end=None, desired_duration=None, cost_factor=1.0, duration_factor=1.0, repetition_factor=1e9, num_paths=32):

    from scipy.io import wavfile

    # read file
    rate, data = wavfile.read(infilename)

    num_levels = min(int(floor(log(len(data)) / log(block_length_shrink))), float("inf") if num_levels is None else num_levels)
    desired_start = int(round(rate * desired_start))
    desired_end = len(data) if desired_end is None else int(round(rate * desired_end))
    desired_duration = int(round(rate * desired_duration))

    # find good cuts
    best = analyze(data, block_length_shrink ** (num_levels - 1), num_cuts, block_length_shrink, weight_factor=weight_factor)
    best = best[:num_keep]

    # perform graph search
    from graphsearch import Graph
    g = Graph(best, (0, desired_start, desired_end, len(data)))
    paths = g.find_paths(start=desired_start, end=desired_end, duration=desired_duration, cost_factor=cost_factor,
            duration_factor=duration_factor / rate, repetition_factor=repetition_factor, num_paths=num_paths)
    segments = paths[0].segments

    # write synthesized sound as wav
    wavfile.write(outfilename, rate, concatenate([data[s.start:s.end] for s in segments]))

if __name__ == "__main__":
    import argparse

    def make_lookup(dtype, **constants):
        def lookup(x):
            try:
                return constants[x]
            except KeyError:
                return dtype(x)
        return lookup


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
    path_group.add_argument("-R", "--repetitionfactor", type=float, default=1.0, help="repetition factor", dest="repetition_factor")
    path_group.add_argument("-p", "--paths", type=int, default=32, help="number of paths to find", dest="num_paths")

    main(**parser.parse_args().__dict__)

