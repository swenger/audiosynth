import os
import pkgutil

from ..algorithm import PathAlgorithm

__all__ = []

# import all PathAlgorithm subclasses into module namespace
for module_loader, name, ispkg in pkgutil.iter_modules([os.path.dirname(__file__)]):
    m = __import__(name, globals(), locals())
    del globals()[name]
    for key, value in m.__dict__.items():
        try:
            if issubclass(value, PathAlgorithm) and value.__module__ == m.__name__:
                globals()[key] = value
                __all__.append(key)
        except TypeError:
            pass
    del module_loader, name, ispkg, m, key, value

del os, pkgutil, PathAlgorithm

