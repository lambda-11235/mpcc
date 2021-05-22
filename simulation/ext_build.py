from cffi import FFI
ffibuilder = FFI()

#ffibuilder.cdef("float pi_approx(int n);")

with open("../src/mpcc.h") as f:
    s = f.read()
    s = "\n".join([s for s in s.splitlines() if (len(s) > 0 and s[0] != '#')])
    #print(s)
    ffibuilder.cdef(s)

ffibuilder.set_source("_mpcc",  # name of the output C extension
"""
    #include "../src/mpcc.h"
""",
    sources=['../src/mpcc.c'],   # includes pi.c as additional sources
    libraries=['m'])    # on Unix, link with the math library

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
