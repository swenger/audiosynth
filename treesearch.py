from path import Path
from segment import Segment

from bisect import bisect_left, bisect_right

def getPath(best, source_keypoints, target_keypoints, data_len, rate, cost_factor, duration_factor, repetition_factor, num_paths):
    frame_to_segment = create_automata(best, 0, data_len)
    sorted_keys = sorted(frame_to_segment.keys())
    segments = []
    pairs = zip(source_keypoints, target_keypoints)
    old_pair = pairs[0]
    duration_diff = 0
    for pair in pairs[1:]:
        duration = pair[1] - old_pair[1]
        new_interval = depthfirstsearch(frame_to_segment, sorted_keys, old_pair[0], pair[0], duration - duration_diff, cost_factor, duration_factor, repetition_factor)
        if new_interval[0] == []:
            break
        else:
            if segments == []:
                segments += new_interval[0]
            else:
                segments += new_interval[0][1:]
        old_pair = pair
        duration_diff += new_interval[1] - duration
    return segments

# Graphen als Aneinanderreihung von Segmenten erstellen
# innerhalb des graphen einen weg zwischen 2 keypoints mit gegener laenge finden
# reicht start und zielsegment sowie die laenge aus?
# laenge muesste je nachdem wo die schluesselstelle in anfang und ziel ist angepasst werden

# similar to the constructor of Graph in pathsearch.py
# Writing this helped me to understand the data better and I feel more comfortable 
def create_automata(best, start, end):
    # best shall contain the start/0 and the end of the file as the biggest value
    sorted_best = sorted(best)
    # create a list of segments, which represent the input file without jumps
    # [(pos1, pos2), (pos2+1, pos3), ...]
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

    # link all segments so that each segments points on its possible successors
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
    # there may be music where it might be possible to jump after the right into it again but I don't consider it
    ret_val = True
    for segment in segments[:len(segments)-2]:
        ret_val &= 0.0 in segment
        ret_val &= len(segment.followers) > 1
    ret_val &= len(segments[len(segments)-1].followers) == 0
    return ret_val

# searches the path through the automata from source_start to source_end. the length of the path is determined by target_start and target_end
# the idea is to perform a depth first search on a tree, which knots represent choices. either continue playing or skip to the next segment
# the first choice is always to continue playing
def depthfirstsearch(frame_to_segment, sorted_keys, source_start, source_end, duration, cost_factor, duration_factor, repetition_factor):
    start_frame_index = sorted_keys[bisect_right(sorted_keys, source_start)-1]
    end_frame_index = sorted_keys[bisect_right(sorted_keys, source_end)-1]
    start_frame = frame_to_segment[start_frame_index]
    end_frame = frame_to_segment[end_frame_index]
    duration += source_start - start_frame_index + end_frame.end - source_end
    # the duration of the path without the last segment must be < duration and with the last segment >= duration
    last_item = lambda x: x[len(x) - 1 ]
    segments = [(start_frame, start_frame.__iter__())]
    segments_duration = start_frame.duration
    iter_count = 0
#    while len(segments) > 0 and (last_item(segments)[0] != end_frame or segments_duration < duration):
    while len(segments) > 0 and (last_item(segments)[0] != end_frame or abs(segments_duration - duration) > 1000000):
        print "\rIteration: %d, remaining duration in percent: %f, Stack size: %d" % (iter_count, (duration-segments_duration)/duration, len(segments))
        iter_count += 1
        top_item = last_item(segments)
        if segments_duration < duration:
            try:
                new_item = top_item[0][top_item[1].next()]
                segments.append((new_item, new_item.__iter__()))
                segments_duration += new_item.duration
            except:
                segments.pop()
                segments_duration -= top_item[0].duration
        else:
            segments.pop()
            segments_duration -= top_item[0].duration

    segments = [segment[0] for segment in segments]

    return (segments, segments_duration)
            
