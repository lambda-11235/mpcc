from cffi import FFI


mpcc = FFI()

with open("../src/mpcc.h") as f:
    s = f.read()
    s = "\n".join([s for s in s.splitlines() if (len(s) > 0 and s[0] != '#')])
    #print(s)
    mpcc.cdef(s)

mpcc.set_source("_mpcc",  # name of the output C extension
"""
    #include "../src/mpcc.h"
""",
    sources=['../src/mpcc.c'],   # includes pi.c as additional sources
    libraries=['m'])    # on Unix, link with the math library


pid = FFI()

with open("../src/pid.h") as f:
    s = f.read()
    s = "\n".join([s for s in s.splitlines() if (len(s) > 0 and s[0] != '#')])
    #print(s)
    pid.cdef(s)

pid.set_source("_pid",  # name of the output C extension
"""
    #include "../src/pid.h"
""",
    sources=['../src/pid.c'],   # includes pi.c as additional sources
    libraries=['m'])    # on Unix, link with the math library


if __name__ == "__main__":
    mpcc.compile(verbose=True)
    print("\n")
    pid.compile(verbose=True)
