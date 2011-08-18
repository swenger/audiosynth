from collections import namedtuple

import numpy

class Algorithm(object):
    """Base class for algorithms that know about their parameters."""

    def get_parameter_names(self):
        """Return the names of the algorithm's parameters."""
        return self.__init__.func_code.co_varnames[1:self.__init__.func_code.co_argcount]

    def get_parameter_defaults(self):
        """Return a dictionary of parameters and their default values."""
        return dict(zip(reversed(self.get_parameter_names()), reversed(self.__init__.func_defaults)))

    def get_parameters(self):
        """Return a dictionary of parameters."""
        return dict((key, getattr(self, key)) for key in self.get_parameter_names())

    def changed_parameters(self, header):
        """Return names of all parameters that have changed with respect to the supplied dictionary."""
        return [name for name in self.get_parameter_names() if name not in header or header[name] != getattr(self, name)]

class CutsAlgorithm(Algorithm):
    """Base class for algorithms that find a set of good cuts in an audio file."""

    def __call__(self, data):
        """Find a set of good ``Cut``s in ``data``."""
        raise NotImplemented()

class PathAlgorithm(Algorithm):
    """Base class for path search algorithms."""

    def __call__(self, source_keypoints, target_keypoints, cuts):
        """Find a ``Path`` through the given ``source_keypoints`` that approximates the given ``target_keypoints``."""
        raise NotImplemented()

class PiecewisePathAlgorithm(PathAlgorithm):
    """Base class for path search algorithms that only look at two keypoints at a time."""

    def __call__(self, source_keypoints, target_keypoints, cuts):
        """Find a path by successively calling ``find_path()``."""
        path = Path()
        for source_start, source_end, target_end in zip(source_keypoints, source_keypoints[1:], target_keypoints[1:]):
            path += self.find_path(source_start, source_end, target_end - path.duration, cuts)
        return path

    def find_path(self, source_start, source_end, target_duration, cuts):
        """Find a ``Path`` from ``source_start`` to ``source_end`` with a duration of approximately ``target_duration``."""
        raise NotImplemented()

Keypoint = namedtuple("Keypoint", ["source", "target"])

Cut = namedtuple("Cut", ["start", "end", "cost"])

class Segment(namedtuple("Segment", ["start", "end"])):
    @property
    def duration(self):
        return self.end - self.start

class Path(object):
    def __init__(self, segments=None, keypoints=None):
        self.segments, self.keypoints = segments or [], keypoints or []

    
    def __lt__(self, other):
        return self.cost() < other.cost()

    def __le__(self, other):
        return self.cost() <= other.cost()

    def __gt__(self, other):
        return self.cost() > other.cost()

    def __ge__(self, other):
        return self.cost() >= other.cost()

    def __eq__(self, other):
        return self.cuts == other.cuts and self.keypoints == other.keypoints

    def __ne__(self, other):
        return not (self == other)


    def __add__(self, other):
        new_keypoints = other.keypoints if other.keypoints[:1] != self.keypoints[-1:] else other.keypoints[1:]
        return Path(self.segments + other.segments, self.keypoints + new_keypoints)

    def __iadd__(self, other):
        self.keypoints += other.keypoints if other.keypoints[:1] != self.keypoints[-1:] else other.keypoints[1:]
        self.segments += other.segments
        return self

    
    @property
    def duration(self):
        return sum(segment.duration for segment in self.segments)

    @property
    def segment_source_starts(self):
        return [s.start for s in self.segments]

    @property
    def segment_source_ends(self):
        return [s.end for s in self.segments]

    @property
    def segment_target_starts(self):
        return [0] + self.segment_target_ends[:-1].tolist()

    @property
    def segment_target_ends(self):
        return numpy.cumsum(segment.duration for segment in self.segments)


    @property
    def cuts(self):
        return [Cut(a.end, b.start, -1) for a, b in zip(self.segments, self.segments[1:]) if a.end != b.start - 1]

    def remove_cuts(self, start, end):
        """Simulate ``self.cuts[start:end] = []``."""
        cut_idx = 0
        for segment_idx, (a, b) in enumerate(zip(self.segments, self.segments[1:])):
            if a.end != b.start - 1: # this is a cut
                if cut_idx == start:
                    start_segment_idx = segment_idx
                if cut_idx == end:
                    end_segment_idx = segment_idx
                    break
                cut_idx += 1
        else: # end_segment_idx was not found
            end_segment_idx = len(self.segments) - 1
        if not self.segments[start_segment_idx].start < self.segments[end_segment_idx].end:
            raise ValueError("removing these cuts would cause segments of negative length")
        self.segments[start_segment_idx:end_segment_idx+1] = [Segment(self.segments[start_segment_idx].start, self.segments[end_segment_idx].end)]

    def insert_cut(self, position, cut):
        """Simulate ``self.cuts.insert(position, cut)``."""
        cut_idx = 0
        first_subsegment_idx = 0
        for segment_idx, (a, b) in enumerate(zip(self.segments, self.segments[1:])):
            if a.end != b.start - 1: # this is a cut
                if cut_idx == position:
                    last_subsegment_idx = segment_idx
                    break
                else:
                    cut_idx += 1
                    first_subsegment_idx = segment_idx + 1
        else:
            last_subsegment_idx = len(self.segments) - 1

        # find segment_idx where cut starts
        for segment_idx, segment in enumerate(self.segments[first_subsegment_idx:last_subsegment_idx+1], first_subsegment_idx):
            if segment.start <= cut.start < segment.end:
                break
        first_subsegment_idx = segment_idx
        
        # find segment_idx where cut ends
        for segment_idx, segment in enumerate(self.segments[first_subsegment_idx:last_subsegment_idx+1], first_subsegment_idx):
            if segment.start <= cut.end < segment.end:
                break
        
        first_subsegment = self.segments[first_subsegment_idx]
        last_subsegment = self.segments[last_subsegment_idx]
        if not cut.end < last_subsegment.end:
            raise ValueError("inserting this cut would cause segments of negative length")
        if first_subsegment.start != cut.start:
            segments = [Segment(first_subsegment.start, cut.start), Segment(cut.end, last_subsegment.end)]
        else:
            segments = [Segment(cut.end, last_subsegment.end)]
        self.segments[first_subsegment_idx:last_subsegment_idx+1] = segments


    def synthesize(self, data):
        """Synthesize the suite of segments represented by this path from the given data array."""
        return numpy.concatenate([data[segment_start:segment_end] for segment_start, segment_end in self.segments])

    def cost(self):
        raise NotImplemented()

