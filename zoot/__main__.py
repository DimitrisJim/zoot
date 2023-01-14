""" Copy tests over from cpython source to rustpython."""
import argparse
import sys
import os
from pathlib import Path
from zoot.helpers import cpython_branch, git_exists
from zoot.drive import Driver

CPYTHON = Path.home() / "Devel/cpython"
RUSTPYTHON = Path.home() / "Devel/RustPython"
MIN_BRANCH = "3.10"
MAIN_BRANCH = "3.12"  # TODO: Make this dynamic.
ZOOT_DESC = """
zoot helps with syncing the stdlib between CPython and RustPython, it does this by
copying files from a specific branch of CPython to RustPython.

For test files, `unittest.skip` and `unittest.expectedFailure`, decorators that
annotate test methods that fail, are grabbed from the files in RustPython and
copied over to the CPython files from the target branch. This is done to ensure 
that the tests are still marked as failing in the target branch. Directory structured
tests, like `test_json` or `test_importlib` are not handled. If any unexpected
mentions of `RUSTPYTHON` are found in a comment not preceding a decorator, a warning
is printed.

If the `--copy-libs` files is passed, simple library files are copied 
over from CPython to RustPython, no changes are made to the library files themselves.
Libraries are located by stripping the `test_` prefix from the supplied names and
looking for the files in the `Lib` directory of CPython. If one is found, the library
gets copied, otherwise a warning is printed. A library file is considered simple if
it is a single Python file, i.e not a directory.
"""

argparser = argparse.ArgumentParser(
    prog="zoot", description=ZOOT_DESC, formatter_class=argparse.RawTextHelpFormatter
)
argparser.add_argument(
    "--cpython", help="Absolute path to CPython source", default=CPYTHON, type=str
)
argparser.add_argument(
    "--rustpython",
    help="Absolute path to RustPython source",
    default=RUSTPYTHON,
    type=str,
)
argparser.add_argument(
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="Increase verbosity. Default '%(default)s'.",
)
argparser.add_argument(
    "--branch",
    help="Branch of CPython to target. Default '%(default)s'.",
    default="3.11",
    type=str,
)
argparser.add_argument(
    "filenames",
    help="Names of the test files (test_string, test_binop)",
    type=str,
    nargs="+",
)
argparser.add_argument(
    "--copy-libs",
    help="Allow copying of library files. Default '%(default)s'",
    action="store_true",
    default=True,
)
# TODO: Support dry run?
argparser.add_argument(
    "--dry",
    help="Don't actually copy files. Default '%(default)s'.",
    action="store_true",
    default=False,
)


def validate(args: argparse.Namespace) -> None:
    """Check that paths exist, version is correct."""
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
    if args.branch == "main":
        # switch it over to 3.12
        args.branch = MAIN_BRANCH


def main() -> None:
    # go for a minimum of 3.8
    if sys.version_info < (3, 8):
        print("[ERROR]: zoot requires python 3.8 or greater", file=sys.stderr)
        sys.exit(1)
    if not git_exists():
        print("[ERROR]: zoot requires git!", file=sys.stderr)
        sys.exit(1)
    # ok to assume from here-on out that git is here.
    args = argparser.parse_args()
    validate(args)
    Driver(args).run()

if __name__ == "__main__":
    main()
