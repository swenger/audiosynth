from datetime import datetime

from numpy.random import random, randint, permutation, seed

def choice(l):
    if len(l) == 0:
        raise IndexError("random choice from empty sequence")
    return l[randint(len(l))]

from ..algorithm import PiecewisePathAlgorithm, Keypoint, Cut, Path, Segment

class GeneticPath(Path):
    def __init__(self, keypoints, cuts=()):
        segment_starts = [keypoints[0].source] + [cut.end for cut in cuts]
        segment_ends = [cut.start for cut in cuts] + [keypoints[-1].source]
        segments = [Segment(start, end) for start, end in zip(segment_starts, segment_ends)]
        super(GeneticPath, self).__init__(segments, keypoints)

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
        self.insert_cut(*choice([(i, c) for i, s in enumerate(self.segments) for c in cuts if s.start < c.start and c.end < s.end]))

    def mutate(self, cuts, add_probability=0.4, remove_probability=0.4):
        """Randomly mutate the path by inserting or removing cuts, assuming ``cuts`` is sorted."""
        if self.cuts and random() < remove_probability:
            num_cuts = randint(1, len(self.cuts) + 1) # TODO nicer distribution
            self.remove_random_cut(cuts, num_cuts)
        if random() < add_probability:
            self.insert_random_cut(cuts)

    def crossover(self, other):
        """Randomly mix two paths by jumping from one into the other."""
        try:
            self_idx, other_idx = choice([(i, j) for i, c in enumerate(self.cuts) for j, d in enumerate(other.cuts) if c.end < d.start])
            return GeneticPath(self.keypoints, self.cuts[:self_idx+1] + other.cuts[other_idx:])
        except IndexError:
            return GeneticPath(self.keypoints, self.cuts[:])

    def breed(self, other, *args, **kwargs):
        """Create a child by crossover and mutation. Arguments are passed to ``self.mutate()``."""
        child = self.crossover(other)
        child.mutate(*args, **kwargs)
        return child

    def cost(self, duration_penalty=1e2, cut_penalty=1e1, repetition_penalty=1e1):
        """Compute the cost of the path based on a quality metric."""
        duration_cost = abs(self.duration - (self.keypoints[-1][1] - self.keypoints[0][1]))
        cut_cost = sum(c.cost for c in self.cuts)
        repetition_cost = 0 # TODO implement repetition cost
        return duration_penalty * duration_cost + cut_penalty * cut_cost + repetition_penalty * repetition_cost

class GeneticPathAlgorithm(PiecewisePathAlgorithm):
    """Genetic algorithm for finding paths."""

    def __init__(self, num_individuals=1000, num_generations=10, num_children=1000, random_seed=None):
        self.num_individuals = int(num_individuals)
        self.num_generations = int(num_generations)
        self.num_children = int(num_children)
        self.random_seed = int(random_seed) if random_seed is not None else randint(1 << 32)

    def find_path(self, source_start, source_end, target_duration, cuts):
        if self.random_seed is not None:
            seed(self.random_seed)
            # TODO sometimes, running the algorithm with the same input yields different outputs; why? race conditions? unordered sequences?
            print choice(range(100)), random(), randint(100), permutation(range(100))[0] # DEBUG

        population = [GeneticPath([Keypoint(source_start, 0), Keypoint(source_end, target_duration)])] * self.num_individuals
        cuts = sorted(Cut(s, e, c) for s, e, c in cuts)

        for generation in range(self.num_generations):
            print
            print "%s: computing generation %d" % (datetime.now().strftime("%c"), generation + 1)

            population.extend(x.breed(y, cuts) for x, y in (permutation(population)[:2] for c in range(self.num_children)))
            population = sorted(set(population)) # sort and remove duplicates; otherwise, do population.sort()
            population = population[:self.num_individuals]
            
            costs = [p.cost() for p in population]
            durations = [p.duration / float(target_duration) for p in population]
            nums_cuts = [len(p.cuts) for p in population]
            print "min/avg/max cost:", min(costs), sum(costs) / float(len(population)), max(costs)
            print "min/avg/max duration / desired duration:", min(durations), sum(durations) / float(len(population)), max(durations)
            print "min/avg/max number of cuts:", min(nums_cuts), sum(nums_cuts) / float(len(population)), max(nums_cuts)

        print choice(range(100)), random(), randint(100), permutation(range(100))[0] # DEBUG
        return population[0]

