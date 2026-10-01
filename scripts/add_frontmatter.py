#!/usr/bin/env python3
"""Add ermaozi-compatible frontmatter to Notes/*.md if missing."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

NOTES = Path(__file__).resolve().parent.parent / "Notes"
PREFIX_RE = re.compile(r"^\d+-")
FM_RE = re.compile(r"^---\s*\n.*?\n---\s*\n?", re.S)


def slugify_path(rel: Path) -> str:
    parts = []
    for part in rel.with_suffix("").parts:
        part = PREFIX_RE.sub("", part)
        parts.append(part)
    return "/".join(parts)


def title_of(path: Path) -> str:
    return PREFIX_RE.sub("", path.stem)


def first_paragraph(body: str) -> str:
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            if lines:
                break
            continue
        if s.startswith("#") or s.startswith("```") or s.startswith("!"):
            if lines:
                break
            continue
        # skip list/quote-only lead-ins for cleaner description
        if re.match(r"^[-*+]\s+", s) or re.match(r"^\d+\.\s+", s) or s.startswith(">"):
            s = re.sub(r"^[-*+]\s+", "", s)
            s = re.sub(r"^\d+\.\s+", "", s)
            s = s.lstrip("> ").strip()
            if not s:
                continue
        lines.append(s)
        if sum(len(x) for x in lines) > 80:
            break
    text = " ".join(lines)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*`_]", "", text)
    return (text[:120] + "…") if len(text) > 120 else text


def yaml_quote(s: str) -> str:
    # Always double-quote: descriptions often start with "-" or contain ":".
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def category_tag(rel: Path) -> str:
    if len(rel.parts) >= 2:
        return rel.parts[0]
    return "其它"


def ensure_frontmatter(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        # already has frontmatter; skip unless missing type/permalink
        m = FM_RE.match(text)
        if m and "permalink:" in m.group(0) and "type:" in m.group(0):
            return False

    body = FM_RE.sub("", text, count=1) if text.startswith("---") else text
    body = body.lstrip("\n")
    rel = path.relative_to(NOTES)
    title = title_of(path)
    slug = slugify_path(rel)
    permalink = f"/blog/{slug}/"
    tag = category_tag(rel)
    desc = first_paragraph(body) or title
    # prefer mtime date
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).date().isoformat()

    fm = "\n".join(
        [
            "---",
            f"title: {yaml_quote(title)}",
            f"description: {yaml_quote(desc)}",
            f"permalink: {permalink}",
            f"createTime: {mtime}",
            f"tags: [{yaml_quote(tag)}]",
            "type: post",
            "---",
            "",
        ]
    )
    path.write_text(fm + body, encoding="utf-8")
    return True


def main() -> None:
    if not NOTES.is_dir():
        raise SystemExit(f"missing {NOTES}")
    changed = 0
    for md in sorted(NOTES.rglob("*.md")):
        if md.name in {"_index.md", "index.md", "README.md"}:
            continue
        if ensure_frontmatter(md):
            changed += 1
            print(f"+ {md.relative_to(NOTES)}")
    print(f"updated {changed} files")


if __name__ == "__main__":
    main()
