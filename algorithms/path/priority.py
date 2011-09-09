import itertools
import time

from ..algorithm import PiecewisePathAlgorithm, Path, Cut, Segment, Keypoint, BOOLEANS

class PriorityPath(Path):
    def __init__(self, keypoints, cuts=None):
        segment_starts = [keypoints[0].source] + [cut.end for cut in cuts or []]
        segment_ends = [cut.start for cut in cuts or []] + [keypoints[-1].source]
        segments = [Segment(start, end) for start, end in zip(segment_starts, segment_ends)]
        super(PriorityPath, self).__init__(segments, keypoints)

    def cost(self):
        """Compute the difference between the actual and desired duration."""
        return abs(self.duration - (self.keypoints[-1].target - self.keypoints[0].target))

    def can_append(self, cut):
        """Check whether `cut` can be appended to `self` as the last cut."""
        return self.segments[-1].start < cut.start and cut.end < self.segments[-1].end

    def __add__(self, other):
        """Append cut `other` to `self` as the last cut."""
        if isinstance(other, Cut):
            if not self.can_append(other):
                raise ValueError("cut does not lie within last segment")
            return PriorityPath(self.keypoints, self.cuts + [other])
        else:
            return Path.__add__(self, other)

class PriorityPathAlgorithm(PiecewisePathAlgorithm):
    """Base class for priority algorithms for finding paths."""

    abstract = None

    def __init__(self):
        pass

    def get_paths(self, keypoints, cuts, iterator=None):
        """Return all cuts in breadth-first order."""
        paths = [PriorityPath(keypoints)] # initial path with no cuts
        if iterator is None:
            iterator = itertools.count()
        for num_cuts in iterator:
            base_paths = []
            for path in paths: # yield all paths with num_cuts cuts
                yield path
                base_paths.append(path)
            paths = (path + cut for path in base_paths for cut in cuts if path.can_append(cut)) # produce all paths with num_cuts + 1 cuts

class AbortConditionPathAlgorithm(PriorityPathAlgorithm):
    """Base class for algorithms for finding paths with an abort condition."""

    abstract = None

    def __init__(self, debug=False):
        self.debug = BOOLEANS[debug]

    def find_path(self, source_start, source_end, target_duration, cuts):
        best_path = None
        best_cost = None
        state = self.initialize_find_path(source_start, source_end, target_duration, cuts)
        for num_paths, path in enumerate(self.get_paths([Keypoint(source_start, 0), Keypoint(source_end, target_duration)], cuts), 1):
            if best_cost is None or path.cost() < best_cost:
                best_path = path
                best_cost = path.cost()
            if self.abort_condition_fulfilled(state, best_path, best_cost, path):
                if self.debug:
                    print "%d paths enumerated, maximum number of cuts %d, lowest cost %.2f." % (num_paths, len(path.cuts), best_path.cost())
                return best_path

    def initialize_find_path(self, source_start, source_end, target_duration, cuts):
        """Initialize the path search and return a state object. Override this in subclasses."""
        raise NotImplementedError

    def abort_condition_fulfilled(self, state, best_path, best_cost, path):
        """Check the state object for a fulfilled abort condition. Override this in subclasses."""
        raise NotImplementedError

class MaxRuntimePathAlgorithm(AbortConditionPathAlgorithm):
    """Algorithm for finding paths with fixed runtime."""

    def __init__(self, max_runtime=10.0, debug=False):
        self.max_runtime = float(max_runtime)
        super(MaxRuntimePathAlgorithm, self).__init__(debug)

    def initialize_find_path(self, source_start, source_end, target_duration, cuts):
        return time.time()

    def abort_condition_fulfilled(self, state, best_path, best_cost, path):
        return time.time() - state > self.max_runtime

class MaxNumCutsPathAlgorithm(PriorityPathAlgorithm):
    """Algorithm for finding paths with a maximum number of cuts."""

    def __init__(self, max_num_cuts=4):
        self.max_num_cuts = int(max_num_cuts)

    def find_path(self, source_start, source_end, target_duration, cuts):
        return min(self.get_paths([Keypoint(source_start, 0), Keypoint(source_end, target_duration)], cuts, range(self.max_num_cuts + 1)))

