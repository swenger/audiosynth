import os
import pkgutil

for module_loader, name, ispkg in pkgutil.iter_modules([os.path.dirname(__file__)]):
    print name # TODO import all CutsAlgorithm subclasses into module namespace

