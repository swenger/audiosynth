import sys
from time import clock

def findmatch(data, length, taper):
    """For a given shift length, find the offset where both signals match best within a window of given size"""
    errors = (data[length:].ravel() - data[:-length].ravel()) ** 2 # TODO normalize by overall loudness in window

    #window_errors = convolve(taper, errors, 'valid') TODO use convolution with taper instead of simple integral
    integrated_errors = cumsum(errors, axis=0)
    window_errors = integrated_errors[len(taper):] - integrated_errors[:-len(taper)]
    
    offset = argmin(window_errors)
    return offset, window_errors[offset] # starting position of loop, error of loop

def find_global_match(data, minlength, maxlength, lengthstep, taper, minoffset, maxoffset):
    minerror = inf
    bestoffset = -1
    bestlength = -1

    data = data[minoffset:maxoffset]
    totalsteps = (maxlength - minlength) / lengthstep
    last_time = clock()
    step_time = nan
    alpha = 0.9
    for i, length in enumerate(xrange(minlength, maxlength, lengthstep)):
        if len(data) <= length + len(taper):
            continue
        eta = (totalsteps - i) * step_time
        sys.stdout.write("Scanning length % 8d of % 8d (% 6.2f%%), eta %.0f:%04.1f...\r" % ((i, totalsteps, i * 100.0 / totalsteps) + divmod(eta, 60)))
        sys.stdout.flush()
        offset, error = findmatch(data, length, taper)
        if error < minerror:
            minerror = error
            bestoffset = offset
            bestlength = length
        if isnan(step_time):
            step_time = clock() - last_time
        else:
            step_time = alpha * step_time + (1.0 - alpha) * (clock() - last_time) # moving average over step time
        last_time = clock()
    return bestoffset + minoffset, bestlength

def make_noise(length, power_law):
    frequencies = array(range((length+1)/2) + range(length/2, 0, -1)).astype(float)
    return ifft(amap(power_law, frequencies) * fft(randn(length)))

if __name__ == "__main__":
    infilename = "/local/wenger/Daten/music/test.wav"
    outfilename = "/local/wenger/Daten/music/test-skip.wav"
    from scikits.audiolab import wavread, wavwrite

    data, fs, enc = wavread(infilename)
    data = mean(data, axis=1) # make mono
    print "The file is %d samples (%d:%04.1f) long, at %d samples per second." % ((len(data),) + divmod(len(data) / float(fs), 60) + (fs,))

    length_step = fs / 50 # TODO detect length of one bar
    print "The step length is %d samples (%d:%04.1f)." % ((length_step,) + divmod(length_step / float(fs), 60))

    window_size = fs / 1 # TODO or use bar length here
    sigma = window_size / 4
    taper = fromfunction(lambda x: exp(-0.5 * ((x - window_size / 2) / sigma) ** 2), (window_size,))
    print "The taper is %d samples (%d:%04.1f) long." % ((len(taper),) + divmod(len(taper) / float(fs), 60))

    minlength = 5 * fs
    print "The minimum repeat length is %d samples (%d:%04.1f)." % ((minlength,) + divmod(minlength / float(fs), 60))

    maxlength = len(data)
    print "The maximum repeat length is %d samples (%d:%04.1f)." % ((maxlength,) + divmod(maxlength / float(fs), 60))

    minoffset = 5 * fs
    print "The minimum allowed offset is %d samples (%d:%04.1f)." % ((minoffset,) + divmod(minoffset / float(fs), 60))

    maxoffset = len(data) - 10 * fs
    print "The maximum allowed offset is %d samples (%d:%04.1f)." % ((maxoffset,) + divmod(maxoffset / float(fs), 60))

    bestoffset, bestlength = find_global_match(data, minlength, maxlength, length_step, taper, minoffset, maxoffset)
    a = bestlength + bestoffset + len(taper) / 2
    b = bestoffset + len(taper) / 2
    print "At sample %d (%d:%04.1f), we will skip back by %d samples (%d:%04.1f)." % ((a,) + divmod(a / float(fs), 60) + (bestlength,) + divmod(bestlength / float(fs), 60))

    composed = hstack((data[:bestlength+bestoffset], 0.5 * (data[bestlength+bestoffset:a] + data[bestoffset:b]), data[b:]))
    wavwrite(composed, outfilename, fs, enc)

