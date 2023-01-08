import os
import subprocess
from typing import List, Union
from contextlib import AbstractContextManager
from pathlib import Path

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


# A couple of very basic helpers for calling git,
# don't wanna use another dep.


def git_add(filename: Union[Path, str], path: Union[Path, str]):
    """Add a file to git."""
    _run_in_dir(["git", "add", filename], path)


def git_commit(filename: Union[Path, str], path: Union[Path, str], msg: str):
    """Commit a file to git."""
    try:
        _run_in_dir(["git", "commit", "-m", msg], path)
    except subprocess.CalledProcessError:
        # restore the file if the commit fails
        git_restore(filename, path, staged=True)


def git_add_commit(filename: Union[Path, str], path: Union[Path, str], msg: str):
    """Add and commit a file to git."""
    git_add(filename, path)
    git_commit(filename, path, msg)


def git_exists() -> bool:
    """Check if git is installed."""
    try:
        subprocess.check_output(["git", "--version"])
    except subprocess.CalledProcessError:
        return False
    return True


def git_restore(
    filename: Union[Path, str], path: Union[Path, str], staged: bool = False
) -> bool:
    """Roll back any changes made if a failure was detected."""
    try:
        cmd = (
            ["git", "restore", "--staged", filename]
            if staged
            else ["git", "restore", filename]
        )
        _run_in_dir(cmd, path)
    except subprocess.CalledProcessError:
        return False
    return True


def git_diff(cpy_file: Path, rustpy_file: Path) -> str:
    """Grab the diff."""
    res = subprocess.run(
        ["git", "diff", "--no-index", cpy_file, rustpy_file], capture_output=True
    )
    return res.stdout.decode("utf-8")


def cpython_branch(path: Path) -> str:
    """Grab the branch of cpython."""
    with chdir(path):
        return (
            subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            .decode("utf-8")
            .strip()
        )


def _run_in_dir(cmd: List[Union[str, Path]], path: Union[str, Path]) -> str:
    """Run a command in a directory."""
    with chdir(path):
        return subprocess.check_output(cmd).decode("utf-8").strip()
