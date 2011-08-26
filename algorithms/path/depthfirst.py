from path import Path
from segment import Segment
from utilities import create_automata 

from bisect import bisect_left, bisect_right
from math import sqrt

# Graphen als Aneinanderreihung von Segmenten erstellen
# innerhalb des graphen einen weg zwischen 2 keypoints mit gegener laenge finden
# reicht start und zielsegment sowie die laenge aus?
# laenge muesste je nachdem wo die schluesselstelle in anfang und ziel ist angepasst werden

def getPath(best, source_keypoints, target_keypoints, data_len, rate, cost_factor, duration_factor, repetition_factor, num_paths):
    frame_to_segment = create_automata(best, 0, data_len)
    average_segment_length = calc_average_segment_length(frame_to_segment)
    sorted_keys = sorted(frame_to_segment.keys())
    # put corresponding keypoints together
    pairs = zip(source_keypoints, target_keypoints)
    # if the duration in the previous step wasn't hit save the difference for the next step
    duration_diff = 0
    costs = []
    segments = []
    old_pair = pairs[0]
    # for each previous and current pair find the path between them with the minimal cost
    for pair in pairs[1:]:
        duration = pair[1] - old_pair[1]
        new_interval = depthfirstsearch(frame_to_segment, sorted_keys, old_pair[0], pair[0], duration - duration_diff, rate, cost_factor, duration_factor / rate, repetition_factor, num_paths, average_segment_length)
        # no solution?
        if new_interval[0] == []:
            break
        if segments == []:
            segments += new_interval[0]
        else:
            segments += new_interval[0][1:]
        costs += [new_interval[2]]
        old_pair = pair
        duration_diff += new_interval[1] - duration
    cut_error = sum([cost[0] for cost in costs])
    duration_error = sum([cost[1] for cost in costs])
    repetition_error = sum([cost[2] for cost in costs])
    print "total cost of best path is %e (%e cuts, %e duration, %e repetition)" % (cut_error + duration_error + repetition_error, cut_error, duration_error, repetition_error)
    return segments

def calc_average_segment_length(frame_to_segment):
    total_length = sum([frame_to_segment[segment].duration for segment in frame_to_segment])
    return total_length / len(frame_to_segment)

# searches the path through the automata from source_start to source_end. the length of the path is determined by target_start and target_end
# the idea is to perform a depth first search on a tree, which knots represent choices. either continue playing or skip to the next segment
# the first choice is always to continue playing
# kellertiefe durch durchschnittslaenge der segmente beschraenken?
def depthfirstsearch(frame_to_segment, sorted_keys, source_start, source_end, duration, rate, cost_factor, duration_factor, repetition_factor, num_paths, avg_segm_length):
    # start and end frame shall be connected with a sequence of a certain duration
    start_frame_index = sorted_keys[bisect_right(sorted_keys, source_start)-1]
    end_frame_index = sorted_keys[bisect_right(sorted_keys, source_end)-1]
    start_frame = frame_to_segment[start_frame_index]
    end_frame = frame_to_segment[end_frame_index]
    duration += source_start - start_frame_index + end_frame.end - source_end
    # the stack, which contains a tuple of (segment, iterator, cost)
    segments = [(start_frame, start_frame.__iter__(), 0.0)]
    segments_duration = start_frame.duration
    iter_count = tried_paths = 0
    # restrict the stack to a maximum depth
    # TODO calculate proper value, or parametrize
    max_stack_size = 2 * duration/(avg_segm_length)
    print "Maximum stack size: %f" %(max_stack_size)
    best_path = None
    while len(segments) > 0 and (segments[-1][0] != end_frame or tried_paths < num_paths):
        if not (iter_count % 1000):
            print "\rIteration: %d, remaining duration: %f%%, Stack size: %d, Considered paths: %d" % (iter_count, (duration-segments_duration)/duration*100, len(segments), tried_paths),
        iter_count += 1
        top_item = segments[-1]
        if segments_duration < duration and len(segments) < max_stack_size:
            # if no further candidate is there pop the stack
            try:
                new_cost = top_item[1].next()
                new_item = top_item[0][new_cost]
                segments.append((new_item, new_item.__iter__(), new_cost))
                segments_duration += new_item.duration
            except:
                segments.pop()
                segments_duration -= top_item[0].duration
        else:
            segments.pop()
            segments_duration -= top_item[0].duration
        # test if we are near the end
        if segments and segments[-1][0] == end_frame and abs(segments_duration - duration) < end_frame.duration/2:
#        if segments[-1][0] == end_frame and segments_duration >= duration:
            tried_paths += 1
            new_path = Path(source_start, duration, cost_factor, duration_factor, repetition_factor, segments)
            if best_path == None or new_path.errorfunc < best_path.errorfunc:
                best_path = new_path
    print "\rIteration: %d, remaining duration: %f%%, Stack size: %d, Considered paths: %d" % (iter_count, (duration-segments_duration)/duration*100, len(segments), tried_paths)

    return (best_path.segments, best_path.duration, (best_path.cost_error, best_path.duration_error, best_path.repetition_error))
