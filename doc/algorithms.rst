Algorithms
==========

The program can easily be extended by adding new algorithms.
Derive algorithms from a suitable base class and place them in the correct package directory (see below), and that's it!

.. automodule:: algorithms

General
-------

The `algorithms` module defines base classes for algorithms, as well as some helper classes.

.. automodule:: algorithms.algorithm
   :members:
   :undoc-members:
   :show-inheritance:

Cuts algorithms
---------------

Algorithms for finding cuts live inside the `algorithms.cuts` package.
To add your own algorithms, derive them from `algorithms.algorithm.CutsAlgorithm` and put them into this package.

.. automodule:: algorithms.cuts
   :members:
   :undoc-members:
   :show-inheritance:

Path algorithms
---------------

Algorithms for finding paths live inside the `algorithms.path` package.
To add your own algorithms, derive them from `algorithms.algorithm.PathAlgorithm` and put them into this package.

.. automodule:: algorithms.path
   :members:
   :undoc-members:
   :show-inheritance:

