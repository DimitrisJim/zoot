""" Holds annotations for the given file (namely, skips, expectedfailures, etc) 
These are then re-applied to the copied file.
"""
import typing, sys
from typing import TypeAlias, TypeVar, Mapping, List, Set, Optional, Tuple
from libcst import (
    Decorator, Comment, FunctionDef, ClassDef, EmptyLine,
    matchers as m
)
import libcst

# currently, we only care about skip and expectedFailure of unittest.
_ATTR_NAMES: Set[str] = {'skip', 'expectedFailure'}


class NodeMeta:
    """ Holds metadata for the decorator. """
    def __init__(self, decos: List[Decorator], leading_comments: List[Comment]):
        self.decos = decos
        self.leading_comments = leading_comments


# helpful shorthands
DecoMapping: TypeAlias = Mapping[Tuple[str, ...], List[NodeMeta]]
Self = TypeVar("Self", bound="DecoAnnotator")

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
        comments = [*_get_lead_comments(node)]
        decos = [d for d in node.decorators if rustpy_deco(d, len(comments) > 0)]
        if decos:
            self.func_decos[(self.class_name, node.name.value)] = NodeMeta(decos, comments)

    def visit_ClassDef(self, node: ClassDef) -> None:
        """ Collect decorators for the class. We do not collect all decorated,
        only those that use `unittest.skip` with a message mentioning RustPython.
        """
        if len(node.bases) == 0:
            return False
        self.class_name = node.name.value
        comments = [*_get_lead_comments(node)]
        decos = [d for d in node.decorators if rustpy_deco(d, len(comments) > 0)]
        if decos:
            self.cls_decos[node.name.value] = NodeMeta(decos, comments)

class DecoAnnotator(m.MatcherDecoratableTransformer):
    """ Annotates a copied file with the given decorators. """
    
    # Mapping from function/class names to decorators (usually, @skip or @expectedFailure)
    func_decos: DecoMapping
    cls_decos: DecoMapping
    stack: Optional[str]

    def __init__(self, func_decos: DecoMapping, cls_decos: DecoMapping):
        self.func_decos = func_decos
        self.cls_decos = cls_decos
        self.class_name = None
        super().__init__()

    @classmethod
    def from_collector(cls: Self, collector: DecoCollector) -> Self:
        return cls(collector.func_decos, collector.cls_decos)

    @staticmethod
    def _add_metadata(metadata: NodeMeta, updated_node: libcst.CSTNode) -> libcst.CSTNode:
        """ Adds the given metadata to the given node. """
        if metadata.leading_comments:
            # add our comments *after* the function/class comments.
            # this brings them closer to the decorator and also deals
            # with some weirdness when empty lines are involved.
            comments = [*updated_node.leading_lines, *metadata.leading_comments]
            updated_node = updated_node.with_changes(
                leading_lines=comments
            )
        decos = [*metadata.decos, *updated_node.decorators]
        return updated_node.with_changes(decorators=decos)

    # visit if in a class which has at least one base class
    # we can't use the same matcher as the collector, because we want to
    # visit the function even if it has no decorators (we might need to add them.)
    @m.call_if_inside(m.ClassDef(bases=[m.AtLeastN(n=1)]))
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        key = (self.class_name, node.name.value)
        # skip if we don't have any decorators for this function.
        if key not in self.func_decos:
            return False
        
    def leave_FunctionDef(self, original_node: FunctionDef, updated_node: FunctionDef) -> libcst.CSTNode:
        key = (self.class_name, original_node.name.value)
        if key not in self.func_decos:
            return updated_node
        # add the decorators/leading comments
        return self._add_metadata(self.func_decos[key], updated_node)
    
    def visit_ClassDef(self, node: ClassDef) -> None:
        # skip if this class doesn't have any base classes.
        if len(node.bases) == 0:
            return False
        self.class_name = node.name.value

    def leave_ClassDef(self, original_node: ClassDef, updated_node: ClassDef) -> libcst.CSTNode:
        if self.class_name not in self.cls_decos:
            return updated_node
        return self._add_metadata(self.cls_decos[self.class_name], updated_node)


# Helpers

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
    has_comment = has_comment or bool(_get_lead_comments(deco))
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


def _get_lead_comments(node: libcst.CSTNode) -> List[EmptyLine]:
    """ Checks if the preceeding comment in a function/class mentions RustPython. """
    rlines = []
    for line in node.leading_lines:
        if line.comment and "rustpython" in line.comment.value.lower():
            rlines.append(line)
    return rlines