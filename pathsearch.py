from heapq import heappush, heappop
from bisect import bisect
from numpy import unique

from path import Path
from segment import Segment

def getPath(best, source_keypoints, target_keypoints, data_len, rate, cost_factor, duration_factor, repetition_factor, num_paths):
    # perform graph search TODO find a globally optimal path through all keypoints at once
    g = Graph(best, [0] + sorted(source_keypoints) + [data_len])
    segments = []
    for start, end, target_end in zip(source_keypoints, source_keypoints[1:], target_keypoints[1:]):
        duration = target_end - sum(s.end - s.start for s in segments)
        paths = g.find_paths(start=start, end=end, duration=duration, cost_factor=cost_factor,
                duration_factor=duration_factor / rate, repetition_factor=repetition_factor, num_paths=num_paths)
        segments += paths[0].segments
    return segments

def find_next(item, sorted_list):
    return sorted_list[bisect(sorted_list, item)]

class Graph(object):
    def __init__(self, cuts, positions):
        # all sample points that can be the end of a copied segment
        segment_ends = unique([cut[0] for cut in cuts] + list(positions))
        # for each segment end, a dict of options where the next segment could end to (associated error, start of copying)
        self._options = dict()

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
                self._options.setdefault(segment_end, default)[skip_play_segment.end] = (cut_error, skip_play_segment)
            except IndexError:
                # add skipping to the dict of options
                self._options.setdefault(segment_end, {})[skip_play_segment.end] = (cut_error, skip_play_segment)

        # create options for positions
        for segment_end in positions:
            try:
                # segment that would be copied if we would just continue playing
                just_play_segment = Segment(segment_end, find_next(segment_end, segment_ends))
                # just playing is an option
                default = {just_play_segment.end: (0.0, just_play_segment)}
                # add playing to the dict of options
                self._options.setdefault(segment_end, default)
            except IndexError:
                # add empty dict of options
                self._options.setdefault(segment_end, {})

    def get_identity_path(self, start, end, duration, cost_factor, duration_factor, repetition_factor):
        p = Path(start, duration, cost_factor, duration_factor, repetition_factor)
        while True:
            try:
                cost, segment = min(self._options[p.end].values())
            except ValueError:
                break
            if cost != 0.0:
                break
            p += (cost, segment)
        if p.end == end:
            return p
        else:
            return None

    def find_paths(self, start, end, duration, cost_factor, duration_factor, repetition_factor, num_paths=10, grace_period=0):
        processed = 0
        incomplete = [Path(start, duration, cost_factor, duration_factor, repetition_factor)] # sorted list of incomplete paths
        initial_path = self.get_identity_path(start, end, duration, cost_factor, duration_factor, repetition_factor)
        if initial_path is not None:
            print "total cost of initial path is %e (%e cuts, %e duration, %e repetition)" % (initial_path.errorfunc, initial_path.cost_error, initial_path.duration_error, initial_path.repetition_error)
            complete = [initial_path] # sorted list of complete paths
        else:
            complete = [] # sorted list of complete paths

        while incomplete and len(complete) < num_paths: # still incomplete paths to process
            print "\r%d paths processed, %d in queue, %d completed" % (processed, len(incomplete), len(complete)),
            item = heappop(incomplete) # get shortest incomplete path
            processed += 1
            for option in self._options[item.end].values():
                newitem = item + option # add a possible cut
                if newitem.end == end: # path arrived at end of source
                    heappush(complete, newitem)
                elif newitem.duration <= duration + grace_period: # adding cuts to path will make it better (or allow it to reach end of source)
                    heappush(incomplete, newitem)
        
        print "\r%d paths processed, %d in queue, %d completed" % (processed, len(incomplete), len(complete))
        print "total cost of best path is %e (%e cuts, %e duration, %e repetition)" % (complete[0].errorfunc, complete[0].cost_error, complete[0].duration_error, complete[0].repetition_error)
        return complete

