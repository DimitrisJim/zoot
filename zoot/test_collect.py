# Some *very* coarse tests.
from io import StringIO
from contextlib import redirect_stderr

import libcst
from zoot.annotate import DecoCollector

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
        # sandwiched, we should grab the expectedFailure
        "@unittest.skipUnless('some condition')\n"
        "# TODO: RUSTPYTHON\n"
        "@unittest.expectedFailure\n"
        "{obj}",
        1,
    ],
    # We currently do not grab these.
    # attribute name not one of skip or expectedFailure
    ["""# TODO: RUSTPYTHON\n@unittest.skipIf("TODO: RUSTPYTHON")\n{obj}""", 0],
    # no preceding comment containing "RUSTPYTHON"
    ["""@unittest.expectedFailure\n{obj}""", 0],
    # bare call, not an attribute.
    ["""@skip("TODO: RUSTPYTHON, socket sharing")\n{obj}""", 0],
    # don't handle attributes other than skip and expectedFailure
    ["""@unittest.skipUnless("TODO: RUSTPYTHON, socket sharing")\n{obj}""", 0],
]


def _wrap_in_class(case: str, cls_name: str, bases=None):
    cls_ = f"class {cls_name}"
    cls_ += f"({bases}):\n" if bases else ":\n"
    for line in case.split("\n"):
        cls_ += "\t" + line + "\n"
    return cls_


def test_func_grabs():
    for (index, (case, expected_caught)) in enumerate(cases):
        func = f"""def func_{index}(): pass"""
        case = case.format(obj=func)
        class_ = _wrap_in_class(case, f"cls_{index}", bases="some_base")
        print(class_)
        node = libcst.parse_statement(class_)
        c = DecoCollector()
        _ = node.visit(c)
        assert len(c.func_decos) == expected_caught
        # check that the names are correct:
        for cls_name, func_name in c.func_decos:
            assert cls_name == f"cls_{index}"
            assert func_name == f"func_{index}"

        # check that we dont get anything if no base classes:]
        class_ = _wrap_in_class(case, f"cls_{index}")
        node = libcst.parse_statement(class_)
        c = DecoCollector()
        _ = node.visit(c)
        assert len(c.func_decos) == 0


def test_cls_grabs():
    # yup, some cases don't make sense for class (those with expectedFailure)
    # but we'll just re-use the cases, no harm done.
    cls = """class _(some_base): pass"""
    for (case, expected_caught) in cases:
        case = case.format(obj=cls)
        print(case)
        node = libcst.parse_statement(case)
        c = DecoCollector()
        _ = node.visit(c)
        assert len(c.cls_decos) == expected_caught


# Check that comments found in the body of a function are reported:
comment_cases = [
# Should just report the presence of it, notifying folks that
# there's some additional stuff to do.
["""
class C(T):
    def f(self):
        a = 1
        some_stuff()
        # TODO: RUSTPYTHON
        # A GIANT HACK
        SOME_HACK_WOW()
""",
(
    "Found a comment referencing 'rustpython' in 'test'. In class 'C'. In function 'f'."
    "\nThis comment could be in a top level block or inside a function"
    " and probably requires manual intervention."
)
],
[
"""
class C(T):

    # Shouldn't report anything.
    # TODO: RUSTPYTHON
    @unittest.expectedFailure
    def f(self):
        a = 1
        some_stuff()
""",
""
]
]

def test_func_comments():
    for stmt, expected in comment_cases:
        node = libcst.parse_statement(stmt)
        c = DecoCollector("test")
        s = StringIO()
        with redirect_stderr(s):
            _ = node.visit(c)
        assert s.getvalue().strip() == expected
        