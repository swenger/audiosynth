from numpy import unique, prod

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

