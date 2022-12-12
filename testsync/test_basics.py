# Some *very* coarse tests.
import pytest
import libcst

from testsync.annotate import DecoCollector

# re-use for functions and classes
cases = [
    # [deco, expected count of decos caught]
    # ok cases
    ["""@unittest.skip("TODO: RUSTPYTHON")\n{obj}""", 1],
    ["""# TODO: RUSTPYTHON\n@unittest.expectedFailure\n{obj}""", 1],
    # check that we grab only one deco:
    [
        "@unittest.skipUnless('some condition')\n"
        "# TODO: RUSTPYTHON\n"
        "@unittest.skip('rustpython')\n"
        "{obj}",
        1,
    ],
    [
        # sandwitched, we should grab the expectedFailure
        "@unittest.skipUnless('some condition')\n"
        "# TODO: RUSTPYTHON\n"
        "@unittest.expectedFailure\n"
        "{obj}",
        1,
    ],
    # We currently do not grab these.
    # attrname not one of skip or expectedFailure
    ["""# TODO: RUSTPYTHON\n@unittest.skipIf("TODO: RUSTPYTHON")\n{obj}""", 0],
    # no preceding comment containing "RUSTPYTHON"
    ["""@unittest.expectedFailure\n{obj}""", 0],
    # bare call, not an attribute.
    ["""@skip("TODO: RUSTPYTHON, socket sharing")\n{obj}""", 0],
    # don't handle attributes other than skip and expectedFailure
    ["""@unittest.skipUnless("TODO: RUSTPYTHON, socket sharing")\n{obj}""", 0],
]


def test_func_grabs():
    func = """def _(): pass"""
    for (case, expected_caught) in cases:
        case = case.format(obj=func)
        print(case)
        node = libcst.parse_statement(case)
        c = DecoCollector()
        _ = node.visit(c)
        assert len(c.func_decos) == expected_caught

        # wrap in class and re-do, should get same results
        class_ = ["class _:\n"]
        for line in case.split("\n"):
            class_.append("\t" + line + "\n")
        class_ = "".join(class_)
        node = libcst.parse_statement(class_)
        c = DecoCollector()
        _ = node.visit(c)
        assert len(c.func_decos) == expected_caught


def test_cls_grabs():
    # yup, some cases don't make sense for class (those with expectedFailure)
    # but we'll just re-use the cases, no harm done.
    cls = """class _: pass"""
    for (case, expected_caught) in cases:
        case = case.format(obj=cls)
        print(case)
        node = libcst.parse_statement(case)
        c = DecoCollector()
        _ = node.visit(c)
        assert len(c.cls_decos) == expected_caught
