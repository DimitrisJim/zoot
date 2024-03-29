""" Holds annotations for the given file (namely, skips, expected failures, etc) 
These are then re-applied to the copied file.
"""
import sys
from typing import Optional, TypeVar, List, Set, Tuple, MutableMapping, Type, Union
from libcst import Decorator, FunctionDef, ClassDef, EmptyLine, matchers as m
import libcst

# currently, we only care about skip and expectedFailure of unittest.
_ATTR_NAMES: Set[str] = {"skip", "expectedFailure"}


class NodeMeta:
    """Holds metadata for the decorator."""

    decos: List[Decorator]
    leading_comments: List[EmptyLine]

    def __init__(self, decos: List[Decorator], leading_comments: List[EmptyLine]):
        self.decos = decos
        self.leading_comments = leading_comments


# helpful shorthands
if sys.version_info.minor >= 10:
    from typing import TypeAlias  # type: ignore

    FuncDecos: TypeAlias = MutableMapping[Tuple[str, str], NodeMeta]
    ClassDecos: TypeAlias = MutableMapping[str, NodeMeta]
else:
    FuncDecos = MutableMapping[Tuple[str, str], NodeMeta]  # type: ignore
    ClassDecos = MutableMapping[str, NodeMeta]  # type: ignore
# Seems to do the trick with classmethod
DA = TypeVar("DA", bound="DecoAnnotator")

# TODO: There's traversals we can probably still skip.
class DecoCollector(m.MatcherDecoratableVisitor):
    """Collects all decorators related to RustPython from a given file."""

    # Mapping from function/class names to decorators (@skip or @expectedFailure)
    func_decos: FuncDecos
    cls_decos: ClassDecos
    current_class_name: str
    current_func_name: str

    def __init__(self, fname: Optional[str] = None):
        self.current_class_name = self.current_func_name = ""
        self.fname = fname
        self.func_decos = {}
        self.cls_decos = {}
        super().__init__()

    def info(self) -> str:
        f = f"function decorators = {len(self.func_decos)}"
        c = f"class decorators = {len(self.cls_decos)}" 
        return f"Caught decorators for '{self.fname}': {f}, {c}"

    # visit if in a class which has at least one base class
    # and at least one decorator.
    @m.call_if_inside(m.ClassDef(bases=[m.AtLeastN(n=1)]))
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """Collect decorators for the function. We do not collect all decorated,
        only those that use `unittest.skip` with a message mentioning RustPython and
        those that have a preceding comment mentioning RustPython (usually
        expectedFailure).
        """
        self.current_func_name = node.name.value
        if len(node.decorators) == 0:
            return
        comments = [*_get_lead_comments(node)]
        decos = [d for d in node.decorators if rustpython_deco(d, len(comments) > 0)]
        if decos:
            self.func_decos[
                (self.current_class_name, self.current_func_name)
            ] = NodeMeta(decos, comments)

    def visit_ClassDef(self, node: ClassDef) -> None:
        """Collect decorators for the class. We do not collect all decorated,
        only those that use `unittest.skip` with a message mentioning RustPython.
        """
        if len(node.bases) == 0:
            return
        self.current_class_name = node.name.value
        comments = [*_get_lead_comments(node)]
        decos = [d for d in node.decorators if rustpython_deco(d, len(comments) > 0)]
        if decos:
            self.cls_decos[node.name.value] = NodeMeta(decos, comments)

    @m.call_if_inside(m.SimpleStatementLine())
    def visit_Comment(self, node: libcst.Comment) -> None:
        """Check for any comments that mention RustPython if inside a
        simple statement. Warn about them.

        # TODO: Doesn't catch everything, see test_list.py
        """
        needle = "rustpython"
        fname = f"'{self.fname}'" if self.fname else "the file"
        if _check_comment(node, needle):
            msg = f"Found a comment referencing '{needle}' in {fname}."
            if self.current_class_name:
                msg += f" In class '{self.current_class_name}'."
            if self.current_func_name:
                msg += f" In function '{self.current_func_name}'."
            msg += (
                "\nThis comment could be in a top level block or inside a function"
                " and probably requires manual intervention."
            )
            print(msg, file=sys.stderr)

    def clear(self):
        """Clear all instance data."""
        self.current_class_name = self.current_func_name = ""
        self.func_decos = {}
        self.cls_decos = {}


class DecoAnnotator(m.MatcherDecoratableTransformer):
    """Annotates a copied file with the given decorators."""

    # Mapping from function/class names to decorators (@skip or @expectedFailure)
    func_decos: FuncDecos
    cls_decos: ClassDecos
    class_name: str

    def __init__(self, func_decos: FuncDecos, cls_decos: ClassDecos):
        self.func_decos = func_decos
        self.cls_decos = cls_decos
        self.class_name = ""
        super().__init__()

    @classmethod
    def from_collector(cls: Type[DA], collector: DecoCollector) -> DA:
        return cls(collector.func_decos, collector.cls_decos)

    @staticmethod
    def _add_metadata(
        metadata: NodeMeta, updated_node: Union[FunctionDef, ClassDef]
    ) -> libcst.CSTNode:
        """Adds the given metadata to the given node."""
        if metadata.leading_comments:
            # add our comments *after* the function/class comments.
            # this brings them closer to the decorator and also deals
            # with some weirdness when empty lines are involved.
            comments = [*updated_node.leading_lines, *metadata.leading_comments]
            updated_node = updated_node.with_changes(leading_lines=comments)
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
            return

    def leave_FunctionDef(self, original_node: FunctionDef, updated_node: FunctionDef):
        key = (self.class_name, original_node.name.value)
        if key not in self.func_decos:
            return updated_node
        # add the decorators/leading comments
        return self._add_metadata(self.func_decos[key], updated_node)

    def visit_ClassDef(self, node: ClassDef) -> None:
        # skip if this class doesn't have any base classes.
        if len(node.bases) == 0:
            return
        self.class_name = node.name.value

    def leave_ClassDef(self, _: ClassDef, updated_node: ClassDef):
        if self.class_name not in self.cls_decos:
            return updated_node
        return self._add_metadata(self.cls_decos[self.class_name], updated_node)


# Helpers


def rustpython_deco(deco: Decorator, has_comment: bool = False) -> bool:
    """Match against the class of deco.decorator. If its
    of type Call, call _rustpython_deco_call, otherwise, call _rustpython_deco_attr.

    Unsure how to express this nicely with the `visit_` or match API.
    """
    decorator = deco.decorator
    if isinstance(decorator, libcst.Call):
        return _rustpython_deco_call(decorator)
    # re-check the leading comment, it could be the case that we're sandwiched
    # between two decorators:
    has_comment = has_comment or bool(_get_lead_comments(deco))
    if isinstance(decorator, libcst.Attribute) and has_comment:
        return _rustpython_deco_attr(decorator)

    # Don't handle bare Name cases for now, I don't think they're used (check?)
    return False


def _rustpython_deco_attr(deco_name: libcst.Attribute) -> bool:
    """Covers the cases where the decorator is of the form:

    # TODO: RustPython
    @unittest.expectedFailure
    def ...

    We've already checked the comment if we reach this point, so we just
    check the attribute name.
    """
    # the typed version of Value is indeed BaseExpression, that can contain a Name
    # which has a value attribute. Unsure how to go about it so a TODO for now.
    if deco_name.value.value == "unittest":  # type: ignore
        if deco_name.attr.value in _ATTR_NAMES:
            return True
    return False


def _rustpython_deco_call(deco_call: libcst.Call) -> bool:
    """Covers the cases where the decorator is of the form:

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
    if _rustpython_deco_attr(func):
        for arg in deco_call.args:
            # Similar issue as previous case with `type` comment. Unsure
            # how to rectify so a TODO for now.
            if "rustpython" in arg.value.value.lower():  # type: ignore
                return True
    return False


def _get_lead_comments(
    node: Union[FunctionDef, ClassDef, Decorator]
) -> List[EmptyLine]:
    """Checks if the preceding comment in a function/class mentions RustPython."""
    lines = []
    for line in node.leading_lines:
        if _check_comment(line.comment, "rustpython"):
            lines.append(line)
    return lines


def _check_comment(comment: Optional[libcst.Comment], needle: str) -> bool:
    """Checks if the comment mentions 'needle'."""
    if not comment:
        return False
    return needle in comment.value.lower()
