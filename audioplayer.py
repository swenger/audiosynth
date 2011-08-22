import pyglet

class ArraySource(pyglet.media.StaticMemorySource):
    '''A source that has been created from a numpy array.'''

    def __init__(self, rate, data):
        '''Construct an `ArraySource` for the data in `data`.
        
        :Parameters:
            `rate` : `int`
                The sampling rate in Hertz.
            `data` : `array`
                A c-contiguous numpy array of dimension (num_samples, num_channels).
        '''
        
        if data.ndim not in (1, 2):
            raise ValueError("The data array must be one- or two-dimensional.""")

        if not data.flags.c_contiguous:
            raise ValueError("The data array must be c-contiguous.""")

        num_channels = data.shape[1] if data.ndim > 1 else 1
        if num_channels not in [1, 2]:
            raise ValueError("Only mono and stereo audio are supported.""")
        
        num_bits = data.dtype.itemsize * 8
        if num_bits not in [8, 16]:
            raise ValueError("Only 8 and 16 bit audio are supported.""")
        
        audio_format = pyglet.media.AudioFormat(num_channels, num_bits, rate)

        super(ArraySource, self).__init__(data.tostring(), audio_format)

    def _get_queue_source(self):
        return self



if __name__ == "__main__":
    import sys
    from scipy.io import wavfile

    sound = ArraySource(*wavfile.read(sys.argv[1]))

    """
    window = pyglet.window.Window()

    @window.event
    def on_draw():
        window.clear()
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ("v2f", (10, 10, 10, 10 + player.time)))
        """

    player = pyglet.media.Player()
    player.queue(sound)
    player.play()

    pyglet.app.run()

