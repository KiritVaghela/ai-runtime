from __future__ import annotations

import pytest

from ai_runtime.tools.builtin import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    GlobTool,
    GrepTool,
    BashTool,
    register_builtin_tools,
)
from ai_runtime.tools import ToolRegistry


@pytest.mark.asyncio
async def test_write_read_edit_roundtrip(tmp_path):
    base = str(tmp_path)
    write = WriteFileTool(base)
    read = ReadFileTool(base)
    edit = EditFileTool(base)

    res = await write.run(None, {"path": "a.txt", "content": "hello world"})
    assert res.success

    r = await read.run(None, {"path": "a.txt"})
    assert r.success and "hello world" in r.output

    e = await edit.run(None, {"path": "a.txt", "old": "world", "new": "there"})
    assert e.success

    r2 = await read.run(None, {"path": "a.txt"})
    assert "hello there" in r2.output


@pytest.mark.asyncio
async def test_glob_and_grep(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.py").write_text("def foo(): pass\n")
    (tmp_path / "sub" / "y.md").write_text("foo bar\n")

    glob = GlobTool(str(tmp_path))
    g = await glob.run(None, {"pattern": "**/*.py"})
    assert any("x.py" in m for m in g.output.splitlines())

    grep = GrepTool(str(tmp_path))
    gr = await grep.run(None, {"pattern": "def foo", "glob": "**/*.py"})
    assert "x.py" in gr.output


@pytest.mark.asyncio
async def test_bash_tool(tmp_path):
    bash = BashTool(cwd=str(tmp_path))
    res = await bash.run(None, {"command": "echo hi"})
    assert res.success and "hi" in res.output


@pytest.mark.asyncio
async def test_register_builtin_tools():
    reg = ToolRegistry()
    register_builtin_tools(reg, base_dir="/tmp")
    names = set(reg._tools.keys())
    assert {"Read", "Write", "Edit", "Glob", "Grep", "Bash"} <= names
