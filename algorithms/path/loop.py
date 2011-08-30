# before: create automata
#         calc loops, which have no duplicate segments
#           consider the shortest possible loops
#           short loops should be extendible to the original path if needed
#         data structure of a loop: (length, cut-cost, [segments])

# idea: calc automata and a reasonable set of loops
#       calc shortest path from start to end/target
#       while the path doesn't meet the target duration (t > eps):
#            augment the path with a good/long loop (t_l <= t + eps)
#            increase the use counter of this loop
#       return path

# stephan wanted a randomized algorithm, which creates a set of paths and takes the best one
# choosing a loop is a random decision

from collections import namedtuple
from heapq import heappush, heappop
from math import sqrt
from bisect import bisect_right
from numpy.random import random, randint, permutation, seed
from scipy.stats import norm
from numpy import prod, unique, std
from ..algorithm import PiecewisePathAlgorithm, Path, Keypoint, Segment as SimpleSegment
from segment import create_automata

class LoopPathAlgorithm(PiecewisePathAlgorithm):
    def __init__(self, random_seed = "random", num_paths=10, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1, iterations=20, new_paths_per_iteration=10, deviation_divisor=100, max_rounds_without_change=3, first_fit_loop_integration = True):
        self.random_seed = randint(0xffffffff) if random_seed == "random" else int(random_seed)
        self.num_paths = int(num_paths)
        self.duration_penalty = int(duration_penalty)
        self.cut_penalty = int(cut_penalty)
        self.repetition_penalty = int(repetition_penalty)
        self.iterations = int(iterations)
        self.new_paths_per_iteration = int(new_paths_per_iteration)
        self.deviation_divisor = int(deviation_divisor)
        self.max_rounds_without_change = int(max_rounds_without_change)
        self.first_fit_loop_integration = bool(first_fit_loop_integration)

    def find_path(self, source_start, source_end, target_duration, cuts): 
        if self.random_seed is not None:
            seed(self.random_seed)
        automat, start_segment, end_segment = create_automata(cuts, source_start, source_end)
        initial_path = LoopPath(self, dijkstra(start_segment, end_segment), target_duration, self.first_fit_loop_integration)
        loops = uniquify_loops(calc_loops(automat))
        loops_duration = [loop.duration for loop in loops]
        inv_std_deviation = (max(loops_duration) - min(loops_duration)) - std(loops_duration)
        inv_std_deviation *= float(self.new_paths_per_iteration)/self.deviation_divisor
        print "Min Duration %d" % min(loops_duration)
        print "Max Duration %d" % max(loops_duration)
        print "Max Duration - Min Duration %d" % (max(loops_duration) - min(loops_duration))
        print "standard deviation %f" % std(loops_duration)
        print "Inverse Duration deviation %f" % inv_std_deviation
        # initial_path is an instance of LoopPath
        # loops is a list of Loops, sorted by duration
        # choose several loops to augment the paths
        # choose long loops when we have a lot of time to consume
        # choose small loops if we are near the desired duration
        # overshooting and undershooting must be possible
        # determine middle loop and an aviation
        # each path will be augmented by at least one loop
        paths = [initial_path]
        old_paths = []
        old_paths_counter = 0
        for i in range(self.iterations):
            if paths == old_paths:
                old_paths_counter += 1
            else:
                old_paths = paths
                old_paths_counter = 0
            if old_paths_counter == self.max_rounds_without_change:
                break
            print "Iteration %d, cost of best path %d, Number of paths %d" % (i, sorted(paths)[0].cost(), len(paths))
            new_paths = []
            for path in paths:
                 chosen_durations = norm(path.missing_duration(), inv_std_deviation).rvs(size = self.new_paths_per_iteration)
                 chosen_indizes = [max(0, bisect_right(loops_duration, duration)-1) for duration in chosen_durations]
                 for index in unique(chosen_indizes):
                    try:
                        new_path = path.integrate_loop(loops[index])
                        new_paths.append(new_path)
                    except PathNotMathingToLoopError:
                        pass
            paths = uniquify_LoopPaths(paths + new_paths)[:self.num_paths]
        return sorted(paths)[0].convert_to_simple_segment()

def uniquify_loops(loops):
    # numpy.unique doesnt like Loop :(
    sorted_loops = sorted(loops)
    ret_val = [sorted_loops[0]]
    for loop in sorted_loops[1:]:
        if ret_val[-1].duration < loop.duration:
            ret_val.append(loop)
    return ret_val

def uniquify_LoopPaths(paths):
    # numpy.unique doesnt like LoopPath :(
    sorted_paths = sorted(paths)
    ret_val = [sorted_paths[0]]
    for path in sorted_paths[1:]:
        if ret_val[-1].cost() < path.cost():
            ret_val.append(path)
    return ret_val

Loop = namedtuple('Loop', "duration cost path used")

# taken from genetic.py
def choice(l):
    if len(l) == 0:
        raise IndexError("random choice from empty sequence")
    return l[randint(len(l))]

def is_loop_valid(loop):
    ret_val = LoopPath(None, loop, 0).is_valid()
    ret_val &= loop.path[-1][loop.cost[0]] == loop.path[0]
    return ret_val

def are_loops_valid(loops):
    ret_val = True
    for loop in loops:
        ret_val &= is_loop_valid(loop)
    return ret_val

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

def calc_loops(automata):
    loops = calc_short_loops(automata)
    loops += calc_straight_loops(automata)
    return loops

# give a sorted list of loops with their length
# a loop consists of (start, end), length, while start and end are segments or framenumbers
def calc_short_loops(automata):
    # shortest loop can be achieved by stepping to the successor of the node and then finding a path back to the node by using dijkstra
    # more longer loops can be created by looking, when the shorter one jumped to the start. to create a longer loop don't take the jump and dijkstra again
    # take caution that jumps always move towards the end, if a jump moves away from the end break
    # we want loops where every node is taken only once (finite amount of loops and each loop is unique)
    loops = []
    segment = automata[sorted(automata.keys())[0]]
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
            # TODO find more loops, by looking after the jump towards the start, really needed? -> creates more jumps than desired
        segment = segment.following_segment()[1]
    return loops

def calc_straight_loops(automata):
    loops = []
    segment = automata[sorted(automata.keys())[0]]
    while segment.has_followers:
        for cost in segment:
            next_segment = segment[cost]
            if next_segment.start < segment.start:
                cost_list = [cost]
                path = [next_segment]
                duration = next_segment.duration
                while next_segment != segment:
                    next_cost, next_segment = next_segment.following_segment()
                    cost_list.append(next_cost)
                    path.append(next_segment)
                    duration += next_segment.duration
                loops.append(Loop(duration, cost_list, path, 0))
        segment = segment.following_segment()[1]
    return loops

class PathNotMathingToLoopError(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

class LoopPath(Path):
    def __init__(self, algo, loop, target_duration, deterministic):
        self.algo = algo
        self.cut_cost = loop.cost[:]
        self.cut_cost[0] = 0
        self.deterministic = deterministic
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
        insertion_points = []
        for segm_nr in range(len(self.segments)):
            for loop_segm_nr in range(len(loop.path)):
                if self.segments[segm_nr].end == loop.path[loop_segm_nr].start:
                    insertion_points.append((segm_nr, loop_segm_nr))
                    if self.deterministic:
                        break
        if len(insertion_points) == 0:
            raise PathNotMathingToLoopError("No intersection point found for integration of the loop")
        insertion_point = choice(insertion_points)
        ret_val = self.copy()
        # maybe a point of failure
        ret_val.segments = ret_val.segments[:insertion_point[0]+1] + loop.path[insertion_point[1]:] + loop.path[:insertion_point[1]] + ret_val.segments[insertion_point[0]+1:]
        # there is no subtraction of cost, so it would be more efficient to just save the sum
        # however with the sum the correctnes of the loop cannot be tested, what is better?
        for begin_cost in ret_val.segments[insertion_point[0]]:
            if self.segments[insertion_point[0]][begin_cost] == loop.path[insertion_point[1]]:
                break
        for end_cost in loop.path[insertion_point[1]-1]:
            if loop.path[insertion_point[1]-1][end_cost] == self.segments[insertion_point[0]+1]:
                break
        ret_val.cut_cost = ret_val.cut_cost[:insertion_point[0]+1] + [begin_cost] + loop.cost[insertion_point[1]+1:] + loop.cost[:insertion_point[1]] + [end_cost] + ret_val.cut_cost[insertion_point[0]+2:]
        assert self.is_valid()
        return ret_val

    def cost(self):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = self.missing_duration() ** 2
        repetition_cost = (max(0, prod([float(self.segments.count(x)) for x in set(self.segments)]) - 1))
        return int(self.algo.duration_penalty * duration_cost + self.algo.cut_penalty * sum(self.cut_cost) + self.algo.repetition_penalty * repetition_cost)

    def copy(self):
        return LoopPath(self.algo, Loop(0, self.cut_cost, self.segments, 0), self.target_duration(), self.deterministic)

    def target_duration(self):
        return self.keypoints[-1].target - self.keypoints[0].target

    def missing_duration(self):
        return self.target_duration() - self.duration

    def convert_to_simple_segment(self):
        ret_val = self.copy()
        for i in range(len(self.segments)):
            ret_val.segments[i] = SimpleSegment(ret_val.segments[i].start, ret_val.segments[i].end)
        return ret_val
