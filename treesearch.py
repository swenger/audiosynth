from path import Path
from segment import Segment

from bisect import bisect_left, bisect_right
from math import sqrt

def getPath(best, source_keypoints, target_keypoints, data_len, rate, cost_factor, duration_factor, repetition_factor, num_paths):
    frame_to_segment = create_automata(best, 0, data_len)
    sorted_keys = sorted(frame_to_segment.keys())
    segments = []
    pairs = zip(source_keypoints, target_keypoints)
    old_pair = pairs[0]
    duration_diff = 0
    error = []
    average_segment_length = calc_average_segment_length(frame_to_segment)
    for pair in pairs[1:]:
        duration = pair[1] - old_pair[1]
        new_interval = depthfirstsearch(frame_to_segment, sorted_keys, old_pair[0], pair[0], duration - duration_diff, rate, cost_factor, duration_factor / rate, repetition_factor, num_paths, average_segment_length)
        if new_interval[0] == []:
            break
        if segments == []:
            segments += new_interval[0]
        else:
            segments += new_interval[0][1:]
        error += [new_interval[2]]
        old_pair = pair
        duration_diff += new_interval[1] - duration
    cut_error = sum([cost[0] for cost in error])
    duration_error = sum([cost[1] for cost in error])
    repetition_error = sum([cost[2] for cost in error])
    print "total cost of best path is %e (%e cuts, %e duration, %e repetition)" % (cut_error + duration_error + repetition_error, cut_error, duration_error, repetition_error)
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
    for segment in segments[:-1]:
        ret_val &= 0.0 in segment
        ret_val &= len(segment.followers) > 1
    ret_val &= len(segments[-1].followers) == 0
    return ret_val

def calc_average_segment_length(frame_to_segment):
    total_length = sum([frame_to_segment[segment].duration for segment in frame_to_segment])
    return total_length / len(frame_to_segment)

# searches the path through the automata from source_start to source_end. the length of the path is determined by target_start and target_end
# the idea is to perform a depth first search on a tree, which knots represent choices. either continue playing or skip to the next segment
# the first choice is always to continue playing
# kellertiefe durch durchschnittslaenge der segmente beschraenken?
def depthfirstsearch(frame_to_segment, sorted_keys, source_start, source_end, duration, rate, cost_factor, duration_factor, repetition_factor, num_paths, avg_segm_length):
    start_frame_index = sorted_keys[bisect_right(sorted_keys, source_start)-1]
    end_frame_index = sorted_keys[bisect_right(sorted_keys, source_end)-1]
    start_frame = frame_to_segment[start_frame_index]
    end_frame = frame_to_segment[end_frame_index]
    duration += source_start - start_frame_index + end_frame.end - source_end
    # the duration of the path without the last segment must be < duration and with the last segment >= duration
    segments = [(start_frame, start_frame.__iter__(), 0.0)]
    best_path = None
    segments_duration = start_frame.duration
    iter_count = 0
    tried_paths = 0
    max_stack_size = 1.5 * duration/(avg_segm_length)
    print "Maximum stack size: %f" %(max_stack_size)
    while len(segments) > 0 and (segments[-1][0] != end_frame or tried_paths < num_paths):
        if not (iter_count % 1000):
            print "\rIteration: %d, remaining duration: %f%%, Stack size: %d, Considered paths: %d" % (iter_count, (duration-segments_duration)/duration, len(segments), tried_paths),
        iter_count += 1
        top_item = segments[-1]
        if segments_duration < duration and len(segments) < max_stack_size:
            try:
                new_cost = top_item[1].next()
                new_item = top_item[0][new_cost]
                segments.append((new_item, new_item.__iter__(), new_cost))
                segments_duration += new_item.duration
            except:
                segments.pop()
                segments_duration -= top_item[0].duration
        else:
            if segments[-1][0] == end_frame:
                tried_paths += 1
                new_path = Path(source_start, duration, cost_factor, duration_factor, repetition_factor, segments)
                if best_path == None or new_path.errorfunc < best_path.errorfunc:
                    best_path = new_path
            segments.pop()
            segments_duration -= top_item[0].duration
    print "\rIteration: %d, remaining duration: %f%%, Stack size: %d, Considered paths: %d" % (iter_count, (duration-segments_duration)/duration, len(segments), tried_paths)

    return (best_path.segments, best_path.duration, (best_path.cost_error, best_path.duration_error, best_path.repetition_error))
