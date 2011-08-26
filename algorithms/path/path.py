from numpy import unique, prod
from random import choice

def create_path_from_loop(loop, target_duration, cost_factor, duration_factor, repetition_factor):
    segment_list = zip(loop.path, range(len(loop.path)), loop.cost)
    return Path(loop.path[0], target_duration, cost_factor, duration_factor, repetition_factor, segment_list)

class PathNotMathingToLoopError(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

# TODO put _cost and _segments into a list of pairs with tuples (segment, cost)
class Path(object):
    def __init__(self, source_start, target_duration, cost_factor, duration_factor, repetition_factor, segments = []):
        # segments is a list of tuple (segment, iterator, cost)
        # iterator is not used
        self._source_start = source_start
        self._target_duration = target_duration
        self._cost_factor = cost_factor
        self._duration_factor = duration_factor
        self._repetition_factor = repetition_factor
        self._cost_list = [item[2] for item in segments]
        self._cost = sum(self._cost_list)
        self._segments = [item[0] for item in segments]
        self._duration = sum([segment.duration for segment in self._segments])

    def is_valid(self):
        ret_val = len(self._segments) == len(self._cost_list)
        for i in range(len(self._segments))[:-1]:
            ret_val &= self._segments[i][self._cost_list[i+1]] == self._segments[i+1]
        return ret_val

    def integrate_loop(self, loop):
        # check if by rotating the loop, it can be integrated in to the path
        # loop is a instance of Loop defined in loopsearch
        # TODO handle the case where no segment of the loop is in the path, but can still be integrated
        insertion_points = []
        for segm_nr in range(len(self._segments)):
            for loop_segm_nr in range(len(loop.path)):
                if self._segments[segm_nr] == loop.path[loop_segm_nr]:
                    insertion_points.append((segm_nr, loop_segm_nr))
        if len(insertion_points) == 0:
            raise PathNotMathingToLoopError("No intersection point found for integration of the loop")
        insertion_point = choice(insertion_points)
        ret_val = self.copy()
        # maybe a point of failure
        ret_val._segments = ret_val._segments[:insertion_point[0]] + loop.path[insertion_point[1]:] + loop.path[:insertion_point[1]]  + ret_val._segments[insertion_point[0]:]
        ret_val._cost_list = ret_val._cost_list[:insertion_point[0]+1] + loop.cost[insertion_point[1]+1:] + loop.cost[:insertion_point[1]+1] + ret_val._cost_list[insertion_point[0]+1:]
        assert len(ret_val._segments) == len(ret_val._cost_list)
        return ret_val

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
        return self._cost_factor * self.cost

    @property
    def duration_error(self):
        return self._duration_factor * abs(self._duration - self._target_duration) ** 2

    @property
    def repetition_error(self):
        return self._repetition_factor * (prod([self.segments.count(x) for x in unique(self.segments)]) - 1)

    @property
    def errorfunc(self):
        return self.cost_error + self.duration_error + self.repetition_error

    @property
    def segments(self):
        return self._segments

    @property
    def start(self):
        try:
            return self.segments[0]._start
        except IndexError:
            return self._source_start

    @property
    def end(self):
        try:
            return self.segments[-1]._end
        except IndexError:
            return self._source_start

    def copy(self):
        ret = Path(self.start, self._target_duration, self._cost_factor, self._duration_factor, self._repetition_factor)
        ret._duration = self._duration
        ret._cost_list = self._cost_list[:]
        ret._cost = self._cost
        ret._segments = self._segments[:]
        return ret

    def __add__(self, (cost, segment)):
        ret = self.copy()
        ret += (cost, segment)
        return ret

    def __iadd__(self, (cost, segment)):
        self._cost_list += [cost]
        self._cost += cost
        self._duration += segment.duration
        self._segments.append(segment)
        return self

    def append(self, path):
        # append another path to this one
        # if end and start are the same, the start is removed
        ret_val = self.copy()
        first_item = ret_val._segments[-1] == path._segments[0]
        ret_val._segments += path._segments[first_item:]
        ret_val._cost_list += path._cost_list[first_item:]
        ret_val._cost += path._cost
        if first_item:
            ret_val._cost -= path.cost_list[0]
        return ret_val

    def __lt__(self, other):
        return self.errorfunc < other.errorfunc

    def __le__(self, other):
        return self.errorfunc <= other.errorfunc

    def __eq__(self, other):
        return other != None and self.segments == other.segments

    def __ne__(self, other):
        return not (self.segments == other.segments)

    def __gt__(self, other):
        return self.errorfunc > other.errorfunc

    def __ge__(self, other):
        return self.errorfunc >= other.errorfunc

