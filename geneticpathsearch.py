from collections import namedtuple
from bisect import bisect_left
from copy import deepcopy
from heapq import heapreplace
from random import choice

import numpy

Keypoint = namedtuple("Keypoint", ["source", "target"])
Cut = namedtuple("Cut", ["start", "end", "cost"])
Segment = namedtuple("Segment", ["start", "end"])

class Path(object):
    def __init__(self, keypoints, cuts=None):
        """Construct a path from a list of keypoints and a list of cuts."""
        if not len(self.keypoints) >= 2:
            raise ValueError("keypoints must be a list of at least two keypoints, not %s" % keypoints)
        self._keypoints = map(Keypoint, keypoints)
        self._cuts = map(Cut, cuts or [])

    def copy(self):
        """Create a deep copy of the path."""
        return deepcopy(self)

    def __lt__(self, other):
        return self.cost() < other.cost()

    def __le__(self, other):
        return self.cost() <= other.cost()

    def __gt__(self, other):
        return self.cost() > other.cost()

    def __ge__(self, other):
        return self.cost() >= other.cost()

    def __eq__(self, other):
        return self._cuts == other._cuts and self._keypoints == other._keypoints

    @property
    def keypoints(self):
        return self._keypoints

    @property
    def cuts(self):
        return self._cuts

    @property
    def segment_starts(self):
        return [self.keypoints[0].source] + [cut.end for cut in self.cuts]

    @property
    def segment_ends(self):
        return [cut.start for cut in self.cuts] + [self.keypoints[-1].source]

    @property
    def segments(self):
        return [Segment(start, end) for start, end in zip(self.segment_starts, self.segment_ends)]

    def synthesize(self, data):
        """Synthesize the suite of segments represented by this path from the given data array."""
        return numpy.concatenate([data[segment_start:segment_end] for segment_start, segment_end in self.segments])

    def find_possible_cuts(self, cuts):
        """Find all possible cuts as (segment_index, cut) tuples, assuming ``cuts`` is sorted."""
        def cuts_in_segment(cuts, segment):
            """Return all cuts that satisfy segment.start <= cut.start < segment.end), assuming ``cuts`` is sorted."""
            return cuts[bisect_left([c.start for c in cuts], segment.start):bisect_left([c.start for c in cuts], segment.end)]
        return [(idx, cut) for idx, segment in enumerate(self.segments) for cut in cuts_in_segment(cuts, segment)]

    def remove_random_cut(self, cuts):
        """Mutate the path by removing a random cut."""
        self.cuts.pop(numpy.random.randint(len(self.cuts)))

    def insert_random_cut(self, cuts):
        """Mutate the path by inserting a random cut, assuming ``cuts`` is sorted."""
        self.cuts.insert(*self.find_possible_cuts(cuts)[numpy.random.randint(len(self.cuts))])

    def mutate(self, cuts, remove_probability=0.0):
        """Randomly mutate the path by inserting or removing cuts, assuming ``cuts`` is sorted."""
        if self.cuts and numpy.random.random() < remove_probability:
            self.remove_random_cut(cuts)
        else:
            self.insert_random_cut(cuts)

    def find_overlaps(self, other):
        """Find all indices of overlapping segments of two paths."""
        return [(i, j) for i, s in enumerate(self.segments) for j, t in enumerate(other.segments) if s.start < t.end and t.start < s.end]

    def crossover(self, other):
        """Randomly mix two paths by jumping from one into the other."""
        child = self.copy()
        self_idx, other_idx = choice(self.find_overlaps(other))
        child._cuts[self_idx:] = other._cuts[other_idx:]
        return child

    def cost(self, cut_penalty=1e1, repetition_penalty=1e3):
        """Compute the cost of the path based on a quality metric."""
        pass # TODO

def path_search(source_keypoints, target_keypoints, cuts, num_individuals, num_generations, num_children):
    population = [Path(zip(source_keypoints, target_keypoints))] * num_individuals
    for generation in range(num_generations):
        for child in [mother.crossover(father) for mother, father in (numpy.random.permutation(population)[:2] for c in range(num_children))]:
            heapreplace(population, child)
    return population[0]

