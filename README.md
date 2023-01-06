# zoot

Sync stdlib between CPython and RustPython.

Ideally, can automatically mark tests that are failing in rustpython. 

Requires `libCST` and Python 3.8+.

## A couple of TODOs:

 1. Use configparser for CPYTHON, RUSTPYTHON, MIN_BRANCH -- probably overkill.
 2. Automatically copy libs? Could work for simple single file libraries, ones in a directory might
    be trickier.
 3. Execute test files with tip of rustpython binary and add skips when necessary? -- This requires
    disambiguation of different error codes returned and a way to grab test-names. Can do this with
    the test lib.  
 4. Spit out names on single verbosity, spit out diffs when doubled -- the diffing is helpful in order
    to not move files unecessarily.