from ..algorithm import PiecewisePathAlgorithm, Path, Cut, Segment, Keypoint

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
    """Priority algorithm for finding paths."""

    def __init__(self, max_num_cuts=4):
        self.max_num_cuts = int(max_num_cuts)

    def get_paths(self, keypoints, cuts):
        """Return all cuts with at most `self.max_num_cuts` cuts in breadth-first order."""
        for num_cuts in range(self.max_num_cuts + 1):
            if num_cuts == 0:
                paths = [PriorityPath(keypoints)] # initial path with no cuts
            else:
                paths = [path + cut for path in paths for cut in cuts if path.can_append(cut)] # produce all paths with num_cuts cuts
            for path in paths: # yield all paths with num_cuts cuts
                yield path

    def find_path(self, source_start, source_end, target_duration, cuts):
        return min(self.get_paths([Keypoint(source_start, 0), Keypoint(source_end, target_duration)], cuts))

