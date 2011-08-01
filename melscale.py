from numpy import log, exp, abs, array, linspace, maximum, minimum, fromfunction, dot
from scipy.fftpack import fft, dct

def hertz_to_mel(hertz):
    return 1127.0 * log(1.0 + hertz / 700.0)

def mel_to_hertz(mel):
    return 700.0 * (exp(mel / 1127.0) - 1.0)

def triangular_window(a, m, b):
    return lambda i: maximum(0, minimum((i - a) / (m - a) ** 2, (b - i) / (b - m) ** 2))

def mfcc(x, n):
    """Compute the ``n`` component mel-frequency cepstral coefficients of the signal ``x``."""
    n += 2
    ft = abs(fft(x)) ** 2
    if len(ft) % 2 == 0:
        spectrum = array([ft[0]] + list(ft[1:len(ft)/2-1] + ft[-1:len(ft)/2+1:-1]) + [ft[len(ft)/2]])
    else:
        spectrum = array([ft[0]] + list(ft[1:len(ft)/2] + ft[-1:len(ft)/2+1:-1]))
    f_max = hertz_to_mel(len(spectrum) - 1)
    fs = [mel_to_hertz(f) for f in linspace(0, f_max, n)]
    windows = zip(fs[:-2], fs[1:-1], fs[2:])
    kernels = array([fromfunction(triangular_window(a, m, b), (len(spectrum),)) for (a, m, b) in windows])
    mel = dot(kernels, spectrum)
    return abs(dct(log(mel)))

