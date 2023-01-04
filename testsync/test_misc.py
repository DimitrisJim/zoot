import argparse
from pathlib import Path
from testsync.helpers import TFile


common = {
    'cpython': Path.home() / 'Devel' / 'cpython', 
    'rustpython': Path.home() / 'Devel' / 'RustPython', 
    'verbose':0, 
    'branch':'3.11',   
}

def test_files_found():
    for filename in ['test_fstring.py', 'test_ast.py', 'test_asyncgen.py']:
        args = argparse.Namespace(**common, testname=filename)
        testfile = TFile(args)

        assert testfile.cpython_path == common['cpython'] / 'Lib'/ 'test/'
        assert testfile.rustpython_path == common['rustpython'] / 'pylib' / 'Lib' / 'test'
        assert testfile.read_pyfile()
        assert testfile.read_rustpyfile()