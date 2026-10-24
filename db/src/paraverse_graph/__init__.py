"""
Paraverse graph: the conference softschema knowledge base as a FalkorDB graph, with a
read-only API and browser.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("paraverse-graph")
except PackageNotFoundError:
    __version__ = "0.0.0"
