from scipy.io import wavfile
from collections import namedtuple

from algorithms.path.segment import create_automata
from algorithms.path.loop import calc_loops, are_loops_valid
from algorithms.path.path import LoopPath
from algorithms.cuts.hierarchical import HierarchicalCutsAlgorithm
from synthesize import read_cuts

def get_best(infilename, cutfilename):
    cuts_algo = HierarchicalCutsAlgorithm()
    return read_cuts(infilename, cutfilename, cuts_algo)

def get_automata(infilename, best):
    # read file
    rate, data = wavfile.read(infilename)
    return create_automata(best, 0, len(data))

def get_loops(automata):
    return calc_loops(automata)
    
def print_loops(loops):
    for loop in sorted(loops):
        print loop

def path_from_loop(loops):
    path_algo = None
    return LoopPath(path_algo, loops[-1], 2345678)

cutsfn = '../inflames.cuts'
infn = '../In Flames - Sounds of a Playground Fading (2011)/01 - Sounds Of A Playground Fading.wav'
best = get_best(infilename = infn, cutfilename = cutsfn)
automata = get_automata(infilename = infn, best = best)
loops = get_loops(automata)
path = path_from_loop(loops)
assert are_loops_valid(loops)

