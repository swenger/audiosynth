def write_datafile(filename, header, data, fmt=None):
    with open(filename, "w") as f:
        if fmt:
            print >> f, "format =", tuple(x.__name__ for x in fmt)
        for key, value in header.items():
            print >> f, "%s = %s" % (key, repr(value))
        for line in data:
            if fmt:
                print >> f, repr(tuple(fmt(value) for fmt, value in zip(fmt, line)))
            else:
                print >> f, repr(line)

def read_datafile(filename):
    with open(filename, "r") as f:
        header, data, fmt = dict(), [], None
        for line in f:
            if not data and "=" in line:
                key, value = [x.strip() for x in line.split("=", 1)]
                if key == "format":
                    fmt = tuple(eval(x) for x in eval(value))
                else:
                    header[key] = eval(value)
            else:
                if fmt:
                    data.append(tuple(fmt(value) for fmt, value in zip(fmt, eval(line))))
                else:
                    data.append(eval(line))
        return header, data

