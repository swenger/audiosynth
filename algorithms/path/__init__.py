import os

from ..algorithm import PathAlgorithm

def find_algorithms(path, klass):
    """Find all classes deriving from ``klass`` that are declared within ``path``."""
    import pkgutil
    d = {}
    for module_loader, name, ispkg in pkgutil.iter_modules(path):
        if name in globals():
            tmp = globals()[name]
            m = __import__(name, globals(), locals())
            globals()[name] = tmp
        else:
            m = __import__(name, globals(), locals())

        for key, value in m.__dict__.items():
            try:
                if issubclass(value, klass) and value.__module__ == m.__name__:
                    d[key] = value
            except TypeError:
                pass
    return d

# import all PathAlgorithm subclasses into module namespace
algorithms = find_algorithms([os.path.dirname(__file__)], PathAlgorithm)
globals().update(algorithms)
__all__ = algorithms.keys()

del os, find_algorithms, PathAlgorithm

