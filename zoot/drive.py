from pathlib import Path
from typing import Generator, Union, List
from collections import namedtuple
import argparse

CPY_LIB = Path("Lib")
RUSTPY_LIB = Path("pylib") / "Lib"


class Driver:
    def __init__(self, args: argparse.Namespace) -> None:
        self.verbose = args.verbose
        self.testlib = TestLib(args.cpython, args.rustpython, args.testnames)


# Result of iterating through TestLib.
TestRow = namedtuple("TestRow", ["filename", "cpython_contents", "rustpython_contents"])

class TestLib:
    """Holds most relevant information."""

    # TODO: make paths properties.
    cpython_path: Path
    rustpython_path: Path
    fnames: str

    def __init__(self, cpy_path: str, rustpy_path: str, tests: List[str]) -> None:
        self.cpython_path = Path(cpy_path) / CPY_LIB / "test/"
        self.rustpython_path = Path(rustpy_path) / RUSTPY_LIB / "test/"
        self.filenames = self._append_py_suffix(tests)
        print(self.filenames)

    def iter(self) -> Generator:
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

    def write_rustpyfile(self, name: Union[Path, str], content: str) -> None:
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