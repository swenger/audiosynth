import pyglet

class ArraySource(pyglet.media.StaticMemorySource):
    def __init__(self, rate, data):
        """Create a pyglet audio source from a numpy array.
        
        ``rate`` is the sampling rate in Hertz.
        ``data`` is a c-contiguous numpy array of dimension (num_samples, num_channels)."""
        
        if data.ndim not in (1, 2) or not data.flags.c_contiguous:
            raise ValueError("data must be a c-contiguous array of shape (num_samples, num_channels).""")

        num_channels = data.shape[1] if data.ndim > 1 else 1
        if num_channels not in [1, 2]:
            raise ValueError("only mono and stereo audio are supported.""")
        
        num_bits = data.dtype.itemsize * 8
        if num_bits not in [8, 16]:
            raise ValueError("only 8 and 16 bit audio are supported.""")
        
        audio_format = pyglet.media.AudioFormat(num_channels, num_bits, rate)

        super(ArraySource, self).__init__(data.tostring(), audio_format)

    def _get_queue_source(self):
        return self



if __name__ == "__main__":
    from scipy.io import wavfile
    infilename = "Crag Lake.wav"
    sound = ArraySource(*wavfile.read(infilename)) # sound = pyglet.media.load(infilename)
    print sound.audio_format, sound.duration

    window = pyglet.window.Window()

    @window.event
    def on_draw():
        window.clear()
        # TODO draw a coordinate system and a live plot of playback
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ("v2f", (10, 10, 10, 10 + player.time)))

    player = pyglet.media.Player()
    player.queue(sound)
    player.play()

    pyglet.app.run()

