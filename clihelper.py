from synthesize import read_cuts
from scipy.io import wavfile
from utilities import create_automata
from loopsearch import calc_loops, are_loops_valid
from path import create_path_from_loop

def get_best(cutfilename, infilename, cut_parameter_names = ["num_levels", "num_cuts", "num_keep", "block_length_shrink", "weight_factor"], block_length_shrink = 16, num_levels = 5, num_cuts = 256, weight_factor = 1.2, num_keep = 40):
    return read_cuts(cutfilename, infilename, cut_parameter_names, block_length_shrink, num_levels, num_cuts, weight_factor, num_keep)

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

cutsfn = '../inflames.cuts'
infn = '../In Flames - Sounds of a Playground Fading (2011)/01 - Sounds Of A Playground Fading.wav'
best = get_best(infilename = infn, cutfilename = cutsfn)
automata = get_automata(infilename = infn, best = best)
loops = get_loops(automata)
path = path_from_loop(loops)
assert are_loops_valid(loops)

