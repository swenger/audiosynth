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
from segment import create_automaton

class LoopPathAlgorithm(PiecewisePathAlgorithm):
    def __init__(self, random_seed = "random", num_paths=10, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1, iterations=20, new_paths_per_iteration=10, deviation_divisor=10, max_rounds_without_change=3, first_fit_loop_integration = "True"):
        self.random_seed = randint((1 << 31) - 1) if random_seed == "random" else int(random_seed)
        self.num_paths = int(num_paths)
        self.duration_penalty = int(duration_penalty)
        self.cut_penalty = int(cut_penalty)
        self.repetition_penalty = int(repetition_penalty)
        self.iterations = int(iterations)
        self.new_paths_per_iteration = int(new_paths_per_iteration)
        self.deviation_divisor = int(deviation_divisor)
        self.max_rounds_without_change = int(max_rounds_without_change)
        # some possible string representations for booleans, extend at leisure
        booleans = {"True": True, "False": False, "true": True, "false": False}
        # recognize boolean string argument or raise KeyError
        self.first_fit_loop_integration = booleans[first_fit_loop_integration]

    def find_path(self, source_start, source_end, target_duration, cuts): 
        if self.random_seed is not None:
            seed(self.random_seed)
        automat, start_segment, end_segment = create_automaton(cuts, source_start, source_end)
        initial_path = LoopPath(self, dijkstra(start_segment, end_segment), target_duration, self.first_fit_loop_integration)
        loops = sorted(set(calc_loops(automat)))
        # initial_path is an instance of LoopPath
        # loops is a list of Loops, sorted by duration
        # choose several loops to augment the paths
        # choose long loops when we have a lot of time to consume
        # choose small loops if we are near the desired duration
        # overshooting and undershooting must be possible
        # determine middle loop and an deviation
        # each path will be augmented by at least one loop
        # TODO shortening of paths
        # TODO new probability distribution function, which rapidly falls behind the desired duration (linearer anstiegt, plus abfall mit hyperbel)
        paths = [initial_path]
        old_paths = []
        old_paths_counter = 0
        for i in range(self.iterations):
            # if nothing happens anymore, early break
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
                 std_deviation = path.missing_duration() / self.deviation_divisor
                 chosen_loops = pick_loops(loops, path.missing_duration(), std_deviation, self.new_paths_per_iteration)
                 for loop in chosen_loops:
                     try:
                         new_path = path.integrate_loop(loop)
                         new_paths.append(new_path)
                     except PathNotMatchingToLoopError:
                         pass
            paths = uniquify_LoopPaths(paths + new_paths)[:self.num_paths]
        return sorted(paths)[0].convert_to_simple_segment()

def weight_loops(loops, mean, std_deviation):
    rv = norm(mean, std_deviation)
    return [rv.pdf(loop.duration) for loop in loops]

def pick_loop_index(loops_probability):
    rand_number = random() * sum(loops_probability)
#    print "random number is %f" % rand_number
    sum_of_probabilities = 0.0
    for i in range(len(loops_probability)):
       sum_of_probabilities += loops_probability[i]
       if sum_of_probabilities >= rand_number:
           break
#    print "sum of probs %f" % sum_of_probabilities
#    print "chosen loop index is %d" % i
    return i

def pick_loops(loops, mean, std_deviation, new_paths_per_iteration):
    loops_probability = weight_loops(loops, mean, std_deviation)
#    print "loops prob " + str(loops_probability)
    indizes = [pick_loop_index(loops_probability) for i in range(new_paths_per_iteration)]
#    print "Indizes of new loops are: " + str(indizes)
    return [loops[i] for i in unique(indizes)]

def uniquify_LoopPaths(paths):
    # in order to use set() and sorted() LoopPath needs to be immutable
    # this could be done, but the parent Path is mutable, too
    sorted_paths = sorted(paths)
    ret_val = [sorted_paths[0]]
    for path in sorted_paths[1:]:
        if ret_val[-1].cost() < path.cost():
            ret_val.append(path)
    return ret_val

Loop = namedtuple('Loop', "duration cost path used")

def loop_to_loop_with_tuples(loop):
    return Loop(loop.duration, tuple(loop.cost), tuple(loop.path), loop.used)

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
                loops.append(loop_to_loop_with_tuples(possible_loop))
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
                loops.append(Loop(duration, tuple(cost_list), tuple(path), 0))
        segment = segment.following_segment()[1]
    return loops

class PathNotMatchingToLoopError(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

class LoopPath(Path):
    def __init__(self, algo, loop, target_duration, deterministic):
        self.algo = algo
        self.cut_cost = list(loop.cost)
        self.cut_cost[0] = 0
        self.deterministic = deterministic
        keypoints = [Keypoint(loop.path[0], 0), Keypoint(loop.path[-1], target_duration)]
        super(LoopPath, self).__init__(loop.path[:], keypoints)

    def is_valid(self):
        ret_val = len(self.segments) == len(self.cut_cost)
        for i in range(len(self.segments))[:-1]:
            ret_val &= self.segments[i][self.cut_cost[i+1]] == self.segments[i+1]
        return ret_val

    def remove_some_segments(self, time):
        # search for a sequence of segments with duration of time and remove them, resulting in a new path
        # prefer removable sequences with a bigger duration than time
        # prefer removing sequences with lots of jumps / high cost => need a decision who lowers the cost best
        Removable_Piece = namedtuple("Removable_Piece", "duration cost start_index end_index")
        rp = Removable_Piece(-1, 0, 0)
        for i in range(len(self.segments)):
            duration = 0
            cost = 0
            for j in range(len(self.segments))[i+1:]:
                for cost in self.segments[i]:
                    # TODO continue 
                    pass
                if self.segments[i].end:
                    pass 
                # duration and cost is what we get if we remove the segments between i and j
        pass

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
            raise PathNotMatchingToLoopError("No intersection point found for integration of the loop")
        insertion_point = choice(insertion_points)
        ret_val = self.copy()
        # maybe a point of failure
        ret_val.segments = ret_val.segments[:insertion_point[0]+1] + list(loop.path[insertion_point[1]:]) + list(loop.path[:insertion_point[1]]) + ret_val.segments[insertion_point[0]+1:]
        # there is no subtraction of cost, so it would be more efficient to just save the sum
        # however with the sum the correctnes of the loop cannot be tested, what is better?
        for begin_cost in ret_val.segments[insertion_point[0]]:
            if self.segments[insertion_point[0]][begin_cost] == loop.path[insertion_point[1]]:
                break
        for end_cost in loop.path[insertion_point[1]-1]:
            if loop.path[insertion_point[1]-1][end_cost] == self.segments[insertion_point[0]+1]:
                break
        ret_val.cut_cost = ret_val.cut_cost[:insertion_point[0]+1] + [begin_cost] + list(loop.cost[insertion_point[1]+1:]) + list(loop.cost[:insertion_point[1]]) + [end_cost] + ret_val.cut_cost[insertion_point[0]+2:]
        assert self.is_valid()
        return ret_val

    def cost(self):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = self.missing_duration() ** 2
        # TODO remove sqrt
        from math import sqrt
        repetition_cost = sqrt(max(0, prod([float(self.segments.count(x)) for x in set(self.segments)]) - 1))
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
