""" Copy tests over from cpython source to rustpython. Ideally, can automatically mark tests that are failing in rustpython. 

TODO: Use git to restore a given test file if a SyntaxError is encountered?
TODO: spit out names on single verbosity, spit out diffs when doubled.
TODO: Execute test files with tip of rustpython binary and add skips when necessary. Iff a syntax error is
      encountered, it should probably be skipped all together after informing user.

      - On success, error code is 0 -> do nada.
      - On segfault, error code is 139 (not sure if this is consistent across platforms) -> unittest.skip
      - On syntax error, error? -> unittest.expectedFailure?

TODO: Can actually do this for lib files too, not only tests.
"""
import argparse
import sys
import os

from testsync.annotate import DecoCollector, DecoAnnotator
from testsync.helpers import cpython_branch, git_exists


cpy = '/home/imijmi/Devel/cpython'
rustpy = '/home/imijmi/Devel/RustPython'

argparser = argparse.ArgumentParser(
    prog="testsync", description="Copy libs/tests over from cpython source to rustpython."
)
# make these two required arguments
# TODO: allow cpython as a git repo?
argparser.add_argument("--cpython", help="Absolute path to cpython source", default=cpy, type=str)
argparser.add_argument("--rustpython", help="Absolute path to rustpython source", default=rustpy, type=str)

argparser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
argparser.add_argument("--branch", help="Branch of CPython to target", default='3.11', type=str)
argparser.add_argument("--annotate", help="Annotate with @skip the tests that are failing in rustpython", default=True, action="store_true")

files = argparser.add_subparsers(help="Files to copy over")
libs = files.add_parser("lib", help="Copy over lib files")
libs.add_argument("libname", metavar="name", help="Lib file to copy over", type=str, nargs="?")
libs.add_argument("--n", dest='libname', help="Lib file to copy over", type=str, required=False)
libs.add_argument("--copy-tests", help="Try and copy the test file for this library", action="store_true", default=False)
libs.add_argument("--all", dest="all_libs", help="Copy over all lib files", action="store_true", default=False)
tests = files.add_parser("test", help="Copy over test files")
tests.add_argument("testname", metavar="name", help="Test file to copy over", type=str, nargs="?")
tests.add_argument("-n", dest='testname', help="Test file to copy over", type=str, required=False)
tests.add_argument("--all", dest="all_tests", help="Copy over all test files", action="store_true", default=False)


def validate_args(args: argparse.Namespace) -> None:
    """ Check that paths exist, version is correct. """
    if not os.path.isdir(args.cpython):
        print("ERROR: Path '{}' to CPython does not denote a directory".format(args.cpython), file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.rustpython):
        print("ERROR: Path '{}' to RustPython does not denote a directory".format(args.rustpython), file=sys.stderr)
        sys.exit(1)
    if args.branch != cpython_branch(args.cpython):
        print("ERROR: CPython branch is not set to {}".format(args.branch), file=sys.stderr)
        sys.exit(1)


def main() -> None:
    args = argparser.parse_args()
    validate_args(args)
    # Get the files to copy over.

    return sys.exit(0)



if __name__ == "__main__":
    # go for a minimum of 3.8
    if sys.version_info < (3, 8):
        print("ERROR: testsyncrequires python 3.8 or greater", file=sys.stderr)
        sys.exit(1)
    if not git_exists():
        print("ERROR: testsyncrequires git!", file=sys.stderr)
        sys.exit(1)
    # ok to assume from hereon out that git is here.
    main()