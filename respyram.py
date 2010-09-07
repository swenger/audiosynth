from scipy.spatial.distance import cdist, squareform
import heapq
from time import clock
import bisect
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

class CutGraph(object):
    def __init__(self, cuts, target_end_sample, positions=[]): # cuts is a list of start-sample/stop-sample/error triples
        self._cuts = dict()
        start_samples = []
        stop_samples = []
        
        for start_sample, stop_sample, cut_error in cuts:
            self._cuts.setdefault(start_sample, dict())[stop_sample] = cut_error # store jump in source
            start_samples.append(start_sample)
            stop_samples.append(stop_sample)

        for position in positions: # constraint points, e.g. start / end
            self._cuts.setdefault(position, dict()) # add cut but no possible jumps
            start_samples.append(position)
            stop_samples.append(position)

        start_samples.sort()
        stop_samples.sort()
        self._next = dict()
        for stop_sample in stop_samples:
            next_sample = bisect.bisect(start_samples, stop_sample)
            if next_sample < len(start_samples):
                self._next[stop_sample] = start_samples[next_sample] # store next start sample for stop sample

        self._source_end_sample = stop_samples[-1]
        self._target_end_sample = target_end_sample

    def get_next_cut(self, source_sample): # finds the next sample to jump away from
        try:
            return self._next[source_sample]
        except KeyError:
            return self._cuts.keys()[bisect.bisect(self._cuts.keys(), source_sample)]

    def get_cuts(self, source_sample):
        return self._cuts[source_sample]

    def get_arcs_from(self, node): # node is a source-sample/target-sample pair
        source_sample, target_sample = node
        arcs = dict()

        # just play
        try:
            next_source_sample = self.get_next_cut(source_sample) # just play until next cut
            next_target_sample = target_sample + next_source_sample - source_sample # increment target by length of played segment
            arcs[(next_source_sample, next_target_sample)] = 0.0 # store error for jump to this node
        except KeyError:
            pass

        # jump and play
        for stop_sample, cut_error in self._cuts[source_sample].items(): # find possible samples to jump to
            try:
                next_source_sample = self.get_next_cut(stop_sample) # play until next cut
                next_target_sample = target_sample + next_source_sample - stop_sample # increment target by length of played segment
                arcs[(next_source_sample, next_target_sample)] = cut_error # store error for jump to this node
            except KeyError:
                pass

        # just jump to end in target if end in source is reached (very bad idea)
        if source_sample == self._source_end_sample: # TODO make this generic for constraints within song
            arcs[(self._source_end_sample, self._target_end_sample)] = (target_sample - self._target_end_sample) ** 2 # TODO weighting

        return arcs
    
    def __getitem__(self, key):
        return self.get_arcs_from(key)

    def dump(self, f): # TODO non-recursive
        f = open(f, "w")
        print >> f, "size(100);"
        print >> f, "defaultpen(0.001);"

        s0 = 0
        t0 = 0

        queue = deque((s0, t0, s1, t1) for (s1, t1) in self[(s0, t0)] if t1 < self._target_end_sample)
        while queue:
            s0, t0, s1, t1 = queue.popleft()
            print >> f, "draw((%d, %d) -- (%d, %d), arrow=Arrow(size=0.1));" % (s0, t0, s1, t1)
            queue.extend((s1, t1, s2, t2) for (s2, t2) in self[(s1, t1)] if t1 < self._target_end_sample)

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

    """
    # display selected cut
    selected_cut = 28
    start_sample, stop_sample, best_d = best[selected_cut]
    a = data[start_sample - initial_block_length / 2 : start_sample + initial_block_length / 2]
    b = data[stop_sample - initial_block_length / 2 : stop_sample + initial_block_length / 2]
    t = arange(-initial_block_length / 2, initial_block_length / 2) / float(fs)
    figure()
    plot(t, a)
    hold(True)
    plot(t, b)
    plot([0, 0], [-1, 1])
    hold(False)

    # write write selected cut to file
    start_time = divmod(start_sample / float(fs), 60)
    stop_time = divmod(stop_sample / float(fs), 60)
    print "At sample %d (%d:%04.1f), we will skip to sample %d (%d:%04.1f)." % ((start_sample,) + start_time + (stop_sample,) + stop_time)
    wavwrite(concatenate((data[start_sample-before-fade_in:start_sample], data[stop_sample:stop_sample+after+fade_out])), outfilename, fs, enc)
    wavwrite(data[stop_sample:start_sample], loopfilename, fs, enc)

    # TODO do something with the result (see architectural synthesis)
    """
    print "Creating CutGraph..."
    graph = CutGraph(best, 3 * len(data) / 2, (0, len(data)))
    print "Done creating CutGraph."
    """
    print "Printing CutGraph..."
    try:
        graph.dump("test.asy")
    except KeyboardInterrupt:
        os.system("head -1000 test.asy > test2.asy && asy test2.asy && epstopdf test2.eps && acroread test2.pdf")
    print "Done printing CutGraph."
    #path = dijkstra.shortestPath(graph, (0, 0), (len(data), 3 * len(data) / 2))
    #print path
    """

    # Markov random chain
    # TODO create random random seed and save seed and parameters
    parts = [] # list of all sample parts
    current_cut = 0 # start with first source sample
    last_cut = current_cut # play start
    next_cut = current_cut # jump start
    current_position = 0
    while current_cut != len(data): # while we are not at the end of the sample
        if current_cut != next_cut: # we jumped
            new_position = current_position + next_cut - last_cut
            print "Copy %d:%05.2f -- %d:%05.2f in sample to %d:%05.2f -- %d:%05.2f in target." % (divmod(last_cut / float(fs), 60) + divmod(next_cut / float(fs), 60) + divmod(current_position / float(fs), 60) + divmod(new_position / float(fs), 60))
            last_cut = current_cut
            current_position = new_position
        print current_cut # DEBUG
        next_cut = graph.get_next_cut(current_cut) # detect next possible jump
        parts.append((current_cut, next_cut)) # play from current to next cut
        cuts = graph.get_cuts(next_cut) # get possible jumps
        cut_positions = array([next_cut,] + cuts.keys(), int) # either do nothing or jump
        cut_errors = array([0.0,] + cuts.values()) # error is zero for doing nothing, something for jump
        cut_probs = exp(-array(cut_errors)) # TODO
        current_cut = cut_positions[diff(concatenate(([False], cumsum(cut_probs) > random_sample() * sum(cut_probs))))][0] # find cut
    new_position = current_position + next_cut - last_cut
    print "Copy %d:%05.2f -- %d:%05.2f in sample to %d:%05.2f -- %d:%05.2f in target." % (divmod(last_cut / float(fs), 60) + divmod(next_cut / float(fs), 60) + divmod(current_position / float(fs), 60) + divmod(new_position / float(fs), 60))
    wavwrite(concatenate([data[start:end] for start, end in parts]), outfilename, fs, enc)

