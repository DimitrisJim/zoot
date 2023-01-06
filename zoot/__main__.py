""" Copy tests over from cpython source to rustpython."""
import argparse
import sys
import os
from pathlib import Path

from zoot.annotate import DecoCollector, DecoAnnotator
from zoot.helpers import cpython_branch, git_exists

CPYTHON = Path.home() / 'Devel/cpython'
RUSTPYTHON = Path.home() / 'Devel/RustPython'
MIN_BRANCH = '3.10'

argparser = argparse.ArgumentParser(
    prog="zoot", description="Copy and annotate test from cpython source to rustpython."
)
argparser.add_argument(
    "--cpython", help="Absolute path to cpython source", default=CPYTHON, type=str
)
argparser.add_argument(
    "--rustpython", 
    help="Absolute path to rustpython source", 
    default=RUSTPYTHON, 
    type=str
)
argparser.add_argument(
    "-v", "--verbose", action="count", default=0, help="Increase verbosity"
)
argparser.add_argument(
    "--branch", help="Branch of CPython to target", default='3.11', type=str
)
argparser.add_argument(
    "--testname", help="Name of test file", type=str
)

def validate_args(args: argparse.Namespace) -> None:
    """ Check that paths exist, version is correct. """
    fmt = []
    if not os.path.isdir(args.cpython):
        fmt.append(f"Path '{args.cpython}' to CPython is not a directory")
    if not os.path.isdir(args.rustpython):
        fmt.append(f"Path '{args.rustpython}' to RustPython is not a directory")
    if args.branch <= MIN_BRANCH:
        fmt.append(f"Branch '{args.branch}' is less than minimum branch '{MIN_BRANCH}'")
    if args.branch != cpython_branch(args.cpython):
        fmt.append(f"CPython branch is not set to {args.branch}")
    if fmt:
        print(f"[ERROR]: {fmt}", file=sys.stderr)
        sys.exit(1)

def run() -> None:
    """
    The steps for a conforming commit history are:
     1. Copy the new file and commit it with message "Update <name> from CPython 
        <branch>"
     2. Apply the annotations to the file, if the file executes without failures -> Done
     3. If the file fails, additional by-hand annotations are needed -> Done
     
    [Done]: Commit the new file with message: "Mark failing tests."
    """
    args = argparser.parse_args()
    validate_args(args)
    # Get the files to copy over.
    _ = DecoCollector()
    _ = DecoAnnotator(None, None)
    return sys.exit(0)


if __name__ == "__main__":
    # go for a minimum of 3.8
    if sys.version_info < (3, 8):
        print("ERROR: zoot requires python 3.8 or greater", file=sys.stderr)
        sys.exit(1)
    if not git_exists():
        print("ERROR: zoot requires git!", file=sys.stderr)
        sys.exit(1)
    # ok to assume from here-on out that git is here.
    run()