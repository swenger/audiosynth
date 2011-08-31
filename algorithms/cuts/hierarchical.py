import heapq

from numpy import inf, unravel_index, asarray, isinf, floor, log, arange, maximum, eye
from scipy.spatial.distance import cdist
from numpy.fft import fft

from ..algorithm import CutsAlgorithm, Cut

class AnalysisLayer(object):
    def __init__(self, data, (start1, end1), (start2, end2), block_length, num_keep, block_length_shrink=16, min_cut_length=0, raw_layers=1,
            num_skip_print=4):
        data1 = data[start1:end1]
        data2 = data[start2:end2]

        self.block_length = block_length
        if block_length >= block_length_shrink ** num_skip_print: # do not print innermost num_skip_print layers
            print "Finding cuts between blocks (%d, %d) and (%d, %d), keeping %d cuts." % (start1, end1, start2, end2, num_keep)
            # TODO compute time from samples

        # split data into non-overlapping blocks of length block_length
        num_blocks1 = len(data1) // block_length
        num_blocks2 = len(data2) // block_length
        blocks1 = data1.reshape((num_blocks1, block_length) + data1.shape[1:])
        blocks2 = data2.reshape((num_blocks2, block_length) + data2.shape[1:])

        # reduce block size
        new_block_length = max(block_length / block_length_shrink, 1)

        # compute spectrum of each block (could also be mel analysis or the like)
        if block_length < block_length_shrink ** raw_layers: # innermost layers: use raw sample data
            feature_vectors1 = blocks1.reshape(num_blocks1, block_length, -1).mean(axis=2)
            feature_vectors2 = blocks2.reshape(num_blocks2, block_length, -1).mean(axis=2)
        else:
            feature_vectors1 = abs(fft(blocks1.reshape(num_blocks1, block_length, -1).mean(axis=2)))
            feature_vectors2 = abs(fft(blocks2.reshape(num_blocks2, block_length, -1).mean(axis=2)))
        
        # compute distances between feature vectors
        distances = cdist(feature_vectors1, feature_vectors2, "sqeuclidean") # (u - v) ** 2
        normalization = cdist(feature_vectors1, -feature_vectors2, "sqeuclidean") # (u + v) ** 2
        distances[normalization != 0] /= normalization[normalization != 0] # (u - v) ** 2 / (u + v) ** 2
        distances[normalization == 0] = 0.0 # both feature vectors are zero => cut okay

        # disallow cuts below mininum cut length
        if min_cut_length == "block": # disallow entire diagonal block
            if start1 == start2 and end1 == end2:
                distances[eye(len(distances)).astype(bool)] = inf
        else:
            for row, block_start1 in zip(distances, arange(start1, end1, block_length)):
                block_end1 = block_start1 + block_length
                block_start2 = arange(start2, end2, block_length)
                block_end2 = block_start2 + block_length
                row[maximum(abs(block_end2 - 1 - block_start1), abs(block_end1 - 1 - block_start2)) < min_cut_length] = inf

        # find best num_keep off-diagonal child indices and their respective distances
        best = heapq.nsmallest(num_keep, zip(distances.ravel(), range(distances.size)))
        self.i, self.j, self.d = zip(*[unravel_index(i, distances.shape) + (d,) for d, i in best])
        self.i = asarray(self.i, int) # block index of cut within data1
        self.j = asarray(self.j, int) # block index of cut within data2
        self.d = asarray(self.d, float) # quality of cut

        # make sure that any cut that violates the minimum cut length has infinite cost
        assert min_cut_length == "block" or all(maximum(
            abs(start2 + self.j * block_length + block_length - 1 - start1 + self.i * block_length),
            abs(start1 + self.i * block_length + block_length - 1 - start2 + self.j * block_length))
            .flat >= min_cut_length | isinf(self.d))
        
        # keep at least one cut per child
        new_num_keep = max(num_keep / distances.size, 1)

        # if children are not empty, initialize them
        if block_length > 1:
            self.children = []
            for i, j, d in zip(self.i, self.j, self.d):
                if not isinf(d):
                    new_start1 = start1 + i * block_length
                    new_end1 = new_start1 + block_length
                    new_start2 = start2 + j * block_length
                    new_end2 = new_start2 + block_length
                    self.children.append(AnalysisLayer(data, (new_start1, new_end1), (new_start2, new_end2),
                        new_block_length, new_num_keep, block_length_shrink, min_cut_length, num_skip_print))

    def get_cuts(self, weight_factor=2.0, weight=1.0):
        """Return a list of all branches of the tree with their respective weighted length."""
        l = []
        new_weight = weight * weight_factor # lower levels get different weight
        if hasattr(self, "children"):
            for child, si, sj, sd in zip(self.children, self.i, self.j, weight * self.d):
                l += [Cut(si * self.block_length + i, sj * self.block_length + j, sd + d)
                        for i, j, d in child.get_cuts(weight_factor, new_weight)]
        else:
            l += [Cut(i, j, d) for i, j, d in zip(self.i, self.j, weight * self.d)]
        return l

class HierarchicalCutsAlgorithm(CutsAlgorithm):
    """Hierarchical algorithm for finding cuts."""
    
    def __init__(self, num_cuts=256, num_keep=40, block_length_shrink=16, num_levels="max", weight_factor=1.2, min_cut_length="block",
            raw_layers=1):
        self.num_cuts = int(num_cuts)
        self.num_keep = int(num_keep)
        self.block_length_shrink = int(block_length_shrink)
        self.num_levels = num_levels if num_levels == "max" else int(num_levels)
        self.weight_factor = float(weight_factor)
        self.min_cut_length = min_cut_length if min_cut_length == "block" else int(min_cut_length) # TODO compute samples from time
        self.raw_layers = int(raw_layers)

    def __call__(self, data):
        num_levels = min(int(floor(log(0.5 * len(data)) / log(self.block_length_shrink))) + 1,
                float("inf") if self.num_levels == "max" else self.num_levels)
        assert floor(len(data) // (self.block_length_shrink ** (num_levels - 1))) > 1
        assert len(data) >= 2 * self.block_length_shrink ** (num_levels - 1)
        assert log(0.5 * len(data)) / log(self.block_length_shrink) >= num_levels - 1
        assert num_levels <= 1 + log(0.5 * len(data)) / log(self.block_length_shrink)
        # => num_levels = floor(log(0.5 * len(data)) / log(self.block_length_shrink) + 1)
        
        block_length = self.block_length_shrink ** (num_levels - 1)
        start, end = 0, block_length * (len(data) // block_length)
        root = AnalysisLayer(data, (start, end), (start, end), block_length, self.num_cuts, self.block_length_shrink, self.min_cut_length,
                self.raw_layers)
        cuts = root.get_cuts(self.weight_factor)
        cuts.sort(key=lambda x: x[2])

        assert self.min_cut_length == "block" or all(abs(c.start - c.end) >= self.min_cut_length or isinf(c.cost) for c in cuts), \
                "some cuts are shorter than min_cut_length"

        return cuts[:self.num_keep] if self.num_keep else cuts

