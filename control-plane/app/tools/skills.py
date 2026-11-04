"""Skills 目录与 AGENTS.md 约定加载。

同样直接复用 openhands-sdk 的 Skill / AgentContext 触发机制(见架构文档 2.1),
本模块只负责平台侧的"目录"管理:哪些 skills 对哪个租户可见/启用。
"""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


def list_available_skills() -> list[str]:
    """列出平台内置 skills 目录下的所有 skill 文件名(不含扩展名)。"""
    if not SKILLS_DIR.exists():
        return []
    return sorted(p.stem for p in SKILLS_DIR.glob("*.md"))


def load_agents_md(repo_path: Path) -> str | None:
    """按 OpenHands 生态约定,从任务工作目录读取 AGENTS.md(若存在)。"""
    candidate = repo_path / "AGENTS.md"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return None
