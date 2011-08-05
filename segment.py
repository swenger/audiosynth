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

