import re
from segment import Segment

def frametime(frame, rate=1, minute_digits=2, decimals=2):
    """Convert a frame number to a time signature."""
    minutes, seconds = divmod(frame / float(rate), 60)
    return "%0*d:%0*.*f" % (minute_digits, minutes, 3 + decimals, decimals, seconds)

def make_lookup(dtype, **constants):
    """Try to read a value from a dictionary; if it fails, cast the value to the specified type."""
    def lookup(x):
        try:
            return constants[x]
        except KeyError:
            return dtype(x)
    return lookup

def ptime(s):
    """Parse a time from a string."""
    r = re.compile(r"(?:(?:(\d+):)?(\d+):)?(\d+(?:.\d+)?)")
    h, m, s = r.match(s).groups()
    return int(h or 0) * 60 * 60 + int(m or 0) * 60 + float(s)

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
