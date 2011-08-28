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
from bisect import bisect_right
from numpy.random import random, randint, permutation, seed
from numpy import unique
from ..algorithm import PiecewisePathAlgorithm
from path import Loop, LoopPath, calc_loops, dijkstra, choice, PathNotMathingToLoopError
from segment import create_automata

class LoopPathSearch(PiecewisePathAlgorithm):
    def __init__(self, random_seed = "random", num_paths=10, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1, iterations=100, new_paths_per_iteration=10):
        self.random_seed = randint((1 << 31) - 1) if random_seed == "random" else int(random_seed)
        self.num_paths = int(num_paths)
        self.duration_penalty = int(duration_penalty)
        self.cut_penalty = int(cut_penalty)
        self.repetition_penalty = int(repetition_penalty)
        self.iterations = int(iterations)
        self.new_paths_per_iteration = int(new_paths_per_iteration)

    def find_path(self, source_start, source_end, target_duration, cuts): 
        if self.random_seed is not None:
            seed(self.random_seed)
        automat = create_automata(cuts, source_start, source_end)
        sorted_keys = sorted(automat.keys())
        end_frame_index = sorted_keys[bisect_right(sorted_keys, source_end)-1]
        start_segment = automat[source_start]
        end_segment = automat[end_frame_index]
        initial_path = LoopPath(self, dijkstra(start_segment, end_segment), target_duration)
        loops = uniquify(calc_loops(automat))
        # initial_path is an instance of LoopPath
        # loops is a list of Loops, sorted by duration
        # choose several loops to augment the paths
        # choose long loops when we have a lot of time to consume
        # choose small loops if we are near the desired duration
        # overshooting and undershooting must be possible
        # determine middle loop and an aviation
        # each path will be augmented by at least one loop
        # if a path reaches target_duration put it into complete paths
        paths = [initial_path]
        for i in range(self.iterations):
            print "Iteration %d, cost of best path %f, Number of paths %d" % (i, sorted(paths)[0].cost(), len(paths))
            new_paths = []
            for path in paths:
                 for j in range(self.new_paths_per_iteration):
                    try:
                        new_path = path.integrate_loop(choice(loops))
                        new_paths.append(new_path)
                    except PathNotMathingToLoopError:
                        pass
            paths = uniquify(paths + new_paths)[:self.num_paths]
        return sorted(paths)[0].convert_to_simple_segment()

def uniquify(paths):
    # numpy.unique doesnt like LoopPath :(
    sorted_paths = sorted(paths)
    ret_val = [sorted_paths[0]] 
    for path in sorted_paths:
        if ret_val[-1] != path:
            ret_val.append(path)
    return ret_val
