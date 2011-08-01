def frametime(rate, frame, minute_digits=2, decimals=2):
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

