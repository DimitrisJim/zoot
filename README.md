# zoot

Sync stdlib between CPython and RustPython. Currently just copies a file over from CPython to RustPython,
grabs any decorators previously specified in the RustPython test file, and then re-applies those
to the new file copied over.

Decorators currently used throughout the test-suite are of the form:

```python
# TODO: RUSTPYTHON <maybe some reason>
@unittest.expectedFailure
```

or:

```python
@unittest.skip("TODO: RUSTPYTHON <maybe some reason>")
```

the `skip` version of the decorators is very rarely used with a test class. 

These decorators denote missing/faulty functionality in RustPython. They are extracted from the test file found
in the RustPython repo and then re-applied along with any preceeding `# TODO: RUSTPYTHON` comments to the new file 
copied over from CPython. 

Ideally, can automatically mark tests that are failing in rustpython. 

## Usage

Flesh this out a bit more.

```bash
$ python -m zoot --cpython <path to cpython dir> --rustpython <path to rustpython dir> --testname <name of test file>
```

## Requirements

Requires `libCST` and Python 3.8+, `pytest` for testing.

### A couple of TODOs:

 1. Use configparser for a couple of the global vars? -- probably.
 2. Automatically copy libs? Could work for simple single file libraries, ones in a directory might
    be trickier. (can be disallowed)
 3. Execute test files with tip of rustpython binary and add skips when necessary? -- This requires
    disambiguation of different error codes returned and a way to grab test-names. Can do this with
    the test lib.  
 4. Spit out names on single verbosity, spit out diffs when doubled -- the diffing is helpful in order
    to not move files unecessarily.
 5. Also look for `# TODO: RustPython` comments in places other than function/class definitions. It
    should warn about this.
 6. Allow running things for more than one file at a time.
 7. Have it watch for file changes in the CPython repo and automatically automatically open a PR for the changes on
    my local fork of RustPython. After reviewing the changes I can push it back upstream. Use submodules for this?