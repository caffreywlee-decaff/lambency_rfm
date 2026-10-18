"""server.py 의 mcp 임포트 fallback — 가짜 mcp 모듈로 네 경우(1.x · 2.x · 둘 다 · 없음)를 만든다. 실제 mcp 설치와 무관하게 돈다.
(2026-10-18, byteme 세션의 bytemescan 시험 꼴을 따름.)"""
import importlib
import pathlib
import sys
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


class _Stub:
    def __init__(self, name): self.name = name
    def tool(self):
        return lambda f: f
    def run(self): pass


def _install(monkeypatch, *, v1: bool, v2: bool):
    for k in [m for m in sys.modules if m == "mcp" or m.startswith("mcp.")]:
        monkeypatch.delitem(sys.modules, k, raising=False)
    monkeypatch.delitem(sys.modules, "lambency_rfm.server", raising=False)
    if not (v1 or v2):
        monkeypatch.setitem(sys.modules, "mcp", None)          # import mcp.* → ImportError
        return
    mcp = types.ModuleType("mcp"); server = types.ModuleType("mcp.server"); mcp.server = server
    monkeypatch.setitem(sys.modules, "mcp", mcp); monkeypatch.setitem(sys.modules, "mcp.server", server)
    if v1:
        fast = types.ModuleType("mcp.server.fastmcp"); fast.FastMCP = type("FastMCP", (_Stub,), {}); server.fastmcp = fast
        monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fast)
    if v2:
        server.MCPServer = type("MCPServer", (_Stub,), {})


@pytest.mark.parametrize("v1,v2,want", [(True, False, "FastMCP"), (False, True, "MCPServer"), (True, True, "FastMCP")])
def test_picks_available_class(monkeypatch, v1, v2, want):
    _install(monkeypatch, v1=v1, v2=v2)
    srv = importlib.import_module("lambency_rfm.server")
    assert type(srv.mcp).__name__ == want and srv.mcp.name == "lambency_rfm"
    assert all(callable(getattr(srv, t)) for t in ("rfm_score", "rfm_migrate", "rfm_params"))


def test_no_mcp_exits_with_hint(monkeypatch):
    _install(monkeypatch, v1=False, v2=False)
    with pytest.raises(SystemExit) as e:
        importlib.import_module("lambency_rfm.server")
    assert "pip install" in str(e.value)
