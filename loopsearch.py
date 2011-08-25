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

from heapq import heappush, heappop
from collections import namedtuple
from random import choice, random

Loop = namedtuple('Loop', "duration cost path used")

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
        return Loop(-1, 0, [], 0)

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
            # TODO find more loops, by looking after the jump towards the start
        segment = segment.following_segment
    return sorted(loops)

def getPath(best, source_keypoints, target_keypoints, data_len, rate, cost_factor, duration_factor, repetition_factor, num_paths):


def loop_search(initial_path, loops, num_paths, num_new_paths = 8): #, target_duration, cost_factor, duration_factor, repetition_factor): # all saved in initial_path
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
        path_nr = int(random() * len(paths))
        path = paths[path_nr]
        del paths[path_nr]
        for i in range(num_new_paths):
            try:
                new_path = path.integrate_loop(choice(loops))
                if abs(new_path.duration - target_duration) < median_duration * random():
                    complete_paths.append(new_path)
                else:
                    paths.append(new_path)
            except PathNotMathingToLoopError:
                pass
    return sorted(complete_paths)[0]
