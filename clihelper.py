from synthesize import read_cuts
from scipy.io import wavfile
from utilities import create_automata

def get_best(cutfilename = '../inflames.cuts', infilename = '../In Flames - Sounds of a Playground Fading (2011)/01 - Sounds Of A Playground Fading.wav', cut_parameter_names = ["num_levels", "num_cuts", "num_keep", "block_length_shrink", "weight_factor"], block_length_shrink = 16, num_levels = 5, num_cuts = 256, weight_factor = 1.2, num_keep = 40):
    return read_cuts(cutfilename, infilename, cut_parameter_names, block_length_shrink, num_levels, num_cuts, weight_factor, num_keep)

def get_automata(infilename = '../In Flames - Sounds of a Playground Fading (2011)/01 - Sounds Of A Playground Fading.wav', best = get_best(infilename = '../In Flames - Sounds of a Playground Fading (2011)/01 - Sounds Of A Playground Fading.wav')):
    # read file
    rate, data = wavfile.read(infilename)
    return create_automata(best, 0, len(data))
