from scipy.spatial.distance import cdist, squareform
import heapq
from time import clock

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

def analyze(data, block_length, num_keep, block_length_shrink=16, num_skip_print=3):
    data = data[:block_length * (len(data) // block_length)]
    return AnalysisLayer(data, data, block_length, num_keep, block_length_shrink, num_skip_print)

if __name__ == "__main__":
    infilename = "/local/wenger/Daten/music/test2.wav"
    outfilename = "/local/wenger/Daten/music/test-skip.wav"
    loopfilename = "/local/wenger/Daten/music/test-loop.wav"
    block_length_shrink = 16
    num_levels = 5 # 5 or 6 usually work
    num_cuts = 256
    initial_block_length = block_length_shrink ** (num_levels - 1)

    # read file
    from scikits.audiolab import wavread, wavwrite
    data, fs, enc = wavread(infilename)
    data = mean(data, axis=1) # make mono
    print "The file is %d samples (%d:%04.1f) long, at %d samples per second." % ((len(data),) + divmod(len(data) / float(fs), 60) + (fs,))

    # find good cuts
    t = clock()
    root = analyze(data, initial_block_length, num_cuts, block_length_shrink)
    best = root.get_cuts()
    best.sort(key=lambda x: x[2])
    print "Time for finding %d good cuts was %.1fs." % (len(best), clock() - t)
    
    # display best cuts
    print "There are %d cuts, the best of which are:" % len(best)
    for i, j, d in best[1:40:2]:
        print "sample % 8d to sample % 8d (% 8d samples, %d:%04.1f), error %s" % ((i, j, abs(i - j)) + divmod(abs(i - j) / float(fs), 60) + (d,))

    # display distribution of cuts in i-j-plane and respective errors
    figure()
    bb = array(zip(*best))
    scatter(bb[0] / float(fs), bb[1] / float(fs), c=bb[2], s=5)
    axis("image")
    colorbar()
    title("position and error of cuts")

    # display selected cut
    selected_cut = 10
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
    wavwrite(concatenate((data[:start_sample], data[stop_sample:])), outfilename, fs, enc)
    wavwrite(data[stop_sample:start_sample], loopfilename, fs, enc)

    # TODO do something with the result (see architectural synthesis)

