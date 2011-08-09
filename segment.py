class Segment(object):
    def __init__(self, start, end):
        self._start = start
        self._end = end
        # a list of (cost, segment)
        # this list contains the segments which may be played after this one
        # with a certain cost
        # TODO maybe allowing each key more than once would be good
        self._followers = dict()
    
    @property
    def duration(self):
        return self._end - self._start

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def followers(self):
        return self._followers.copy()

    def __str__(self):
        return "%d--%d" % (self.start, self.end)

    def __repr__(self):
        ret_val = "Segment(%d, %d" % (self.start, self.end)
        for f in self._followers:
            ret_val += ", " + "(" + str(f) + ", " + str(self._followers[f]) + ")"
        return ret_val + ")"

    def __add__(self, follower):
        seg = Segment(self._start, self._end)
        seg._followers = self._followers.copy()
        seg += follower
        return seg

    def __iadd__(self, follower):
        # when this assertion breaks, it is time to allow for each key more than one item
        # hopefully this will never break
        assert not follower[0] in self._followers
        assert follower[0] >= 0.0
        self._followers[follower[0]] = follower[1]
        return self

    def __iter__(self):
       return sorted(self._followers).__iter__()

    def __getitem__(self, index):
        return self._followers[index]
