"""Tests for native cadquery-ocp and OCP.wasm API compatibility."""

from types import SimpleNamespace

from wormgear.core import ocp_compat

_NATIVE_TOPODS = SimpleNamespace(
    Edge_s=lambda shape: ("native edge", shape),
    Shell_s=lambda shape: ("native shell", shape),
)
_WASM_TOPODS = SimpleNamespace(
    Edge=lambda shape: ("wasm edge", shape),
    Shell=lambda shape: ("wasm shell", shape),
)


def test_downcast_uses_native_static_method(monkeypatch):
    monkeypatch.setattr(ocp_compat, "TopoDS", _NATIVE_TOPODS)

    assert ocp_compat.as_edge("shape") == ("native edge", "shape")
    assert ocp_compat.as_shell("shape") == ("native shell", "shape")


def test_downcast_falls_back_to_wasm_method(monkeypatch):
    monkeypatch.setattr(ocp_compat, "TopoDS", _WASM_TOPODS)

    assert ocp_compat.as_edge("shape") == ("wasm edge", "shape")
    assert ocp_compat.as_shell("shape") == ("wasm shell", "shape")
