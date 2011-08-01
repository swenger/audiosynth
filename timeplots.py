import numpy as np
import matplotlib
import matplotlib.ticker

class FrameTimeLocator(matplotlib.ticker.Locator):
    def __init__(self, fps, n_steps=10, steps=None):
        self._fps = float(fps)
        self._n_steps = n_steps
        self._steps = steps or [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 5, 10, 30, 1 * 60, 5 * 60, 10 * 60, 30 * 60, 60 * 60]

    def __call__(self):
        vmin, vmax = self.axis.get_view_interval()
        tmin, tmax = vmin / self._fps, vmax / self._fps

        # find step size that gives a number of steps closest to the desired step size
        step = self._steps[np.argmin([abs((tmax - tmin) / step - self._n_steps) for step in self._steps])]
        
        # find nearest multiple of step size
        rmin, rmax = round(tmin / float(step)), round(tmax / float(step))
        return np.arange(rmin, rmax + 1) * step * self._fps

class FrameTimeFormatter(matplotlib.ticker.Formatter):
    def __init__(self, fps, decimals=0):
        self._fps = float(fps)
        self._decimals = int(decimals)

    def __call__(self, frame, pos=None):
        minutes, seconds = divmod(frame / self._fps, 60)
        if self._decimals:
            return "%d:%0*.*f" % (minutes, 3 + self._decimals, self._decimals, seconds)
        else:
            return "%d:%02d" % (minutes, seconds)

def cumreduce(function, sequence, initial=Ellipsis):
    if initial is Ellipsis:
        return reduce(lambda lst, item: lst + [function(lst[-1], item)], sequence[1:], [sequence[0]])
    else:
        return reduce(lambda lst, item: lst + [function(lst[-1], item)], sequence, [initial])

if __name__ == "__main__":
    from pylab import axes, show

    fps = 5 # frames per second
    total_time = 180 # seconds
    a = 0.01 # moving average innovation factor

    signal = cumreduce(lambda old, new: (1.0 - a) * old + a * new, np.random.random(fps * total_time))

    ax = axes()
    ax.xaxis.set_major_locator(FrameTimeLocator(fps, 10))
    ax.xaxis.set_minor_locator(FrameTimeLocator(fps, 100))
    ax.xaxis.set_major_formatter(FrameTimeFormatter(fps))
    ax.plot(signal)
    
    show()

