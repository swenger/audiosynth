#!/usr/bin/env python

import sys

from numpy import mgrid, hstack
from scipy.io import wavfile
from pylab import imsave

blocksize = 4096
resolution = 256
infilename = sys.argv[1] # wav file
outfilename = sys.argv[2] # png file

rate, data = wavfile.read(infilename)
data = data.mean(axis=-1)
blocks = data[:blocksize*(len(data)//blocksize)].reshape(-1, blocksize)
extremum = max(blocks.max(), -blocks.min())

scale = extremum * mgrid[0:1:resolution/2*1.0j] ** 3

img_pos = (blocks[:, :, None] >= scale[None, None, :]).sum(axis=1)
img_neg = (blocks[:, :, None] <= -scale[None, None, ::-1]).sum(axis=1)
img = hstack((img_neg, img_pos))

imsave(outfilename, -img.T, cmap="gray", vmin=-0.7*img.max(), vmax=0)

