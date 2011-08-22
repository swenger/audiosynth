from itertools import izip_longest

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

def draw_line(x0, x1, y0, y1, color=None):
    if color:
        pyglet.gl.glColor3f(*color)
    pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ("v2f", (x0, y0, x1, y1)))

def draw_point(x, y, color=None):
    if color:
        pyglet.gl.glColor3f(*color)
    pyglet.graphics.draw(1, pyglet.gl.GL_POINTS, ("v2f", (x, y))) # TODO draw marker

def draw_keypoints(source_keypoints, target_keypoints, color=(1, 0, 0)):
    for s, t in zip(source_keypoints, target_keypoints):
        draw_point(s, t, color)

def draw_path(segments, position=None, play_color=(0, 0, 1), jump_color=(0, 1, 0)):
    """Draw a path up to the specified `position`."""
    start = 0
    for s0, s1 in izip_longest(segments, segments[1:]):
        if position is None or start + s0[1] - s0[0] <= position:
            draw_line(s0[0], s0[1], start, start + s0[1] - s0[0], play_color)
        elif position != start:
            duration = (position - start)
            draw_line(s0[0], s0[0] + duration, start, start + duration, play_color)
        start += s0[1] - s0[0]
        if position is not None and start > position:
            break
        if s1 is not None:
            draw_line(s0[1], s1[0], start, start, jump_color)

if __name__ == "__main__":
    import sys
    from scipy.io import wavfile
    from datafile import read_datafile

    if len(sys.argv) != 3:
        print >> sys.stderr, "Usage: %s wavfilename pathfilename" % sys.argv[0]
        sys.exit(1)

    wavfilename = sys.argv[1]
    pathfilename = sys.argv[2]

    sound = ArraySource(*wavfile.read(wavfilename))

    pathdata = read_datafile(pathfilename)
    rate = float(pathdata["rate"])
    source_keypoints = [x / rate for x in pathdata["source_keypoints"]]
    target_keypoints = [x / rate for x in pathdata["target_keypoints"]]
    segments = [(start_sample / rate, end_sample / rate) for start_sample, start_time, end_sample, end_time in pathdata["data"]]
    max_source = pathdata["length"] / rate
    max_target = max(max(target_keypoints), sum(s[1] - s[0] for s in segments))

    window = pyglet.window.Window(resizable=True)

    @window.event
    def on_resize(width, height):
        pyglet.gl.glViewport(0, 0, width, height)
        pyglet.gl.glMatrixMode(pyglet.gl.GL_PROJECTION)
        pyglet.gl.glLoadIdentity()
        pyglet.gl.glOrtho(0, max_source, 0, max_target, -1, 1) # TODO does not work, why?
        pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)

    @window.event
    def on_draw():
        window.clear()
        draw_path(segments, play_color=(1.0, 1.0, 1.0), jump_color=(1.0, 1.0, 1.0))
        draw_path(segments, player.time, play_color=(0.0, 0.0, 1.0), jump_color=(0.0, 1.0, 0.0))
        draw_keypoints(source_keypoints, target_keypoints)

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.SPACE:
            if player.playing:
                player.pause()
            else:
                player.play()
        elif symbol == pyglet.window.key.LEFT:
            player.seek(player.time - 5.0)
            player.play()
        elif symbol == pyglet.window.key.RIGHT:
            player.seek(player.time + 5.0)
            player.play()

    player = pyglet.media.Player()
    player.queue(sound)
    player.play()

    pyglet.app.run()

