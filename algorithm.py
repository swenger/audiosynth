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

