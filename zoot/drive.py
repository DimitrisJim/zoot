from pathlib import Path
from typing import Generator, Union, List, Optional, NamedTuple
from datetime import datetime
import subprocess
import argparse

from libcst import parse_module

from zoot.annotate import DecoCollector, DecoAnnotator
from zoot.helpers import git_add, git_add_commit, git_checkout

CPYTHON_LIB = Path("Lib")
RUSTPYTHON_LIB = Path("pylib") / "Lib"


def keep_print():
    old_print = print

    def verbose_print(verbosity):
        if verbosity:
            return old_print
        return lambda *args, **kwargs: None

    return verbose_print

# Per-file, print only if verbose is set.
verbose_print = keep_print()


class Driver:
    def __init__(self, args: argparse.Namespace) -> None:
        globals()["print"] = verbose_print(args.verbose)
        self.branch = args.branch
        self.dry = args.dry
        self.testlib = TestLib(args)

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
        dry = self.dry
        self.checkout_test_branch()
        for testname, cpy, rustpy, libname, libfile in self.testlib:
            print(f"> Processing '{testname}'")
            # handle the library file
            self.write_lib(libname, libfile)

            # Read annotations present in the RustPython file:
            collect = DecoCollector(testname)
            parse_module(rustpy).visit(collect)
            print(collect.info())

            # Got the annotations, write to RustPython file and commit.
            print(f"Writing CPython file for '{testname}' to RustPython test library.")
            if not dry:
                self.testlib.write_to_rustpython(testname, cpy)
                git_add_commit(
                    testname,
                    self.testlib.rustpython_testlib,
                    f"Update {testname} from CPython {self.branch}.",
                )
            # Apply the annotations to the CPython file.
            print(f"Applying annotations to '{testname}'.")
            annotate = DecoAnnotator.from_collector(collect)
            module = parse_module(cpy).visit(annotate)
            if not dry:
                self.testlib.write_to_rustpython(testname, module.code)
                git_add(testname, self.testlib.rustpython_testlib)

            # TODO: Run against tip of rustpython repo and catch new errors.

    def checkout_test_branch(self) -> None:
        """Checkout a new branch for the tests. Make it somewhat unique by attaching
        a timestamp of the current local date and time.
        """
        if self.dry:
            return
        trail = repr(datetime.now().timestamp()).replace(".", "")
        branch_name = f"update_stdlib_{trail}"
        try:
            git_checkout(self.testlib.rustpython_testlib, branch_name)
        except subprocess.CalledProcessError as e:
            print(f"Failed to checkout branch '{branch_name}'. Exiting.")
            raise e

    def write_lib(self, libname: Optional[str], libfile: Optional[str]) -> None:
        """Write the library file to the RustPython test lib."""
        if libname and libfile:
            print(f"Copying library '{libname}' from '{self.testlib.cpython_lib}'.")
            if not self.dry:
                self.testlib.write_to_rustpython(libname, libfile, lib=True)
        else:
            print("Library not found.")


class Row(NamedTuple):
    """A row in the test file."""

    # The name of the test.
    filename: str
    # The test file from cpython.
    cpython_test: str
    # The test file from rustpython.
    rustpython_test: str
    # The name of the library, if applicable
    libname: Optional[str]
    # The library file corresponding to this test file.
    libfile: Optional[str]


class TestLib:
    """Holds most relevant information."""

    cpython_path: Path
    rustpython_path: Path
    filenames: List[str]

    def __init__(self, args: argparse.Namespace) -> None:
        self.cpython_path = Path(args.cpython)
        self.rustpython_path = Path(args.rustpython)
        self.filenames = self._append_py_suffix(args.filenames)
        self.copy_libs = args.copy_libs

    @property
    def cpython_lib(self) -> Path:
        """Path to the Lib directory in the CPython repo."""
        return self.cpython_path / CPYTHON_LIB

    @property
    def rustpython_lib(self) -> Path:
        """Path to the Lib directory in the RustPython repo."""
        return self.rustpython_path / RUSTPYTHON_LIB

    @property
    def cpython_testlib(self) -> Path:
        """Path to the test directory in the CPython repo."""
        return self.cpython_lib / "test"

    @property
    def rustpython_testlib(self) -> Path:
        """Path to the test directory in the RustPython repo."""
        return self.rustpython_lib / "test"

    def __iter__(self) -> Generator:
        """Iterate over test files in testlib returning a
        TestRow namedtuple containing the name of the test and the
        contents of it for cpython and rustpython.
        """
        for fname in self.filenames:
            libname = libfile = None
            if self.copy_libs:
                libname = self.find_library(fname)
                if libname:
                    libfile = self._read(self.cpython_lib, libname)
            yield Row(
                fname,
                self._read(self.cpython_testlib, fname),
                self._read(self.rustpython_testlib, fname),
                libname,
                libfile,
            )

    def write_to_rustpython(
        self, name: Union[Path, str], content: str, *, lib: bool = False
    ) -> None:
        """Write content to rustpython test file."""
        dir = self.rustpython_lib if lib else self.rustpython_testlib
        with open(dir / name, "w") as f:
            f.write(content)

    def find_library(self, name: str) -> Optional[str]:
        """Given a test name, find if a corresponding library for it exists."""
        if not name.startswith("test_"):
            return None
        name = name[5:]
        # see if you can find the library in the stdlib
        if (self.cpython_lib / name).exists():
            if not (self.cpython_lib / name).is_dir():
                return name
            return name
        return None

    def _read(self, path: Path, name: Union[Path, str]) -> str:
        """Read file from path."""
        with open(path / name, "r") as f:
            return f.read()

    def _append_py_suffix(self, names: List[str]) -> List[str]:
        """Append .py suffix to names if not present."""
        res, suffix = [], ".py"
        for name in names:
            if name.endswith(suffix):
                res.append(name)
            else:
                res.append(f"{name}{suffix}")
        return res
