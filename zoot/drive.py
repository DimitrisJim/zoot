from pathlib import Path
from typing import Generator, Union, List, Any
from collections import namedtuple
from datetime import datetime
import subprocess
import argparse

from libcst import parse_module

from zoot.annotate import DecoCollector, DecoAnnotator
from zoot.helpers import git_add, git_add_commit, git_checkout

CPYTHON_LIB = Path("Lib")
RUSTPYTHON_LIB = Path("pylib") / "Lib"


class Driver:
    def __init__(self, args: argparse.Namespace) -> None:
        self.verbose = args.verbose
        self.branch = args.branch
        self.testlib = TestLib(args.cpython, args.rustpython, args.testnames)

    def run(self) -> None:
        """
        The steps for a conforming commit history are:
        1. Copy the new file and commit it with message "Update <name> from CPython
            <branch>"
        2. Apply the annotations to the file, if the file executes without 
           failures -> Done
        3. If the file fails, additional by-hand annotations are needed -> Done

        [Done]: Commit the new file with message: "Mark failing tests."
        """
        vprint = self.verbose_print
        self.checkout_test_branch()
        for fname, cpy, rustpy in self.testlib:
            # Read annotations present in the RustPython file:
            collect = DecoCollector(fname)
            vprint(f"Processing {fname}.")
            parse_module(rustpy).visit(collect)
            vprint(f"Got {len(collect.func_decos)} function annotations from {fname}.")

            # Got the annotations, write to RustPython file and commit.
            vprint(f"Writing CPython file for '{fname}' to RustPython test lib.")
            self.testlib.write_to_rustpython(fname, cpy)
            git_add_commit(
                fname,
                self.testlib.rustpython_path, 
                f"Update {fname} from CPython {self.branch}."
            )

            # Apply the annotations to the CPython file.
            vprint(f"Applying annotations to '{fname}'.")
            annotate = DecoAnnotator.from_collector(collect)
            module = parse_module(cpy).visit(annotate)
            self.testlib.write_to_rustpython(fname, module.code)
            git_add(fname, self.testlib.rustpython_path)

            # TODO: Run against tip of rustpython repo and catch new errors.


    def checkout_test_branch(self) -> None:
        """ Checkout a new branch for the tests. Make it somewhat unique by attaching
        a timestamp of the current local date and time.
        """
        trail = repr(datetime.now().timestamp()).replace(".", "")
        branch_name = f"update_stdlib_{trail}"
        try:
            git_checkout(self.testlib.rustpython_path, branch_name)
        except subprocess.CalledProcessError as e:
            print(e)
            self.verbose_print(f"Failed to checkout branch '{branch_name}'. Exiting.")
            exit(1)

    # Any, for now.
    def verbose_print(self, *args: Any, **kwargs: Any) -> None:
        """ Print message if verbose is set. """
        if self.verbose:
            print(*args, **kwargs)

# Result of iterating through TestLib.
TestRow = namedtuple("TestRow", ["filename", "cpython_contents", "rustpython_contents"])

class TestLib:
    """Holds most relevant information."""

    # TODO: make paths properties.
    cpython_path: Path
    rustpython_path: Path
    filenames: List[str]

    def __init__(self, cpy_path: str, rustpython_path: str, tests: List[str]) -> None:
        self.cpython_path = Path(cpy_path) / CPYTHON_LIB / "test/"
        self.rustpython_path = Path(rustpython_path) / RUSTPYTHON_LIB / "test/"
        self.filenames = self._append_py_suffix(tests)
        print(self.filenames)

    def __iter__(self) -> Generator:
        """ Iterate over test files in testlib returning a
        TestRow namedtuple containing the name of the test and the
        contents of it for cpython and rustpython.
        """
        for fname in self.filenames:
            yield TestRow(
                fname,
                self._read(self.cpython_path, fname),
                self._read(self.rustpython_path, fname),
            )

    def write_to_rustpython(self, name: Union[Path, str], content: str) -> None:
        """ Write content to rustpython test file."""
        with open(self.rustpython_path / name, "w") as f:
            f.write(content)

    def _read(self, path: Path, name: Union[Path, str]) -> str:
        """ Read file from path."""
        with open(path / name, "r") as f:
            return f.read()

    def _append_py_suffix(self, names: List[str]) -> List[str]:
        """ Append .py suffix to names if not present."""
        res, suffix = [], ".py"
        for name in names:
            if name.endswith(suffix):
                res.append(name)
            else:
                res.append(f'{name}{suffix}')
        return res