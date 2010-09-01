from scipy.spatial.distance import cdist, squareform

class AnalysisLayer(object):
    def __init__(self, data1, data2, block_length, num_keep):
        # split data into non-overlapping blocks of length block_length
        blocks1 = data1.reshape(-1, block_length)
        blocks2 = data2.reshape(-1, block_length)

        # compute spectrum of each block (could also be mel analysis or the like)
        feature_vectors1 = abs(fft(blocks1))
        feature_vectors2 = abs(fft(blocks2))

        # compute correlations between feature vectors
        correlations = squareform(cdist(feature_vectors1, feature_vectors2, "correlation"))

        # find best num_keep off-diagonal child indices and their respective correlations
        # TODO self.i, self.j, self.c = find_best(correlations, num_keep)
        
        # reduce block size
        new_block_length = block_length / 16

        # keep specified density of matches, but at least one per child
        new_num_keep = max(round(num_keep * (block_length / new_block_length) ** 2 / float(len(blocks1) * len(blocks2))), 1)

        # if children are not empty, initialize them
        if new_block_length > 1:
            self.children = []
            for i, j, c in zip(self.i, self.j, self.c):
                self.children.append(AnalysisLayer(data1[i], data2[j], new_block_length, new_num_keep))

def analyze(data, block_length, num_keep):
    data = data[:block_length * (len(data) // block_length)]
    return AnalysisLayer(data, data, block_length, num_keep)

if __name__ == "__main__":
    infilename = "/local/wenger/Daten/music/test.wav"
    outfilename = "/local/wenger/Daten/music/test-skip.wav"

    from scikits.audiolab import wavread, wavwrite
    data, fs, enc = wavread(infilename)
    data = mean(data, axis=1) # make mono
    print "The file is %d samples (%d:%04.1f) long, at %d samples per second." % ((len(data),) + divmod(len(data) / float(fs), 60) + (fs,))

    root = analyze(data, 2 ** 18, 32) # TODO do something with the result

