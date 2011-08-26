# similar to the constructor of Graph in pathsearch.py
# Writing this helped me to understand the data better and I feel more comfortable 
def create_automata(best, start, end):
    # return an automata as a dict, which is indexable by the startframes of the segments
    # best shall contain the start and the end of the file as the biggest value
    sorted_best = sorted(best)
    # create a list of segments, which represent the input file without jumps
    # [(pos1, pos2), (pos2, pos3), ...]
    segments = []
    frame_to_segment_begin = dict()
    frame_to_segment_end = dict()
    sorted_best.append((end, 0, 0))
    for item in sorted_best:
        new_segment = Segment(start, item[0])
        frame_to_segment_begin[start] = new_segment
        frame_to_segment_end[item[0]] = new_segment
        segments.append(new_segment)
        start = item[0] # +1 waere schoener
    sorted_best.pop()

    # link all segments so that each segments points to its possible successors
    previous_segment = segments[0]
    for segment in segments[1:]:
        previous_segment += (0.0, segment)
        previous_segment = segment

    # all segments are in our list, so look at inter-segment jumps
    for item in sorted_best:
        frame_to_segment_end[item[0]] += (item[2], frame_to_segment_begin[item[1]])

    assert is_automata_correct(segments)

    return frame_to_segment_begin

def is_automata_correct(segments):
    # now check if everything worked fine
    # every segment should have a jump to its direct successor with no cost
    # every segment should have at leat one jump to another segment somehwere in the file
    # the end segment should have no jumps at all
    # there may be music where it might be possible to jump after the end right into the middle of the music again but I don't consider that
    ret_val = True
    for segment in segments[:-1]:
        ret_val &= 0.0 in segment
        ret_val &= len(segment.followers) > 1
    ret_val &= len(segments[-1].followers) == 0
    return ret_val

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
        # add a segment, which may be choosen after this one
        # follower is a tuple (cost, segment)
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
        
    @property
    def following_segment(self):
        return self._followers[sorted(self._followers)[0]]
        
    @property
    def has_followers(self):
        return self._followers != dict()
