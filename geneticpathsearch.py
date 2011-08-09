from collections import namedtuple
from datetime import datetime
from random import choice, seed

import numpy

Keypoint = namedtuple("Keypoint", ["source", "target"])
Cut = namedtuple("Cut", ["start", "end", "cost"])

# TODO caching
# TODO pass parameters externally
# TODO evaluate influence of different mutation and crossover schemes on energy function

class Segment(namedtuple("Segment", ["start", "end"])):
    @property
    def duration(self):
        return self.end - self.start

class Path(object):
    def __init__(self, keypoints, cuts=None):
        """Construct a path from a list of keypoints and a list of cuts."""
        if not len(keypoints) >= 2:
            raise ValueError("keypoints must be a list of at least two keypoints, not %s" % keypoints)
        self.keypoints, self.cuts = keypoints, cuts or []
        if not all(s.duration > 0 for s in self.segments):
            raise ValueError("cuts must be a chronologically ordered list, not %s" % cuts)

    def __lt__(self, other):
        return self.cost() < other.cost()

    def __le__(self, other):
        return self.cost() <= other.cost()

    def __gt__(self, other):
        return self.cost() > other.cost()

    def __ge__(self, other):
        return self.cost() >= other.cost()

    def __eq__(self, other):
        return self.cost() == other.cost() # DEBUG self.cuts == other.cuts and self.keypoints == other.keypoints

    def __ne__(self, other):
        return not (self == other)

    @property
    def segment_starts(self):
        return [self.keypoints[0].source] + [cut.end for cut in self.cuts]

    @property
    def segment_ends(self):
        return [cut.start for cut in self.cuts] + [self.keypoints[-1].source]

    @property
    def segments(self):
        return [Segment(start, end) for start, end in zip(self.segment_starts, self.segment_ends)]

    @property
    def duration(self):
        return sum(s.end - s.start for s in self.segments)

    def synthesize(self, data):
        """Synthesize the suite of segments represented by this path from the given data array."""
        return numpy.concatenate([data[segment_start:segment_end] for segment_start, segment_end in self.segments])

    def remove_random_cut(self, cuts, num_cuts=1):
        """Mutate the path by removing a random cut (or the given number of successive cuts)."""
        possible_cuts = [i for i, (x, y) in enumerate(zip([self.keypoints[0].source] + [cut.end for cut in self.cuts],
            [cut.start for cut in self.cuts[num_cuts:]] + [self.keypoints[-1].source])) if x < y]
        if possible_cuts:
            cut = choice(possible_cuts)
            self.cuts[cut:cut+num_cuts] = []

    def insert_random_cut(self, cuts):
        """Mutate the path by inserting a random cut, assuming ``cuts`` is sorted."""
        self.cuts.insert(*choice([(i, c) for i, s in enumerate(self.segments) for c in cuts if s.start < c.start and c.end < s.end]))

    def mutate(self, cuts, add_probability=0.4, remove_probability=0.4):
        """Randomly mutate the path by inserting or removing cuts, assuming ``cuts`` is sorted."""
        if self.cuts and numpy.random.random() < remove_probability:
            num_cuts = numpy.random.randint(len(self.cuts)) # TODO nicer distribution
            self.remove_random_cut(cuts, num_cuts)
        if numpy.random.random() < add_probability:
            self.insert_random_cut(cuts)

    def crossover(self, other):
        """Randomly mix two paths by jumping from one into the other."""
        try:
            self_idx, other_idx = choice([(i, j) for i, c in enumerate(self.cuts) for j, d in enumerate(other.cuts) if c.end < d.start])
            return Path(self.keypoints, self.cuts[:self_idx+1] + other.cuts[other_idx:])
        except IndexError:
            return Path(self.keypoints, self.cuts[:])

    def breed(self, other, *args, **kwargs):
        """Create a child by crossover and mutation. Arguments are passed to ``self.mutate()``."""
        child = self.crossover(other)
        child.mutate(*args, **kwargs)
        return child

    def cost(self, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = (self.duration - (self.keypoints[-1].target - self.keypoints[0].target)) ** 2 # TODO take all key points into account
        cut_cost = sum(c.cost for c in self.cuts)
        repetition_cost = 0 # TODO implement repetition cost
        return duration_penalty * duration_cost + cut_penalty * cut_cost + repetition_penalty * repetition_cost

def path_search(source_keypoints, target_keypoints, cuts, num_individuals=1000, num_generations=10, num_children=1000, random_seed=None):
    """Find a path that identifies the ``source_keypoints`` with the corresponding ``target_keypoints``.
    ``cuts`` contains jumps (start, end, cost) in the source. The path consists of a list of (start, end) in the source."""
    if random_seed is not None:
        numpy.random.seed(random_seed)
        seed(random_seed)
    population = [Path([Keypoint(s, t) for s, t in zip(source_keypoints, target_keypoints)])] * num_individuals
    cuts = sorted(Cut(s, e, c) for s, e, c in cuts)
    for generation in range(num_generations):
        print
        print "%s: computing generation %d" % (datetime.now().strftime("%c"), generation + 1)

        population.extend(x.breed(y, cuts) for x, y in (numpy.random.permutation(population)[:2] for c in range(num_children)))
        population.sort()
        population = population[:num_individuals]
        
        costs = [p.cost() for p in population]
        durations = [p.duration / (target_keypoints[-1] - target_keypoints[0]) for p in population]
        nums_cuts = [len(p.cuts) for p in population]
        print "min/avg/max cost:", min(costs), sum(costs) / float(len(population)), max(costs)
        print "min/avg/max duration / desired duration:", min(durations), sum(durations) / float(len(population)), max(durations)
        print "min/avg/max number of cuts:", min(nums_cuts), sum(nums_cuts) / float(len(population)), max(nums_cuts)

    return population[0].segments

