"""Compatibility helpers for cadquery-ocp Python bindings.

Native cadquery-ocp releases expose TopoDS downcasts with a ``_s`` suffix,
while the OCP.wasm build used by the web generator exposes the older names.
"""

from OCP.TopoDS import TopoDS


def _downcast(shape, topology_name: str):
    """Downcast *shape* using either the native or OCP.wasm API spelling."""
    caster = getattr(TopoDS, f"{topology_name}_s", None)
    if caster is None:
        caster = getattr(TopoDS, topology_name)
    return caster(shape)


def as_edge(shape):
    """Return *shape* downcast to ``TopoDS_Edge``."""
    return _downcast(shape, "Edge")


def as_shell(shape):
    """Return *shape* downcast to ``TopoDS_Shell``."""
    return _downcast(shape, "Shell")
