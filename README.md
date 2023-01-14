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
in the RustPython repo and then re-applied along with any preceding `# TODO: RUSTPYTHON` comments to the new file 
copied over from CPython. 

Ideally, can automatically mark tests that are failing in rustpython. 

## Usage

Flesh this out a bit more.

```bash
$ python -m zoot --cpython <path to cpython dir> --rustpython <path to rustpython dir> <names of test files>
```

## Requirements

Requires `libCST` and Python 3.8+, `pytest` for testing.

### A couple of TODOs:

 1. Execute test files with tip of rustpython binary and add skips when necessary? -- This requires
    disambiguation of different error codes returned and a way to grab test-names. Can do this with
    the test lib.  
 2. Allow running things for more than one file at a time.
 3. Have it watch for file changes in the CPython repo and automatically automatically open a PR for the changes on
    my local fork of RustPython. After reviewing the changes I can push it back upstream. Use submodules for this?