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

def f2t(fs, f, minute_digits=2, decimals=2):
    """Convert a frame number f to a time signature."""
    format_string = "%0" + str(minute_digits) + "d:%0" + str(decimals + 3) + "." + str(decimals) + "f"
    return format_string % divmod(f / float(fs), 60)

def make_set_of_files(dataset):
    import os
    infilename = "/local/wenger/Daten/music/data/%s/%s.wav" % (dataset, dataset)
    basename, extension = os.path.splitext(infilename)

    # cut search parameters
    num_cuts = 256 # 256 usually works
    num_keep = 128 # 40 number of best cuts to keep
    block_length_shrink = 16 # 16 usually works
    num_levels = 5 # 5 or 6 usually work, depending on length of sample; 0 for automatic computation
    weight_factor = 1.2 # 1.0 .. 2.0 usually work

    # graph search parameters
    desired_start = 0 # seconds in sample
    desired_end = 56.05 # seconds in sample or 0 for end of sample
    desired_duration = 30.5 # seconds or 0 for twice the input length
    cost_factor = 1.0 # 1.0
    duration_factor = 1.0 # 1.0
    repetition_factor = 1e9 # 1e9
    num_paths = 32 # 100

    # read file
    from scikits.audiolab import wavread, wavwrite
    if extension.lower().endswith("wav"):
        data, fs, enc = wavread(infilename)
    else:
        raise "unsupported audio format:", extension
    if len(data.shape) > 1 and data.shape[1] > 1:
        data = mean(data, axis=1) # make mono TODO use stereo
    print "The file is %d samples (%s) long, at %d samples per second." % (len(data), f2t(fs, len(data)), fs)
    if num_levels == 0:
        num_levels = int(floor(log(len(data)) / log(block_length_shrink)))
    initial_block_length = block_length_shrink ** (num_levels - 1)
    while block_length_shrink * initial_block_length > len(data):
        num_levels -= 1
        initial_block_length = block_length_shrink ** (num_levels - 1)

    desired_start = int(round(fs * desired_start))
    if desired_end == 0:
        desired_end = len(data)
    else:
        desired_end = int(round(fs * desired_end))
    if desired_duration == 0:
        desired_duration = 2 * len(data)
    else:
        desired_duration = int(round(fs * desired_duration))

    # file names
    cutparams = "-%04d-%03d-%02d-%01d-%04.2f" % (num_cuts, num_keep, block_length_shrink, num_levels, weight_factor)
    synthparams = "-%.2e-%.2e-%.2e-%04d" % (cost_factor, duration_factor, repetition_factor, num_paths)
    cut_wav_filename_tmpl = basename + "-cuts" + cutparams + "-%04d-%09d-%09d" + os.path.extsep + "wav"
    cut_txt_filename = basename + "-cuts" + cutparams + os.path.extsep + "txt"
    path_txt_filename_tmpl = basename + "-path" + cutparams + synthparams + "-%04d" + os.path.extsep + "txt"
    synth_wav_filename = basename + "-synthesized" + cutparams + synthparams + os.path.extsep + "wav"
    synth_txt_filename = basename + "-synthesized" + cutparams + synthparams + os.path.extsep + "txt"

    # find good cuts
    t_cuts = clock()
    best = analyze(data, initial_block_length, num_cuts, block_length_shrink, weight_factor=weight_factor)
    best = best[:num_keep] # keep only best cuts
    t_cuts = clock() - t_cuts

    # write cuts as txt
    with open(cut_txt_filename, "w") as f:
        print >> f, "jump_start_sample, jump_start_time, jump_stop_sample, jump_stop_time, jump_error"
        print >> f, "fs = %d, initial_block_length = %d, time_for_cuts = %s" % (fs, initial_block_length, t_cuts)
        for i, j, d in best:
            print >> f, i, f2t(fs, i), j, f2t(fs, j), d

    # write cuts as wav
    fade_in = fs
    before = 4 * fs
    after = 4 * fs
    fade_out = fs
    for idx, (start_sample, stop_sample, best_d) in enumerate(best):
        fname = cut_wav_filename_tmpl % (idx, start_sample, stop_sample)
        a = data[max(start_sample - before - fade_in, 0) : max(start_sample - before, 0)].copy()
        a *= mgrid[0:1:len(a)*1.0j]
        a = concatenate((zeros(fade_in - len(a)), a))
        b = data[max(start_sample - before, 0) : start_sample]
        b = concatenate((zeros(before - len(b)), b))
        c = data[stop_sample : min(stop_sample + after, len(data) - 1)]
        c = concatenate((c, zeros(after - len(c))))
        d = data[min(stop_sample + after, len(data) - 1) : min(stop_sample + after + fade_out, len(data) - 1)].copy()
        d *= mgrid[1:0:len(d)*1.0j]
        d = concatenate((d, zeros(fade_out - len(d))))
        wavwrite(concatenate((a, b, c, d)), fname, fs, enc)

    # perform graph search
    from graphsearch import Graph
    t_graph = clock()
    g = Graph(best, (0, desired_start, desired_end, len(data)))
    paths = g.find_paths(start=desired_start, end=desired_end, duration=desired_duration, cost_factor=cost_factor,
            duration_factor=duration_factor / fs, repetition_factor=repetition_factor, num_paths=num_paths)
    t_graph = clock() - t_graph
    segments = paths[0].segments

    # write best paths as txt
    for idx, path in enumerate(paths):
        with open(path_txt_filename_tmpl % idx, "w") as f:
            print >> f, "source_start_sample, source_start_time, source_end_sample, source_end_time"
            print >> f, "fs = %d, initial_block_length = %d, time_for_cuts = %s, cost = %s, duration = %s, error_func = %s, time_for_graph_search = %s" % (fs, initial_block_length, t_cuts, path.cost, path.duration, path.errorfunc, t_graph)
            for s in path.segments:
                print >> f, s.start, f2t(fs, s.start), s.end, f2t(fs, s.end)

    # write synthesized sound as txt
    with open(synth_txt_filename, "w") as f:
        print >> f, "target_start_sample, target_start_time, source_start_sample, source_start_time, source_end_sample, source_end_time"
        print >> f, "fs = %d, initial_block_length = %d, time_for_cuts = %s, cost = %s, duration = %s, error_func = %s" % (fs, initial_block_length, t_cuts, paths[0].cost, paths[0].duration, paths[0].errorfunc)
        print >> f, 0, f2t(fs, 0), segments[0].start, f2t(fs, segments[0].start),
        pos = segments[0].duration
        last_end = segments[0].end
        for s in segments[1:]:
            if s.start != last_end: # a real jump occured
                print >> f, last_end, f2t(fs, last_end)
                print >> f, pos, f2t(fs, pos), s.start, f2t(fs, s.start),
            last_end = s.end
            pos += s.duration
        print >> f, segments[-1].end, f2t(fs, segments[-1].end)
    length = pos

    # write synthesized sound as wav
    wavwrite(concatenate([data[s.start:s.end] for s in segments]), synth_wav_filename, fs, enc)

if __name__ == "__main__":
    for dataset in ("playmateoftheyear", ):#DEBUG"intro", "crowd", "fire", "rain", "surf", "water", "blowinginthewind", "zdarlight", "swanlake", "endlichnichtschwimmer"):
        print "Processing '%s':" % dataset
        make_set_of_files(dataset)
        print
    
