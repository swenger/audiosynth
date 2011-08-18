from heapq import heappush, heappop
from bisect import bisect
from numpy import unique, prod

# TODO turn this into a PathAlgorithm subclass

def find_next(item, sorted_list):
    return sorted_list[bisect(sorted_list, item)]

class Segment(object):
    def __init__(self, start, end):
        self._start = start
        self._end = end
    
    @property
    def duration(self):
        return self._end - self._start

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    def __str__(self):
        return "%d--%d" % (self.start, self.end)

    def __repr__(self):
        return "Segment(%d, %d)" % (self.start, self.end)

class Path(object):
    def __init__(self, source_start, target_duration, cost_factor, duration_factor, repetition_factor):
        self._source_start = source_start
        self._target_duration = target_duration
        self._cost_factor = cost_factor
        self._duration_factor = duration_factor
        self._repetition_factor = repetition_factor
        self._duration = 0
        self._cost = 0
        self._segments = []

    def __str__(self):
        return "duration %d, cost %e: %s." % (self.duration, self.cost, ", ".join(map(str, self._segments)))

    @property
    def cost(self):
        return self._cost

    @property
    def duration(self):
        return self._duration

    @property
    def cost_error(self):
        return self._cost_factor * self._cost

    @property
    def duration_error(self):
        return self._duration_factor * abs(self._duration - self._target_duration) ** 2

    @property
    def repetition_error(self):
        return self._repetition_factor * (prod([self._segments.count(x) for x in unique(self._segments)]) - 1)

    @property
    def errorfunc(self):
        return self.cost_error + self.duration_error + self.repetition_error

    @property
    def segments(self):
        return self._segments

    @property
    def start(self):
        try:
            return self._segments[0]._start
        except IndexError:
            return self._source_start

    @property
    def end(self):
        try:
            return self._segments[-1]._end
        except IndexError:
            return self._source_start

    def copy(self):
        ret = Path(self._source_start, self._target_duration, self._cost_factor, self._duration_factor, self._repetition_factor)
        ret._duration = self._duration
        ret._cost = self._cost
        ret._segments = self._segments[:]
        return ret

    def __add__(self, (cost, segment)):
        ret = self.copy()
        ret += (cost, segment)
        return ret

    def __iadd__(self, (cost, segment)):
        self._cost += cost
        self._duration += segment.duration
        self._segments.append(segment)
        return self

    def __lt__(self, other):
        return self.errorfunc < other.errorfunc

    def __le__(self, other):
        return self.errorfunc <= other.errorfunc

    def __eq__(self, other):
        return self._segments == other._segments

    def __ne__(self, other):
        return not (self._segments == other._segments)

    def __gt__(self, other):
        return self.errorfunc > other.errorfunc

    def __ge__(self, other):
        return self.errorfunc >= other.errorfunc

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

