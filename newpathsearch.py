from heapq import heappush, heappop
from numpy import cumsum
from bisect import bisect
from copy import deepcopy

# TODO turn this into a PathAlgorithm subclass

# TODO genetic algorithm: crossover, selection, mutation
# TODO make mutate() work as a generator
# TODO make segments and paths immutable, add slots, cache cumsum
# TODO move class variables of Path into members of an Algorithm class

class Segment(object):
    def __init__(self, start, end):
        self.start, self.end = start, end

    def __contains__(self, pos):
        """Check if the segment contains the given position."""
        return self.start <= pos < self.end

    def length(self):
        """Return the length of the segment."""
        return self.end - self.start

    def distance(self, offset, source_pos, target_pos): # TODO test this
        """Compute the squared distance of this segment from the given key point."""
        dex, dey = source_pos - self.end, offset + self.length() - target_pos
        if dex > dey:
            return dex ** 2 + dey ** 2
        dex, dey = self.start - source_pos, target_pos - offset
        if dex > dey:
            return dex ** 2 + dey ** 2
        return 0.25 * (dex + dey) ** 2

class Path(object):
    source_keypoints = []
    target_keypoints = []

    def __init__(self, segments):
        self.segments = segments

    def copy(self):
        """Return a deep copy of this path."""
        return deepcopy(self)

    def distance(self, source_pos, target_pos):
        """Compute the squared distance of this path from the given key point."""
        return min(s.distance(offset, source_pos, target_pos) for s, offset in zip(self.segments, self.offsets()))
    
    def cost(self):
        """Compute the cost of this path."""
        return sum(self.distance(source_pos, target_pos) for source_pos, target_pos in zip(Path.source_keypoints, Path.target_keypoints))

    def __cmp__(self, other):
        """Compare the cost of two paths."""
        return cmp(self.cost(), other.cost())

    def __len__(self):
        """Compute the duration of this path."""
        return sum(s.end - s.start for s in self.segments)

    def offsets(self):
        """Compute the durations of this path up to, but excluding, each segment."""
        return cumsum([s.end - s.start for s in self.segments])

    def offset(self, segment_idx):
        """Compute the duration of this path up to, but excluding, the given segment."""
        return sum(s.end - s.start for s in self.segments[:segment_idx])

    def locate_segment(self, target_pos):
        """Find the index of the segment containing the specified target position ``target_pos``."""
        idx = bisect(self.offsets(), target_pos)
        if target_pos < 0 or idx >= len(self.segments):
            raise ValueError("target position %s is not contained in path" % target_pos)
        return idx

    def insert_cut(self, target_pos, source_pos):
        """At target position ``target_pos``, jump to source position ``source_pos``."""
        idx = self.locate_segment(target_pos)
        assert self.segments[idx].end > source_pos # TODO find a meaningful way to "insert a cut"
        end = self.segments[idx].start + target_pos - self.offset(idx)
        self.segments[idx:idx+1] = [Segment(self.segments[idx].start, end), Segment(source_pos, self.segments[idx].end)]

    def mutate(self, cuts):
        """Return a list of paths obtained by applying all possible cuts."""
        # TODO exclude repeated cuts
        paths = []
        for source_from, source_to, badness in cuts:
            for idx, segment in enumerate(self.segments):
                if source_from in segment:
                    target_pos = self.offset(idx) + (source_from - segment.start)
                    paths.append(self.copy())
                    paths[-1].insert_cut(target_pos, source_to)
        return paths

def path_search(source_keypoints, target_keypoints, cuts, num_paths=100):
    """Find a path that identifies the ``source_keypoints`` with the corresponding ``target_keypoints``.
    ``cuts`` contains tuples of the form (from_sample, to_sample, cost) of possible jumps in the source.
    The path is returned as a list of segments, which have attributes ``start`` and ``end``."""

    Path.source_keypoints = source_keypoints
    Path.target_keypoints = target_keypoints

    cuts = sorted(cuts) # sort cuts by start position in example

    possible_paths = [Path([Segment(source_keypoints[0], source_keypoints[-1])])]
    complete_paths = []

    while possible_paths and len(complete_paths) < num_paths:
        path = heappop(possible_paths)
        heappush(complete_paths, path)
        possible_paths.extend(path.mutate(cuts))

        print "%d paths complete, %d paths available" % (len(complete_paths), len(possible_paths))

    if possible_paths:
        return min(possible_paths[0], complete_paths[0])
    return complete_paths[0]

