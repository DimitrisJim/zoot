import os, subprocess
from contextlib import AbstractContextManager

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


def cpython_branch(path: str) -> str:
    """ Grab the branch of cpython. """
    with chdir(path):
        return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()