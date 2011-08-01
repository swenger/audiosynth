from numpy import isnan, inf, eye, unravel_index, asarray, isinf
from scipy.spatial.distance import cdist
import heapq
from numpy.fft import fft

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
            feature_vectors1 = blocks1.reshape(num_blocks1, block_length, -1).mean(axis=2)
            feature_vectors2 = blocks2.reshape(num_blocks2, block_length, -1).mean(axis=2)
        else:
            feature_vectors1 = abs(fft(blocks1.reshape(num_blocks1, block_length, -1).mean(axis=2)))
            feature_vectors2 = abs(fft(blocks2.reshape(num_blocks2, block_length, -1).mean(axis=2)))
        
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
    cuts.sort(key=lambda x: x[2])
    return cuts


