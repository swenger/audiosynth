from ..algorithm import PiecewisePathAlgorithm, Keypoint, Segment as SimpleSegment
from greedy import CostAwarePath

from segment import Segment, create_automata 

from bisect import bisect_right
from math import sqrt
from collections import namedtuple

# searches the path through the automata from source_start to source_end. the length of the path is determined by target_start and target_end
# the idea is to perform a depth first search on a tree, which knots represent choices. either continue playing or skip to the next segment
# the first choice is always to continue playing
# kellertiefe durch durchschnittslaenge der segmente beschraenken?

# Graphen als Aneinanderreihung von Segmenten erstellen
# innerhalb des graphen einen weg zwischen 2 keypoints mit gegener laenge finden
# reicht start und zielsegment sowie die laenge aus?
# laenge muesste je nachdem wo die schluesselstelle in anfang und ziel ist angepasst werden
class DepthFirstPathAlgorithm(PiecewisePathAlgorithm):
    def __init__(self, num_paths=10, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1, avg_stack_size_times_factor = 1.5, avg_segment_divisor = 2):
        self.num_paths = int(num_paths)
        self.duration_penalty = float(duration_penalty)
        self.cut_penalty = float(cut_penalty)
        self.repetition_penalty = float(repetition_penalty)
        self.avg_stack_size_times_factor = float(avg_stack_size_times_factor)
        self.avg_segment_divisor = float(avg_segment_divisor)

    def find_path(self, source_start, source_end, target_duration, cuts):
        frame_to_segment = create_automata(cuts, source_start, source_end)
        sorted_keys = sorted(frame_to_segment.keys())
        avg_segm_length = calc_average_segment_length(frame_to_segment)
        # start and end frame shall be connected with a sequence of a certain duration
        end_frame_index = sorted_keys[bisect_right(sorted_keys, source_end)-1]
        start_frame = frame_to_segment[source_start]
        end_frame = frame_to_segment[end_frame_index]
        # the stack, which contains a tuple of (segment, iterator, cost)
        Stack_Item = namedtuple('Stack_Item', "segment iterator cost duration")
        segments = [Stack_Item(start_frame, start_frame.__iter__(), 0.0, start_frame.duration)]
        iter_count = tried_paths = 0
        # restrict the stack to a maximum depth
        max_stack_size = self.avg_stack_size_times_factor * target_duration/(avg_segm_length)
        print "Maximum stack size: %f" %(max_stack_size)
        best_path = None
        while segments and tried_paths < self.num_paths:
            if not (iter_count % 1000):
                print "\rIteration: %d, Stack size: %d, Considered paths: %d" % (iter_count, len(segments), tried_paths),
            iter_count += 1
            top_item = segments[-1]
            if top_item.duration < target_duration and len(segments) < max_stack_size:
                # if no further candidate is there pop the stack
                try:
                    cost = top_item.iterator.next()
                    new_item = top_item.segment[cost]
                    new_cost = top_item.cost + cost
                    new_duration = top_item.duration + new_item.duration
                    segments.append(Stack_Item(new_item, new_item.__iter__(), new_cost, new_duration))
                except StopIteration:
                    segments.pop()
                    continue
            else:
                segments.pop()
                continue
            # test if we are near the end
            if segments and segments[-1].segment == end_frame and abs(top_item.duration - target_duration) < avg_segm_length/self.avg_segment_divisor:
                tried_paths += 1
                new_path = CostAwarePath(self, [SimpleSegment(stack_item.segment.start, stack_item.segment.end) for stack_item in segments], [Keypoint(source_start, 0), Keypoint(source_end, target_duration)], top_item.cost)
                if best_path is None or new_path < best_path:
                    best_path = new_path
        print "\rFinal Iteration: %d, Stack size: %d, Considered paths: %d" % (iter_count, len(segments), tried_paths)

        return best_path

def calc_average_segment_length(frame_to_segment):
    total_length = sum([frame_to_segment[segment].duration for segment in frame_to_segment])
    return total_length / len(frame_to_segment)
