from collections import namedtuple

Keypoint = namedtuple("Keypoint", ["source", "target"])

Cut = namedtuple("Cut", ["start", "end", "cost"])

class Segment(namedtuple("Segment", ["start", "end"])):
    @property
    def duration(self):
        return self.end - self.start

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
    pass

class PathAlgorithm(Algorithm):
    pass

class PiecewisePathAlgorithm(PathAlgorithm):
    """Meta-algorithm for finding paths through keypoints based on an algorithm to find paths of a given length."""

    def find_path(self, source_start, source_end, target_duration, cuts):
        raise NotImplemented()

    def __call__(self, source_keypoints, target_keypoints, cuts):
        segments = []
        for source_start, source_end, target_end in zip(source_keypoints, source_keypoints[1:], target_keypoints[1:]):
            segments.extend(self.find_path(source_start, source_end, target_end - sum(s.duration for s in segments), cuts))

