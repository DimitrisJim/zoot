# Some *very* coarse tests.
import pytest
import libcst

from testsync.annotate import DecoCollector, DecoAnnotator

# python case, rustpython_case, wanted_result
cases = [
# Check the most simple of cases:
[
"""
class Test(base_class):
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @unittest.skip("TODO: RUSTPYTHON")
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @unittest.skip("TODO: RUSTPYTHON")
    def test_foo_empty_decos(self):
        pass
""",
],
# Check that decorators are added before any already existing decorators:
[
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    @unittest.skip("TODO: RUSTPYTHON")
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @unittest.skip("TODO: RUSTPYTHON")
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
],
# We dont check for duplicate decorators are not added:
[
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @a_fancy_decorator
    @unittest.skip("TODO: RUSTPYTHON")
    @yet_another_fancy_decorator
    @unittest.skip("TODO: RUSTPYTHON")
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @unittest.skip("TODO: RUSTPYTHON")
    @unittest.skip("TODO: RUSTPYTHON")
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
],
# Grab both unittest.skip and unittest.expectedFailure. For the second, this
# only happens if there's a leading comment mentioning rustpython:
[
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @a_fancy_decorator
    # TODO: RUSTPYTHON
    @unittest.expectedFailure
    @yet_another_fancy_decorator
    @unittest.skip("TODO: RUSTPYTHON")
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    # TODO: RUSTPYTHON
    @unittest.expectedFailure
    @unittest.skip("TODO: RUSTPYTHON")
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
],
# Check that leading comment mentioning rustpython cases the
# unittest.expectedFailure decorator to be added:
[
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    # TODO: RUSTPYTHON the sky has stopped falling.
    @a_fancy_decorator
    @unittest.expectedFailure
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    # TODO: RUSTPYTHON the sky has stopped falling.
    @unittest.expectedFailure
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
],
# While one that doesn't mention rustpython doesn't:
[
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
# comment & expectedFailure are ignored. (maybe not?)
"""
class Test(base_class):
    # TODO: Do not say the word which we mustn't say
    @a_fancy_decorator
    @unittest.expectedFailure
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
],
# A sandwitched comment belong to the decorator below it, if it
# mentions rustpython we should grab it and add the expectedFailure:
[
"""
class Test(base_class):
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    @a_fancy_decorator
    # TODO: RUSTPYTHON the sky is considering its options.
    @unittest.expectedFailure
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
# dunno how it differentiates between a comment belonging to deco
# vs a comment belonging to the function.
"""
class Test(base_class):
    # TODO: RUSTPYTHON the sky is considering its options.
    @unittest.expectedFailure
    @a_fancy_decorator
    @yet_another_fancy_decorator
    def test_foo_empty_decos(self):
        pass
""",
],
# Check that we grab all leading comments:
[
"""
class Test(base_class):
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    # TODO: RUSTPYTHON theres a huge giant space bug here, that's why we skip.
    # Rustpython: Any comments containing rustpython are caught, right?
    # including this, rustpython.
    @unittest.skip("TODO: RUSTPYTHON")
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    # TODO: RUSTPYTHON theres a huge giant space bug here, that's why we skip.
    # Rustpython: Any comments containing rustpython are caught, right?
    # including this, rustpython.
    @unittest.skip("TODO: RUSTPYTHON")
    def test_foo_empty_decos(self):
        pass
""",
],
# Leading comments aren't grabbed if no deco is present:
[
"""
class Test(base_class):
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    # TODO: RUSTPYTHON the sky is legit falling.
    def test_foo_empty_decos(self):
        pass
""",
"""
class Test(base_class):
    def test_foo_empty_decos(self):
        pass
""",
]
]


def test_annotate():
    for (index, (py_case, rust_case, wanted_result)) in enumerate(cases):
        py_node = libcst.parse_module(py_case)
        rust_node = libcst.parse_module(rust_case)
        c = DecoCollector()
        
        # collect decorators/comments
        _ = rust_node.visit(c)
        a = DecoAnnotator.from_collector(c)
        node_result = py_node.visit(a)
        print("Wanted result:\n", wanted_result, "\n\n Result:\n", node_result.code, "\n")
        # print(rust_node)
        # yes, libcst allows this to be done easily since source in == source out
        assert wanted_result == node_result.code