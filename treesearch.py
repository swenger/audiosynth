from path import Path
from segment import Segment

def getPath(best, source_keypoints, target_keypoints, data_len, rate, cost_factor, duration_factor, repetition_factor, num_paths):
    frame_to_segment = create_automata(best, source_keypoints[0], source_keypoints[len(source_keypoints)-1])
    start = frame_to_segment[source_keypoints[0]]
    segments = [start]
    # TODO verkackt, wenn man alternative spruenge drin hat -> endlosschleife
    while not start.is_empty():
        next_index = start.__iter__().next()
        start = start[next_index]
        segments.append(start)
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

    # now check if everything worked fine
    # every segment should have a jump to its direct successor with no cost
    # every segment should have at leat one jump to another segment somehwere in the file
    # the end segment should have no jumps at all
    # there may be music where it might be possible to jump after the right into it again but I don't consider it
    for segment in segments[:len(segments)-2]:
        assert 0.0 in segment
        assert len(segment.followers) > 1
    assert len(segments[len(segments)-1].followers) == 0

    return frame_to_segment_begin
