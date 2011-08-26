from scipy.io import wavfile
from segment import create_automata
from loop import calc_loops, are_loops_valid
from path import create_path_from_loop
from collections import namedtuple

# import this from algorithm
Cut = namedtuple("Cut", ["start", "end", "cost"])

# an import from datafile would be nice too
def read_datafile(filename):
    g = {}
    contents = {}
    execfile(filename, g, contents)
    return contents

# it would be nicer to import this from synthesize
def read_cuts(cutsfilename):
    best = None
    if cutsfilename is not None:
        try:
            print "Reading cuts from %s." % cutsfilename
            contents = read_datafile(cutsfilename)
            best = [Cut(int(start), int(end), float(error)) for start, start_time, end, end_time, error in contents["data"]]
        except (OSError, IOError):
            print "Cut file could not be read, recomputing cuts."""
        except (KeyError, SyntaxError):
            print "Cut file could not be parsed, recomputing cuts."""
    else:
        print "No cut file specified, recomputing cuts."""
    return best

def get_best(cutfilename):
    return read_cuts(cutfilename)

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
    return create_path_from_loop(loops[-1], 2345678, 1.2, 2, 1.5)

cutsfn = '../../../inflames.cuts'
infn = '../../../In Flames - Sounds of a Playground Fading (2011)/01 - Sounds Of A Playground Fading.wav'
best = get_best(cutfilename = cutsfn)
automata = get_automata(infilename = infn, best = best)
loops = get_loops(automata)
path = path_from_loop(loops)
assert are_loops_valid(loops)

