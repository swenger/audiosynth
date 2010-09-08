from scipy.spatial.distance import cdist, squareform
import heapq
from time import clock
from bisect import bisect
from collections import deque
import dijkstra
import sys, os

class AnalysisLayer(object):
    def __init__(self, data1, data2, block_length, num_keep, block_length_shrink=16, num_skip_print=3):
        self.block_length = block_length
        if block_length >= block_length_shrink ** num_skip_print: # do not print innermost num_skip_print layers
            print "len(data1) = %d, len(data2) = %d, block_length = %d, num_keep = %d" % (len(data1), len(data2), block_length, num_keep)

        # split data into non-overlapping blocks of length block_length
        blocks1 = data1.reshape(-1, block_length)
        blocks2 = data2.reshape(-1, block_length)

        # reduce block size
        new_block_length = max(block_length / block_length_shrink, 1)

        # compute spectrum of each block (could also be mel analysis or the like)
        if new_block_length <= 1: # innermost layer: use raw sample data
            feature_vectors1 = blocks1
            feature_vectors2 = blocks2
        else:
            feature_vectors1 = abs(fft(blocks1)) # TODO MFCCs
            feature_vectors2 = abs(fft(blocks2)) # TODO MFCCs

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

if __name__ == "__main__":
    infilename = "/local/wenger/Daten/music/test.wav"
    outfilename = "/local/wenger/Daten/music/test-skip.wav"
    loopfilename = "/local/wenger/Daten/music/test-loop.wav"
    block_length_shrink = 16 # 16 usually works
    num_levels = 5 # 5 or 6 usually work
    num_cuts = 256 # 256 usually works
    initial_block_length = block_length_shrink ** (num_levels - 1)

    # read file
    from scikits.audiolab import wavread, wavwrite
    if infilename.lower().endswith(".wav"):
        data, fs, enc = wavread(infilename)
    elif infilename.lower().endswith(".mp3"):
        enc = "pcm16" # TODO set data, fs from MP3
    else:
        raise "unsupported audio format"
    data = mean(data, axis=1) # make mono TODO use stereo
    print "The file is %d samples (%d:%04.1f) long, at %d samples per second." % ((len(data),) + divmod(len(data) / float(fs), 60) + (fs,))

    # find good cuts
    t = clock()
    best = analyze(data, initial_block_length, num_cuts, block_length_shrink, weight_factor=1.0)
    best = best[:20] # DEBUG keep only best cuts
    print "Time for finding %d good cuts was %.1fs." % (len(best), clock() - t)

    # display best cuts
    print "There are %d cuts:" % len(best)
    for idx, (i, j, d) in enumerate(best):
        print "% 8d: sample % 8d to sample % 8d (% 8d samples, %d:%04.1f), error %s" % ((idx, i, j, abs(i - j)) + divmod(abs(i - j) / float(fs), 60) + (d,))

    # display distribution of cuts in i-j-plane and respective errors
    figure()
    bb = array(zip(*best))
    scatter(bb[0] / float(fs), bb[1] / float(fs), c=bb[2], s=5)
    axis("image")
    colorbar()
    title("position and error of cuts")

    fade_in = fs
    before = 4 * fs
    after = 4 * fs
    fade_out = fs
    for idx, (start_sample, stop_sample, best_d) in enumerate(best):
        print "Writing cut %d of %d..." % (idx, len(best))
        fname = "/local/wenger/Daten/music/cut%06d-%08d-to-%08d.wav" % (idx, start_sample, stop_sample)

        a = data[max(start_sample - before - fade_in, 0) : max(start_sample - before, 0)].copy()
        a *= mgrid[0:1:len(a)*1.0j]
        if len(a) != fade_in:
            print "  fade_in padded"
        a = concatenate((zeros(fade_in - len(a)), a))

        b = data[max(start_sample - before, 0) : start_sample]
        if len(b) != before:
            print "  before padded"
        b = concatenate((zeros(before - len(b)), b))
        
        c = data[stop_sample : min(stop_sample + after, len(data) - 1)]
        if len(c) != after:
            print "  after padded"
        c = concatenate((c, zeros(after - len(c))))
        
        d = data[min(stop_sample + after, len(data) - 1) : min(stop_sample + after + fade_out, len(data) - 1)].copy()
        d *= mgrid[1:0:len(d)*1.0j]
        if len(d) != fade_out:
            print "  fade_out padded"
        d = concatenate((d, zeros(fade_out - len(d))))
        
        block = concatenate((a, b, c, d))
        wavwrite(block, fname, fs, enc)

    from graphsearch import Graph
    g = Graph(best, (0, len(data)))
    paths = g.find_paths(start=0, end=len(data), duration=2*len(data),
            cost_factor=1.0,
            duration_factor=1.0/fs,
            repetition_factor=1e9,
            num_paths=100)
    for path in paths:
        print path.cost, path.duration
    wavwrite(concatenate([data[s.start:s.end] for s in paths[0]._segments]), outfilename, fs, enc) # TODO use iterator semantics of path

