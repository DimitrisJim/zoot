import argparse, os, subprocess
from contextlib import AbstractContextManager
from pathlib import Path

CPY_LIB = Path("Lib")
RUSTPY_LIB = Path("pylib") / 'Lib'


class FileTest:

    def __init__(self, args: argparse.Namespace) -> None:
        self.cpython_path = Path(args.cpython) / CPY_LIB / 'test/'
        self.rustpython_path = Path(args.rustpython) / RUSTPY_LIB / 'test/'
        self.fname = args.testname
        self.verbosity = args.verbose

    def _read(self, path: Path) -> str:
        with open(path / self.fname, 'r') as f:
            return f.read()

    def read_pyfile(self) -> str:
        return self._read(self.cpython_path)

    def read_rustpyfile(self) -> str:
        return self._read(self.rustpython_path)

    def write_rustpyfile(self, content: str) -> None:
        with open(self.rustpython_path / self.fname, 'w') as f:
            f.write(content)


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