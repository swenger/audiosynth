def write_datafile(filename, contents):
    with open(filename, "w") as f:
        for key, value in contents.items():
            print >> f, "%s = %s" % (key, repr(value))

def read_datafile(filename):
    g = {}
    contents = {}
    execfile(filename, g, contents)
    return contents

