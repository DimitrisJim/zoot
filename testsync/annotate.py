""" Holds annotations for the given file (namely, skips, expectedfailures, etc. 
These are then re-applied to the copied file.
"""
import typing, sys
from typing import TypeAlias, Mapping, List, Set, Optional, Tuple
from libcst import (
    Decorator, Comment, FunctionDef, ClassDef,
    CSTVisitor, CSTTransformer, matchers as m
)
import libcst

# currently, we only care about skip and expectedFailure of unittest.
_ATTR_NAMES: Set[str] = {'skip', 'expectedFailure'}


class NodeMeta:
    """ Holds metadata for the decorator. """
    def __init__(self, decos: List[Decorator], leading_comment: Optional[Comment]=None):
        self.decos = decos
        self.leading_comment = leading_comment


# helpful shorthands
DecoMapping: TypeAlias = Mapping[Tuple[str, ...], List[NodeMeta]]

# TODO: There's traversals we can probably still skip.
class DecoCollector(m.MatcherDecoratableVisitor):
    """ Collects all decorators related to RustPython from a given file. """

    # Mapping from function/class names to decorators (usually, @skip or @expectedFailure)
    func_decos: DecoMapping
    cls_decos: DecoMapping
    stack: Optional[str]

    def __init__(self):
        self.class_name = None
        self.func_decos = {}
        self.cls_decos = {}
        super().__init__()

    # visit if in a class which has at least one base class
    # and at least one decorator.
    @m.call_if_inside(m.ClassDef(bases=[m.AtLeastN(n=1)]))
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """ Collect decorators for the function. We do not collect all decorated,
        only those that use `unittest.skip` with a message mentioning RustPython and
        those that have a preceeding comment mentioning RustPython (usually
        expectedFailure).
        """
        if len(node.decorators) == 0:
            return False
        comment = _get_lead_comment(node)
        decos = [d for d in node.decorators if rustpy_deco(d, comment is not None)]
        if decos:
            self.func_decos[(self.class_name, node.name.value)] = NodeMeta(decos, comment)

    def visit_ClassDef(self, node: ClassDef) -> None:
        """ Collect decorators for the class. We do not collect all decorated,
        only those that use `unittest.skip` with a message mentioning RustPython.
        """
        if len(node.bases) == 0:
            return False
        self.class_name = node.name.value
        comment = _get_lead_comment(node)
        decos = [d for d in node.decorators if rustpy_deco(d, comment is not None)]
        if decos:
            self.cls_decos[node.name.value] = NodeMeta(decos, comment)

class DecoAnnotator(m.MatcherDecoratableTransformer):
    """ Annotates a copied file with the given decorators. """
    
    # Mapping from function/class names to decorators (usually, @skip or @expectedFailure)
    func_decos: DecoMapping
    cls_decos: DecoMapping
    stack: Optional[str]

    @classmethod
    def from_collector(cls: "DecoAnnotator", collector: DecoCollector) -> "DecoAnnotator":
        return cls(collector.func_decos, collector.cls_decos)

    def __init__(self, func_decos: DecoMapping, cls_decos: DecoMapping):
        self.func_decos = func_decos
        self.cls_decos = cls_decos
        self.class_name = None
        super().__init__()

    # visit if in a class which has at least one base class
    # we can't use the same matcher as the collector, because we want to
    # visit the function even if it has no decorators (we might need to add them.)
    @m.call_if_inside(m.ClassDef(bases=[m.AtLeastN(n=1)]))
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        key = (self.class_name, node.name.value)
        if key in self.func_decos:
            print("Found function", key)

    def visit_ClassDef(self, node: ClassDef) -> None:
        if len(node.bases) == 0:
            return False
        self.class_name = node.name.value

def rustpy_deco(deco: Decorator, has_comment: bool = False) -> bool:
    """ Match against the class of deco.decorator. If its
    of type Call, call _rustpy_deco_call, otherwise, call _rustpy_deco_attr.

    Unsure how to express this nicely with the `visit_` or match API.
    """
    decorator = deco.decorator
    if isinstance(decorator, libcst.Call):
        return _rustpy_deco_call(decorator)
    # re-check the leading comment, it could be the case that we're sandwiched
    # between two decorators:
    has_comment = has_comment or bool(_get_lead_comment(deco))
    if isinstance(decorator, libcst.Attribute) and has_comment:
        return _rustpy_deco_attr(decorator)
    
    # Don't handle bare Name cases for now, I don't think they're used (check?)
    return False


def _rustpy_deco_attr(deco_name: libcst.Attribute) -> bool:
    """ Covers the cases where the decorator is of the form:
    
    # TODO: RustPython
    @unittest.expectedFailure
    def ...
    
    We've already checked the comment if we reach this point, so we just
    check the attribute name.
    """
    if deco_name.value.value == "unittest":
        if deco_name.attr.value in _ATTR_NAMES:
            return True
    return False


def _rustpy_deco_call(deco_call: libcst.Call) -> bool:
    """ Covers the cases where the decorator is of the form:
    
    @unittest.expectedFailure("todo: RustPython ...")
    def ...

    or:

    @unittest.skip("todo: Rustpython ...")
    def ...
    
    In short, we check the call args to see if a the value
    mentions RustPython.
    """
    func = deco_call.func
    if not isinstance(func, libcst.Attribute):
        # don't handle call cases where the function is a Name, i.e:
        # @skip("todo: RustPython ..."), we don't use these. (check?)
        return False
    
    # Have an Attribute, check if it complies: 
    if _rustpy_deco_attr(func):
            for arg in deco_call.args:
                if "rustpython" in arg.value.value.lower():
                    return True
    return False


def _get_lead_comment(node: libcst.CSTNode) -> Optional[Comment]:
    """ Checks if the preceeding comment in a function mentions RustPython. """
    if node.leading_lines:
        for line in node.leading_lines:
            if line.comment and "rustpython" in line.comment.value.lower():
                return line.comment
    return None