""" Copy tests over from cpython source to rustpython. Ideally, can automatically mark tests that are failing in rustpython. 

TODO: Use configparser for CPYTHON, RUSTPYTHON, MIN_BRANCH?
TODO: Automatically copy lib? Could work for simple lib.
TODO: Use git to restore a given test file if a SyntaxError is encountered?
TODO: spit out names on single verbosity, spit out diffs when doubled.
TODO: Execute test files with tip of rustpython binary and add skips when necessary. This requires
      disambiguation of different error codes returned and a way to grab test-names. Can do this with
      the test lib.
"""
import argparse
import sys
import os
from pathlib import Path

from testsync.annotate import DecoCollector, DecoAnnotator
from testsync.helpers import cpython_branch, git_exists

CPYTHON = Path.home() / 'Devel/cpython'
RUSTPYTHON = Path.home() / 'Devel/RustPython'
MIN_BRANCH = '3.10'

argparser = argparse.ArgumentParser(
    prog="testsync", description="Copy and annotate test from cpython source to rustpython."
)
argparser.add_argument("--cpython", help="Absolute path to cpython source", default=CPYTHON, type=str)
argparser.add_argument("--rustpython", help="Absolute path to rustpython source", default=RUSTPYTHON, type=str)

argparser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
argparser.add_argument("--branch", help="Branch of CPython to target", default='3.11', type=str)
# TODO: Automatically copy lib? Could work for simple lib.
argparser.add_argument("--testname", help="Name of test file", type=str)

def validate_args(args: argparse.Namespace) -> None:
    """ Check that paths exist, version is correct. """
    if not os.path.isdir(args.cpython):
        print("ERROR: Path '{}' to CPython does not denote a directory".format(args.cpython), file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.rustpython):
        print("ERROR: Path '{}' to RustPython does not denote a directory".format(args.rustpython), file=sys.stderr)
        sys.exit(1)
    if args.branch <= MIN_BRANCH:
        print("ERROR: CPython 3.10 is the minimum target branch", file=sys.stderr)
        sys.exit(1)
    if args.branch != cpython_branch(args.cpython):
        print("ERROR: CPython branch is not set to {}".format(args.branch), file=sys.stderr)
        sys.exit(1)


def run() -> None:
    """
    The steps for a conforming commit history are:
     1. Copy the new file and commit it with message "Update <name> from CPython <branch>"
     2. Apply the annotations to the file, if the file executes without failures -> Done
     3. If the file fails, additional by-hand annotations are needed -> Done
     
    [Done]: Commit the new file with message: "Mark failing tests."
    """
    args = argparser.parse_args()
    validate_args(args)
    # Get the files to copy over.

    return sys.exit(0)


if __name__ == "__main__":
    # go for a minimum of 3.8
    if sys.version_info < (3, 8):
        print("ERROR: testsync requires python 3.8 or greater", file=sys.stderr)
        sys.exit(1)
    if not git_exists():
        print("ERROR: testsync requires git!", file=sys.stderr)
        sys.exit(1)
    # ok to assume from here-on out that git is here.
    run()