import argparse, os, subprocess, sys
from contextlib import AbstractContextManager

from testsync.helpers import git_diff

CPY_LIB = 'Lib/'
RUSTPY_LIB = 'pylib/Lib/'


# TODO: Refactor this.
class GetABetterName:
    """ Copy over tests from CPython to RustPython. """
    def __init__(self, args: argparse.Namespace) -> None:
        is_lib = hasattr(args, 'libname')

        self.cpython_path = os.path.join(args.cpython, (CPY_LIB if is_lib else os.path.join(CPY_LIB, 'test/')))
        self.rustpython_path = os.path.join(args.rustpython, (RUSTPY_LIB if is_lib else os.path.join(RUSTPY_LIB, 'test/')))
        self.fname = args.libname if is_lib else args.testname
        self.copy_all = getattr(args, 'all_tests', False) or getattr(args, 'all_libs', False)
        self.verbosity = args.verbose
        # can only be true if copying a lib.
        self.copy_test = args.copy_tests if is_lib else False

    def _copy(self, source: str, dest: str, file: str) -> None:
        """ Copy a single file from CPython to RustPython if there's a diff. """
        cpy = os.path.join(source, file)
        rustpy = os.path.join(dest, file)
        if os.path.exists(cpy) and not os.path.exists(rustpy):
            # TODO: Move anyway? (for now, report that the file does not exist, don't copy over)
            print("File '{}' does not exist in RustPython.".format(rustpy))
            return
        if self.verbosity > 0:
            print("Copying '{}' to '{}'.".format(cpy, rustpy))
        diff = git_diff(rustpy, cpy)
        if not diff:
            print("File '{}' is up to date!".format(file), file=sys.stderr)
            return
        if self.verbosity > 0:
            print("Copying over file '{}'".format(file))
            if self.verbosity > 1:
                print(diff)
        
        # TODO: do the copy, check that file exists.
        return

    def copy(self) -> None:
        """ Copy over a single file or all files. """
        # note: when running a single file, we do not know if it *actually* exists.
        files = []
        if self.copy_all:
            # note: filter by files, for now.
            files = get_files(self.cpython_path)
            if self.copy_test:
                # note: filter by files, for now.
                files += get_files(os.path.join(self.cpython_path, 'test/'))
        else:
            files.append(self.fname)
            if self.copy_test:
                files.append("test_{}.py".format(self.fname.rsplit('.')[0]))

        for file in files:
            self._copy(self.cpython_path, self.rustpython_path, file)



def get_files(path) -> list:
    """ Traverse the path and return only files, excluding directories for now. """
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]


# copied over from source, so as to not require 3.11 to run the script.
class chdir(AbstractContextManager):
    """Non thread-safe context manager to change the current working directory."""

    def __init__(self, path):
        self.path = path
        self._old_cwd = []

    def __enter__(self):
        self._old_cwd.append(os.getcwd())
        os.chdir(self.path)

    def __exit__(self, *excinfo):
        os.chdir(self._old_cwd.pop())


def git_exists() -> bool:
    """ Check if git is installed."""
    try:
        subprocess.check_output(["git", "--version"])
    except subprocess.CalledProcessError:
        return False
    return True

def git_restore(rustpy_repo: str, file: str) -> bool:
    """ Roll back any changes made if a failure was detected. """
    with chdir(rustpy_repo):
        try:
            subprocess.check_output(["git", "restore", file])
        except subprocess.CalledProcessError:
            return False
    return True

def git_diff(cpy_file: str, rustpy_file: str) -> str:
    """ Grab the diff."""
    res = subprocess.run(["git", "diff", "--no-index", cpy_file, rustpy_file], capture_output=True)
    return res.stdout.decode('utf-8')

def cpython_branch(path: str) -> str:
    """ Grab the branch of cpython. """
    with chdir(path):
        return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()