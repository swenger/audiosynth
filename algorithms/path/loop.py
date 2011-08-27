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
from random import choice, random
from bisect import bisect_right
from ..algorithm import PiecewisePathAlgorithm
from path import Loop, LoopPath, calc_loops, dijkstra
from segment import calc_automata

class LoopPathSearch(PiecewisePathAlgorithm):
    def __init__(self, random_seed = "random", num_paths=10, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1, new_paths_per_iteration=8):
        self.random_seed = randint((1 << 31) - 1) if random_seed == "random" else int(random_seed)
        self.num_paths = num_paths
        self.duration_penalty = duration_penalty
        self.cut_penalty = cut_penalty
        self.repetition_penalty = repetition_penalty
        self.new_paths_per_iteration = new_paths_per_iteration

    def find_path(self, source_start, source_end, target_duration, cuts): 
        automat = calc_automata(cuts, source_start, source_end)
        sorted_keys = sorted(automat.keys())
        end_frame_index = sorted_keys[bisect_right(sorted_keys, source_end)-1]
        start_segment = automat[source_start]
        end_segment = automat[end_frame_index]
        initial_path = LoopPath(self, dijkstra(start_segment, end_segment), target_duration)
        loops = calc_loops(automat)
        # initial_path is an instance of Path
        # loops is a list of Loops, sorted by duration
        # target_duration specifies the duration including the complete start segment and end segment
        loop_durations = [loop.duration for loop in loops]
        median_duration = sorted(loop_durations)[len(loop_durations)/2]
        target_duration = initial_path._target_duration
        paths = [initial_path]
        complete_paths = [initial_path]
        # choose several loops to augment the paths
        # each path will be augmented by at least one loop
        # if a path reaches target_duration put it into complete paths
        while len(complete_paths) < num_paths+1:
            print "\rNumber of complete pahts %d, Number of paths in queue %d" % (len(complete_paths), len(paths)),
            path_nr = int(random() * len(paths))
            path = paths[path_nr]
            del paths[path_nr]
            for i in range(self.new_paths_per_iteration):
                try:
                    new_path = path.integrate_loop(choice(loops))
                    # decide if this path is finished or not
                    # TODO maybe a better decision if a path is complete is needed
                    if abs(new_path.duration - target_duration) < median_duration * random():
                        complete_paths.append(new_path)
                    if new_path.duration < target_duration + median_duration:
                        paths.append(new_path)
                except PathNotMathingToLoopError:
                    pass
        return sorted(complete_paths)[0]
