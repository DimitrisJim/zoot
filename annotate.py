""" Holds annotations for the given file (namely, skips, expectedfailures, etc. 
These are then re-applied to the copied file.
"""
import typing
import libcst


class DecoCollector(libcst.CSTVisitor):
    """ Collects all decorators from a given file. """

    # Mapping from function names to decorators (usually, @skip or @expectedFailure)
    decos: typing.Mapping[str, libcst.Decorator]

    def __init__(self):
        self.decos = {}



class DecoAnnotator(libcst.CSTTransformer):
    """ Annotates a copied file with the given decorators. """

    def __init__(self, decos: typing.Mapping[str, libcst.Decorator]):
        self.decos = decos
        