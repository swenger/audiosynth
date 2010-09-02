from scipy.spatial.distance import cdist, squareform
import heapq

class AnalysisLayer(object):
    def __init__(self, data1, data2, block_length, num_keep, block_length_shrink=16, num_skip_print=3):
        self.block_length = block_length
        if block_length >= block_length_shrink ** num_skip_print: # do not print innermost num_skip_print layers
            print "len(data1) = %d, len(data2) = %d, block_length = %d, num_keep = %d" % (len(data1), len(data2), block_length, num_keep)

        # split data into non-overlapping blocks of length block_length
        blocks1 = data1.reshape(-1, block_length)
        blocks2 = data2.reshape(-1, block_length)

        # compute spectrum of each block (could also be mel analysis or the like)
        feature_vectors1 = abs(fft(blocks1)) # TODO use identity for small samples and MFCCs otherwise
        feature_vectors2 = abs(fft(blocks2)) # TODO use identity for small samples and MFCCs otherwise

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
        
        # reduce block size
        new_block_length = max(block_length / block_length_shrink, 1)

        # keep at least one cut per child
        new_num_keep = max(num_keep / distances.size, 1)

        # if children are not empty, initialize them
        if new_block_length > 1:
            self.children = []
            for i, j, d in zip(self.i, self.j, self.d):
                if not isinf(d):
                    self.children.append(AnalysisLayer(blocks1[i], blocks2[j], new_block_length, new_num_keep))

    def get_cuts(self, weight_factor=1.1, weight=1.0):
        """Return a list of all branches of the tree with their respective weighted length."""
        l = []
        new_weight = weight * weight_factor # lower levels get different weight
        if hasattr(self, "children"):
            for child, si, sj, sc in zip(self.children, self.i, self.j, weight * self.d):
                l += [(si * self.block_length + i, sj * self.block_length + j, sc + d) for i, j, d in child.get_cuts(weight_factor, new_weight)]
        else:
            l += zip(self.i, self.j, weight * self.d)
        return l

def analyze(data, block_length, num_keep):
    data = data[:block_length * (len(data) // block_length)]
    return AnalysisLayer(data, data, block_length, num_keep)

if __name__ == "__main__":
    infilename = "/local/wenger/Daten/music/test.wav"
    outfilename = "/local/wenger/Daten/music/test-skip.wav"
    block_length_shrink = 16
    num_cuts = 256

    from scikits.audiolab import wavread, wavwrite
    data, fs, enc = wavread(infilename)
    data = mean(data, axis=1) # make mono
    print "The file is %d samples (%d:%04.1f) long, at %d samples per second." % ((len(data),) + divmod(len(data) / float(fs), 60) + (fs,))

    root = analyze(data, block_length_shrink ** 4, num_cuts) # find about num_cuts places to cut
    best = root.get_cuts()
    best.sort()
    
    for i, line in enumerate(best[:20]):
        print line

    for best_i, best_j, best_d in best[:5]:
        a = data[best_i - 100 : best_i + 100]
        b = data[best_j - 100 : best_j + 100]
        figure()
        plot(a)
        hold(True)
        plot(b)
        plot([100, 100], [-1, 1])
        hold(False)

    # TODO do something with the result (see architectural synthesis)

