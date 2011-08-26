import re

def frametime(frame, rate=1, minute_digits=2, decimals=2):
    """Convert a frame number to a time signature."""
    minutes, seconds = divmod(frame / float(rate), 60)
    return "%0*d:%0*.*f" % (minute_digits, minutes, 3 + decimals, decimals, seconds)

def make_lookup(dtype, **constants):
    """Try to read a value from a dictionary; if it fails, cast the value to the specified type."""
    def lookup(x):
        try:
            return constants[x]
        except KeyError:
            return dtype(x)
    return lookup

def ptime(s):
    """Parse a time from a string."""
    r = re.compile(r"(?:(?:(\d+):)?(\d+):)?(\d+(?:.\d+)?)")
    h, m, s = r.match(s).groups()
    return int(h or 0) * 60 * 60 + int(m or 0) * 60 + float(s)
