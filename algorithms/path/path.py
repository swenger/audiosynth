from numpy import prod
from random import choice
from collections import namedtuple
from heapq import heappush, heappop
from ..algorithm import Path, Keypoint

Loop = namedtuple('Loop', "duration cost path used")

def is_loop_valid(loop):
    ret_val = LoopPath(None, loop, 0).is_valid()
    ret_val &= loop.path[-1][loop.cost[0]] == loop.path[0]
    return ret_val

def are_loops_valid(loops):
    ret_val = True
    for loop in loops:
        ret_val &= is_loop_valid(loop)
    return ret_val

class PathNotMathingToLoopError(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

def dijkstra(start, end):
    # start/end are segments
    # convert to a usable graph structur and convert back?
    # or build dijkstra myself?
    # build dijkstra myself
    # returns the shortest path from start to end
    priority_queue = [Loop(0, [0], [start], 0)]
    final_segments = []
    while priority_queue and priority_queue[0].path[-1] != end:
        item = heappop(priority_queue)
        # TODO maybe we can use the path to item later
        final_segments.append(item.path[-1])
        new_duration = item.duration + item.path[-1].duration
        for cost in item.path[-1]:
            segment = item.path[-1][cost]
            if not segment in final_segments:
                heappush(priority_queue, Loop(new_duration, item.cost + [cost], item.path + [segment], 0))
    if priority_queue:
        return priority_queue[0]
    else:
        return Loop(-1, [0], [], 0)

# TODO add a reference to loops to the segments (maybe not necessary)
# give a sorted list of loops with their length
# a loop consists of (start, end), length, while start and end are segments or framenumbers
def calc_loops(automata):
    # shortest loop can be achieved by stepping to the successor of the node and then finding a path back to the node by using dijkstra
    # more longer loops can be created by looking, when the shorter one jumped to the start. to create a longer loop don't take the jump and dijkstra again
    # take caution that jumps always move towards the end, if a jump moves away from the end break
    # we want loops where every node is taken only once (finite amount of loops and each loop is unique)
    loops = []
    segment = automata[sorted(automata.keys())[0]]
    end = automata[sorted(automata.keys())[-1]]
    while segment.has_followers:
        for cost in segment:
            next_segment = segment[cost]
            possible_loop = dijkstra(next_segment, segment)
            if possible_loop.duration >= 0:
                # since this is a loop the first element may have a cost != 0
                for cost in possible_loop.path[-1]:
                    if possible_loop.path[-1][cost] == possible_loop.path[0]:
                        possible_loop.cost[0] = cost
                        break
                loops.append(possible_loop)
            # TODO find more loops, by looking after the jump towards the start, really needed?
        segment = segment.following_segment
    return sorted(loops)

class LoopPath(Path):
    def __init__(self, algo, loop, target_duration):
        self.algo = algo
        self.cut_cost = loop.cost[:]
        self.cut_cost[0] = 0
        keypoints = [Keypoint(loop.path[0], 0), Keypoint(loop.path[-1], target_duration)]
        super(LoopPath, self).__init__(loop.path[:], keypoints)

    def is_valid(self):
        ret_val = len(self.segments) == len(self.cut_cost)
        for i in range(len(self.segments))[:-1]:
            ret_val &= self.segments[i][self.cut_cost[i+1]] == self.segments[i+1]
        return ret_val

    def integrate_loop(self, loop):
        # check if by rotating the loop, it can be integrated in to the path
        # loop is a instance of Loop defined in loopsearch
        # TODO handle the case where no segment of the loop is in the path, but can still be integrated
        insertion_points = []
        for segm_nr in range(len(self.segments)):
            for loop_segm_nr in range(len(loop.path)):
                if self.segments[segm_nr] == loop.path[loop_segm_nr]:
                    insertion_points.append((segm_nr, loop_segm_nr))
        if len(insertion_points) == 0:
            raise PathNotMathingToLoopError("No intersection point found for integration of the loop")
        insertion_point = choice(insertion_points)
        ret_val = self.copy()
        # maybe a point of failure
        ret_val.segments = ret_val.segments[:insertion_point[0]] + loop.path[insertion_point[1]:] + loop.path[:insertion_point[1]]  + ret_val.segments[insertion_point[0]:]
        # there is no subtractio of cost, so it would be more efficient to just save the sum
        # however with the sum the correctnes of the loop cannot be tested, what is better?
        ret_val.cut_cost = ret_val.cut_cost[:insertion_point[0]+1] + loop.cost[insertion_point[1]+1:] + loop.cost[:insertion_point[1]+1] + ret_val.cut_cost[insertion_point[0]+1:]
        assert self.is_valid()
        return ret_val

    def cost(self):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = abs(self.duration - (self.keypoints[-1].target - self.keypoints[0].target)) ** 2
        repetition_cost = prod([self.segments.count(x) for x in set(self.segments)]) - 1
        return self.algo.duration_penalty * duration_cost + self.algo.cut_penalty * sum(self.cut_cost) + self.algo.repetition_penalty * repetition_cost

    def copy(self):
        return LoopPath(self.algo, Loop(0, self.cut_cost, self.segments, 0), self.keypoints[-1].target - self.keypoints[0].target)
