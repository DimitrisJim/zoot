""" Holds annotations for the given file (namely, skips, expectedfailures, etc. 
These are then re-applied to the copied file.
"""
import typing, sys
import libcst

# helpful shorthand
DecoMapping: typing.TypeAlias = typing.Mapping[str, typing.List[libcst.Decorator]]
# currently, we only care about skip and expectedFailure of unittest.
_ATTR_NAMES: typing.Set[str] = {'skip', 'expectedFailure'}

class DecoCollector(libcst.CSTVisitor):
    """ Collects all decorators related to RustPython from a given file. """

    # Mapping from function/class names to decorators (usually, @skip or @expectedFailure)
    func_decos: DecoMapping
    cls_decos: DecoMapping

    def __init__(self):
        self.func_decos = {}
        self.cls_decos = {}

    def visit_FunctionDef(self, node: libcst.FunctionDef) -> None:
        """ Collect decorators for the function. We do not collect all decorated,
        only those that use `unittest.skip` with a message mentioning RustPython and
        those that have a preceeding comment mentioning RustPython (usually
        expectedFailure).
        """
        decos = [d for d in node.decorators if rustpy_deco(d, _has_lead_comment(node))]
        if decos:
            self.func_decos[node.name.value] = decos

    def visit_ClassDef(self, node: libcst.ClassDef) -> None:
        """ Collect decorators for the class. We do not collect all decorated,
        only those that use `unittest.skip` with a message mentioning RustPython.
        """
        decos = [d for d in node.decorators if rustpy_deco(d, _has_lead_comment(node))]
        if decos:
            self.cls_decos[node.name.value] = decos

    def __repr__(self) -> str:
        """ Just dump out decos. """
        return super().__repr__() + f"({self.func_decos})" + f"({self.cls_decos})"


class DecoAnnotator(libcst.CSTTransformer):
    """ Annotates a copied file with the given decorators. """

    def __init__(self, func_decos: DecoMapping, cls_decos: DecoMapping):
        self.func_decos = func_decos
        self.cls_decos = cls_decos


def rustpy_deco(deco: libcst.Decorator, check_name: bool = False) -> bool:
    """ Match against the class of deco.decorator. If its
    of type Call, call _rustpy_deco_call, otherwise, call _rustpy_deco_attr.
    """
    decorator = deco.decorator
    if isinstance(decorator, libcst.Call):
        return _rustpy_deco_call(decorator)
    # re-check the leading comment, it could be the case that we're sandwiched
    # between two decorators:
    check_name = check_name or _has_lead_comment(deco)
    if isinstance(decorator, libcst.Attribute) and check_name:
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


def _has_lead_comment(node: libcst.CSTNode) -> bool:
    """ Checks if the preceeding comment in a function mentions RustPython. """
    if node.leading_lines:
        for line in node.leading_lines:
            if line.comment and "rustpython" in line.comment.value.lower():
                return True
    return False