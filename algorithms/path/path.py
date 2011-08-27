from numpy import unique, prod
from random import choice
from collections import namedtuple
from ..algorithm import Path, Keypoint

Loop = namedtuple('Loop', "duration cost path used")

class PathNotMathingToLoopError(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

# TODO put _cost and _segments into a list of pairs with tuples (segment, cost)
class LoopPath(Path):
    def __init__(self, algo, loop, target_duration):
        self.algo = algo
        self.cut_cost = loop.cost
        self.cut_cost[0] = 0
        keypoints = [Keypoint(loop.path[0], 0), Keypoint(loop.path[-1], target_duration)]
        super(LoopPath, self).__init__(loop.path, keypoints)

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
        assert is_valid()
        return ret_val

    def cost(self):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = abs(self.duration - (self.keypoints[-1].target - self.keypoints[0].target)) ** 2
        repetition_cost = prod([self.segments.count(x) for x in set(self.segments)]) - 1
        return self.algo.duration_penalty * duration_cost + self.algo.cut_penalty * sum(self.cut_cost) + self.algo.repetition_penalty * repetition_cost

    def copy(self):
        return LoopPath(self.algo, Loop(0, self.cut_cost, self.segments, 0), self.keypoints[-1].target - self.keypoints[0].target)
