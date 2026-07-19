"""
Skills loader for the Yên assistant
====================================

The `artifacts/skills/` folder holds one markdown file per "skill" — a focused
instruction set the LLM should follow while doing a task (e.g. phân khoa triệu
chứng → chuyên khoa đặt lịch). Skills are written in human-readable markdown so
they can be edited without touching code.

This module discovers every `*.md` file in that folder, parses the front-matter
(title + metadata if present), and exposes helpers to:

  * list discovered skills
  * build a single markdown block that can be appended to the system prompt so
    the model "uses" the skill when answering.

Skills are injected AFTER the base system_prompt so they act as task-specific
instructions layered on top of the core persona.

Usage
-----
    from artifacts.skills import load_skills, build_skills_section

    skills = load_skills(ARTIFACTS_DIR / "skills")
    section = build_skills_section(skills)
    system_prompt = base_prompt + "\n\n" + section
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# A skill file may carry optional YAML front-matter between the first two `---`
# lines. Everything after the (optional) front-matter is the skill body.
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass
class Skill:
    name: str                 # slug derived from the filename
    title: str                # first H1 in the body, or the filename
    path: Path
    body: str                 # markdown content (front-matter stripped)
    meta: dict[str, Any]      # parsed front-matter (empty if none)

    @property
    def enabled(self) -> bool:
        # Skill can opt out via front-matter `enabled: false`.
        return bool(self.meta.get("enabled", True))


def _parse_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    """Split optional YAML front-matter from the body.

    Returns (meta, body). If no front-matter is present, meta is empty and the
    body is the original text.
    """
    match = _FRONT_MATTER_RE.match(raw)
    if not match:
        return {}, raw

    import yaml

    fm_text = match.group(1)
    try:
        meta = yaml.safe_load(fm_text) or {}
    except Exception:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    body = raw[match.end():]
    return meta, body


def _slugify(path: Path) -> str:
    stem = path.stem
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stem.strip()).strip("_") or path.stem


def load_skill(path: Path) -> Skill:
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(raw)

    title_match = _TITLE_RE.search(body)
    title = title_match.group(1).strip() if title_match else path.stem

    return Skill(
        name=_slugify(path),
        title=title,
        path=path,
        body=body.strip(),
        meta=meta,
    )


def load_skills(skills_dir: Path) -> list[Skill]:
    """Load every `*.md` skill file from `skills_dir`, sorted by name.

    Missing/invalid directories return an empty list (skills are additive, never
    fatal).
    """
    if not skills_dir or not Path(skills_dir).is_dir():
        return []

    skills: list[Skill] = []
    for path in sorted(Path(skills_dir).glob("*.md"), key=lambda p: p.name):
        try:
            skills.append(load_skill(path))
        except Exception as exc:  # a broken skill file shouldn't crash boot
            print(f"⚠️  skipped skill {path.name}: {type(exc).__name__}: {exc}")
    return skills


def build_skills_section(skills: list[Skill]) -> str:
    """Render enabled skills into a single markdown block for the system prompt.

    Each skill is wrapped in a clearly delimited section so the model can tell
    where one skill ends and another begins.
    """
    enabled = [s for s in skills if s.enabled]
    if not enabled:
        return ""

    parts = ["# KỸ NĂNG HỖ TRỢ (SKILLS)", ""]
    parts.append(
        "Dưới đây là các kỹ năng chuyên biệt. Khi câu hỏi của khách thuộc phạm vi "
        "một kỹ năng, BẮT BUỘC tuân thủ quy trình và luật trong kỹ năng đó."
    )
    parts.append("")

    for skill in enabled:
        parts.append(f"<!-- SKILL START: {skill.name} -->")
        parts.append(skill.body)
        parts.append(f"<!-- SKILL END: {skill.name} -->")
        parts.append("")

    return "\n".join(parts).strip() + "\n"


def build_system_prompt(base_prompt: str, skills_dir: Path) -> str:
    """Convenience: append the skills section to a base system prompt."""
    skills = load_skills(skills_dir)
    section = build_skills_section(skills)
    if not section:
        return base_prompt
    return base_prompt.rstrip() + "\n\n" + section
