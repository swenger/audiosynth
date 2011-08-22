#!/usr/bin/env python

from bisect import bisect
from itertools import izip_longest

import pyglet

from algorithms.algorithm import Segment

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

def draw_point(x, y, color=None, size=5):
    if color:
        pyglet.gl.glColor3f(*color)
    pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ("v2f", (x - 0.5 * size, y - 0.5 * size, x + 0.5 * size, y + 0.5 * size)))
    pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ("v2f", (x - 0.5 * size, y + 0.5 * size, x + 0.5 * size, y - 0.5 * size)))

def draw_keypoints(source_keypoints, target_keypoints, scale_source, scale_target, offset_source, offset_target, color=(1, 0, 0)):
    for s, t in zip(source_keypoints, target_keypoints):
        draw_point(scale_source * s + offset_source, scale_target * t + offset_target, color)

def draw_path(segments, position=None, play_color=(0, 0, 1), jump_color=(0, 1, 0)):
    """Draw a path up to the specified `position`."""
    start = 0
    for s0, s1 in izip_longest(segments, segments[1:]):
        if position is None or start + s0.duration <= position:
            draw_line(s0.start, s0.end, start, start + s0.duration, play_color)
        elif position != start:
            duration = (position - start)
            draw_line(s0.start, s0.start + duration, start, start + duration, play_color)
        start += s0.duration
        if position is not None and start > position:
            break
        if s1 is not None:
            draw_line(s0.end, s1.start, start, start, jump_color)

def play(rate, data, source_keypoints, target_keypoints, raw_segments, length):
    sound = ArraySource(rate, data)

    source_keypoints = [x / rate for x in source_keypoints]
    target_keypoints = [x / rate for x in target_keypoints]

    # combine segments between which no jump occurs
    segments = []
    for segment in (Segment(start_sample / rate, end_sample / rate) for start_sample, end_sample in raw_segments):
        if segments and segments[-1].end == segment.start - 1:
            segments[-1] = Segment(segments[-1].start, segment.end)
        else:
            segments.append(segment)

    max_source = length / rate
    max_target = max(max(target_keypoints), sum(s[1] - s[0] for s in segments))

    target_starts = reduce(lambda x, y: x + [x[-1] + y], (s.duration for s in segments), [0])
    points_of_interest = sorted(set([max(x - 3, 0) for x in target_starts]))

    window = pyglet.window.Window(resizable=True)

    pyglet.gl.glEnable(pyglet.gl.GL_LINE_SMOOTH)
    pyglet.gl.glHint(pyglet.gl.GL_LINE_SMOOTH_HINT, pyglet.gl.GL_NICEST)
    pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
    pyglet.gl.glEnable(pyglet.gl.GL_BLEND)

    @window.event
    def on_draw():
        window.clear()
        pyglet.gl.glPushMatrix()
        offset_source = 5.0
        offset_target = 5.0
        scale_source = (window.width - 10) / float(max_source)
        scale_target = (window.height - 10) / float(max_target)
        pyglet.gl.glScalef(scale_source, scale_target, 1.0)
        pyglet.gl.glTranslatef(offset_source / scale_source, offset_target / scale_target, 1.0)
        draw_path(segments, play_color=(1.0, 1.0, 1.0), jump_color=(1.0, 1.0, 1.0))
        draw_path(segments, player.time, play_color=(0.0, 0.0, 1.0), jump_color=(0.0, 1.0, 0.0))
        pyglet.gl.glPopMatrix()
        draw_keypoints(source_keypoints, target_keypoints, scale_source, scale_target, offset_source, offset_target)

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.SPACE: # pause / unpause
            if player.playing:
                player.pause()
            else:
                player.play()
        elif symbol == pyglet.window.key.LEFT: # jump back 5 seconds
            player.seek(player.time - 5.0)
            if player.playing:
                player.play()
        elif symbol == pyglet.window.key.RIGHT: # jump forward 5 seconds
            player.seek(player.time + 5.0)
            if player.playing:
                player.play()
        elif symbol == pyglet.window.key.UP: # jump to shortly before next cut
            current_segment_idx = bisect(points_of_interest[1:], player.time)
            try:
                player.seek(max(points_of_interest[current_segment_idx + 1], 0.0))
                if player.playing:
                    player.play()
            except IndexError:
                pass
        elif symbol == pyglet.window.key.DOWN: # jump to shortly before last cut
            current_segment_idx = bisect(points_of_interest[1:], player.time)
            if current_segment_idx:
                player.seek(max(points_of_interest[current_segment_idx - 1], 0.0))
            else:
                player.seek(0)
            if player.playing:
                player.play()

    player = pyglet.media.Player()
    player.queue(sound)
    player.play()

    pyglet.app.run()

if __name__ == "__main__":
    import sys
    from scipy.io import wavfile
    from datafile import read_datafile

    if len(sys.argv) != 3:
        print >> sys.stderr, "Usage: %s wavfilename pathfilename" % sys.argv[0]
        sys.exit(1)

    rate, data = wavfile.read(sys.argv[1])
    pathdata = read_datafile(sys.argv[2])
    segments = [(start_sample, end_sample) for start_sample, start_time, end_sample, end_time in pathdata["data"]]

    play(rate, data, pathdata["source_keypoints"], pathdata["target_keypoints"], segments, pathdata["length"])

