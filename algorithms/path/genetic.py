from bisect import bisect
from datetime import datetime
from itertools import product

from numpy.random import random, randint, permutation, seed

from ..algorithm import PiecewisePathAlgorithm, Keypoint, Cut, Path, Segment

def unique(lst):
    """Return a sorted list made of the unique elements of `l`."""
    a = []
    for x in lst:
        index = bisect(a, x)
        if index == 0 or a[index-1] != x:
            a.insert(index, x)
    return a

def choice(l):
    if len(l) == 0:
        raise IndexError("random choice from empty sequence")
    return l[randint(len(l))]

class GeneticPath(Path):
    def __init__(self, algo, keypoints, cuts=()):
        segment_starts = [keypoints[0].source] + [cut.end for cut in cuts]
        segment_ends = [cut.start for cut in cuts] + [keypoints[-1].source]
        segments = [Segment(start, end) for start, end in zip(segment_starts, segment_ends)]
        super(GeneticPath, self).__init__(segments, keypoints)
        self.algo = algo

    def remove_random_cut(self, cuts, num_cuts=1):
        """Mutate the path by removing a random cut (or the given number of successive cuts)."""
        segment_starts = [self.keypoints[0].source] + [cut.end for cut in self.cuts]
        segment_ends = [cut.start for cut in self.cuts[num_cuts:]] + [self.keypoints[-1].source]
        possible_cuts = [i for i, (x, y) in enumerate(zip(segment_starts, segment_ends)) if x < y]
        if possible_cuts:
            cut_idx = choice(possible_cuts)
            self.remove_cuts(cut_idx, cut_idx + num_cuts)

    def insert_random_cut(self, cuts):
        """Mutate the path by inserting a random cut, assuming ``cuts`` is sorted."""
        possible_cuts = [(i, c) for i, s in enumerate(self.segments) for c in cuts if s.start < c.start and c.end < s.end]
        if possible_cuts:
            self.insert_cut(*choice(possible_cuts))

    def mutate(self, cuts):
        """Randomly mutate the path by inserting or removing cuts, assuming ``cuts`` is sorted."""
        if self.cuts and random() < self.algo.remove_probability:
            num_cuts = randint(1, len(self.cuts) + 1) # TODO nicer distribution
            self.remove_random_cut(cuts, num_cuts)
        if random() < self.algo.add_probability:
            self.insert_random_cut(cuts)

    def crossover(self, other):
        """Randomly mix two paths by jumping from one into the other."""
        try:
            self_idx, other_idx = choice([(i, j) for i, c in enumerate(self.cuts) for j, d in enumerate(other.cuts) if c.end < d.start])
            return GeneticPath(self.algo, self.keypoints[:], self.cuts[:self_idx+1] + other.cuts[other_idx:])
        except IndexError:
            return GeneticPath(self.algo, self.keypoints[:], self.cuts[:])

    def breed(self, other, *args, **kwargs):
        """Create a child by crossover and mutation. Arguments are passed to ``self.mutate()``."""
        child = self.crossover(other)
        child.mutate(*args, **kwargs)
        return child

    def repetition_cost(self):
        """Compute a function that grows when parts of the source occur multiple times in the output."""
        return sum(max(min(a.end, b.end) - max(a.start, b.start), 0) for a, b in product(self.segments, self.segments) if a is not b)

    def cost(self):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = abs(self.duration - (self.keypoints[-1].target - self.keypoints[0].target))
        cut_cost = sum(c.cost for c in self.cuts)
        repetition_cost = self.repetition_cost()
        return self.algo.duration_penalty * duration_cost + self.algo.cut_penalty * cut_cost + self.algo.repetition_penalty * repetition_cost

class GeneticPathAlgorithm(PiecewisePathAlgorithm):
    """Genetic algorithm for finding paths."""

    def __init__(self, num_individuals=1000, num_generations=10, num_children=1000, random_seed="random",
            add_probability=0.4, remove_probability=0.4,
            duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1):
        self.num_individuals = int(num_individuals)
        self.num_generations = int(num_generations)
        self.num_children = int(num_children)
        self.random_seed = randint((1<<31) - 1) if random_seed == "random" else int(random_seed)
        self.add_probability = add_probability
        self.remove_probability = remove_probability
        self.duration_penalty = duration_penalty
        self.cut_penalty = cut_penalty
        self.repetition_penalty = repetition_penalty

    def find_path(self, source_start, source_end, target_duration, cuts):
        # TODO sometimes, the algorithm seems to yield different results even when run with the same random seed
        if self.random_seed is not None:
            seed(self.random_seed)

        population = [GeneticPath(self, [Keypoint(source_start, 0), Keypoint(source_end, target_duration)]) for i in range(self.num_individuals)]
        cuts = sorted(Cut(s, e, c) for s, e, c in cuts)

        for generation in range(self.num_generations):
            print
            print "%s: computing generation %d" % (datetime.now().strftime("%c"), generation + 1)

            population.extend(x.breed(y, cuts) for x, y in (permutation(population)[:2] for c in range(self.num_children)))
            population = unique(population)[:self.num_individuals]
            
            costs = [p.cost() for p in population]
            durations = [p.duration / float(target_duration) for p in population]
            nums_cuts = [len(p.cuts) for p in population]
            print "min/avg/max cost:", min(costs), sum(costs) / float(len(population)), max(costs)
            print "min/avg/max duration / desired duration:", min(durations), sum(durations) / float(len(population)), max(durations)
            print "min/avg/max number of cuts:", min(nums_cuts), sum(nums_cuts) / float(len(population)), max(nums_cuts)

        return population[0]

