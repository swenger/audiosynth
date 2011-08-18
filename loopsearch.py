# before: create automata
#         calc loops, which have no duplicate segments
#           consider the shortest possible loops
#           short loops should be extendible to the original path if needed
#         data structure of a loop: (length, cut-cost, [segments])

# create shortest path from start to end using dijkstra
# augment the path with loops of length, which is smaller than the remaining duration + eps
# count the usage of each loop

from heapq import heappush, heappop

def dijkstra(start, end):
    # start/end are segments
    # convert to a usable graph structur and convert back?
    # or build dijkstra myself?
    # build dijkstra myself
    # returns the shortest path from start to end

    # item if the queue is of the form (length, path)
    # TODO named_tuple
    priority_queue = [(0, [start])]
    final_segments = []
    while priority_queue[0][1][-1] != end:
        item = heappop(priority_queue)
        final_segments.append(item[1][-1])
        new_duration = item[0] + item[1][-1].duration
        for segment in item[1][-1]:
            if not segment in final_segments:
                heappush(priority_queue, (new_duration, item[1] + [segment]))
    return priority_queue[0]
