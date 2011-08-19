from heapq import heappush, heappop
from bisect import bisect
from numpy import unique, prod

from ..algorithm import Segment, Path, PiecewisePathAlgorithm, Keypoint

def find_next(item, sorted_list):
    return sorted_list[bisect(sorted_list, item)]

class CostAwarePath(Path):
    def __init__(self, segments=None, keypoints=None, cut_cost=0):
        super(CostAwarePath, self).__init__(segments, keypoints)
        self.cut_cost = cut_cost

    def add_segment(self, cost, segment):
        self.cut_cost += cost
        self += segment

    def cost(self, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = abs(self.duration - (self.keypoints[-1].target - self.keypoints[0].target)) ** 2
        repetition_cost = (prod([self.segments.count(x) for x in unique(self.segments)]) - 1)
        return duration_penalty * duration_cost + cut_penalty * self.cut_cost + repetition_penalty * repetition_cost

    @property
    def end(self):
        try:
            return self.segments[-1].end
        except IndexError:
            return self.keypoints[0].source

class GreedyPathAlgorithm(PiecewisePathAlgorithm):
    def __init__(self, num_paths=10, grace_period=0):
        self.num_paths, self.grace_period = num_paths, grace_period

    def find_path(self, source_start, source_end, target_duration, cuts):
        # all sample points that can be the end of a copied segment
        segment_ends = unique([cut.start for cut in cuts] + [source_start, source_end])
        # for each segment end, a dict of options where the next segment could end to (associated error, start of copying)
        self.options = dict()

        # create options for cuts
        for segment_end, segment_start, cut_error in cuts:
            # segment that would be copied if we would first skip, than continue playing
            skip_play_segment = Segment(segment_start, find_next(segment_start, segment_ends))
            try:
                # segment that would be copied if we would just continue playing
                just_play_segment = Segment(segment_end, find_next(segment_end, segment_ends))
                # just playing is an option
                default = {just_play_segment.end: (0.0, just_play_segment)}
                # add skipping and playing to the dict of options
                self.options.setdefault(segment_end, default)[skip_play_segment.end] = (cut_error, skip_play_segment)
            except IndexError:
                # add skipping to the dict of options
                self.options.setdefault(segment_end, {})[skip_play_segment.end] = (cut_error, skip_play_segment)

        # create options for positions
        for segment_end in [source_start, source_end]:
            try:
                # segment that would be copied if we would just continue playing
                just_play_segment = Segment(segment_end, find_next(segment_end, segment_ends))
                # just playing is an option
                default = {just_play_segment.end: (0.0, just_play_segment)}
                # add playing to the dict of options
                self.options.setdefault(segment_end, default)
            except IndexError:
                # add empty dict of options
                self.options.setdefault(segment_end, {})

        # find paths
        processed = 0
        incomplete = [CostAwarePath([Keypoint(source_start, 0), Keypoint(source_end, target_duration)])] # sorted list of incomplete paths
        complete = [] # sorted list of complete paths

        while incomplete and len(complete) < self.num_paths: # still incomplete paths to process
            print "\r%d paths processed, %d in queue, %d completed" % (processed, len(incomplete), len(complete)),
            path = heappop(incomplete) # get shortest incomplete path
            processed += 1
            for option in self.options[path.end].values():
                newpath = CostAwarePath(path.segments[:], path.keypoints[:], path.cut_cost)
                newpath.add_segment(*option) # add a possible cut
                if newpath.end == source_end: # path arrived at end of source
                    heappush(complete, newpath)
                elif newpath.duration <= target_duration + self.grace_period: # adding cuts to path will make it better
                    heappush(incomplete, newpath)
        
        print "\r%d paths processed, %d in queue, %d completed" % (processed, len(incomplete), len(complete))
        print "total cost of best path is %e (%e cuts, %e duration, %e repetition)" % \
                (complete[0].errorfunc, complete[0].cost_error, complete[0].duration_error, complete[0].repetition_error)
        return complete[0]

