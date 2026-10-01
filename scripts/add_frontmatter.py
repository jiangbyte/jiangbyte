#!/usr/bin/env python3
"""Ensure Notes/*.md use Hugo/Solitude frontmatter."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

NOTES = Path(__file__).resolve().parent.parent / "Notes"
PREFIX_RE = re.compile(r"^\d+-")
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


def yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def title_of(path: Path) -> str:
    return PREFIX_RE.sub("", path.stem)


def category_of(rel: Path) -> str:
    if len(rel.parts) >= 2:
        return rel.parts[0]
    return "其它"


def first_paragraph(body: str) -> str:
    lines: list[str] = []
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
        if re.match(r"^[-*+]\s+", s) or re.match(r"^\d+\.\s+", s) or s.startswith(">"):
            s = re.sub(r"^([-*\+]|\d+\.)\s+", "", s)
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


def parse_existing_date(fm: str) -> str | None:
    for key in ("date", "createTime"):
        m = re.search(rf'^{key}:\s*["\']?([0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})', fm, re.M)
        if m:
            return m.group(1)
    return None


def ensure_frontmatter(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    fm_body = ""
    body = text
    m = FM_RE.match(text)
    if m:
        fm_body = m.group(1)
        body = text[m.end() :].lstrip("\n")

    # Already Hugo-shaped?
    if (
        fm_body
        and re.search(r"^date:", fm_body, re.M)
        and re.search(r"^categories:", fm_body, re.M)
        and not re.search(r"^(permalink|createTime|type):", fm_body, re.M)
    ):
        return False

    rel = path.relative_to(NOTES)
    title = title_of(path)
    cat = category_of(rel)
    desc = first_paragraph(body) or title
    date = parse_existing_date(fm_body) or datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc
    ).date().isoformat()

    fm = "\n".join(
        [
            "---",
            f"title: {yaml_quote(title)}",
            f"date: {date}",
            "draft: false",
            f"description: {yaml_quote(desc)}",
            f"categories: [{yaml_quote(cat)}]",
            f"tags: [{yaml_quote(cat)}]",
            "---",
            "",
        ]
    )
    path.write_text(fm + body, encoding="utf-8")
    return True


def main() -> None:
    if not NOTES.is_dir():
        raise SystemExit(f"missing {NOTES}")
    n = 0
    for md in sorted(NOTES.rglob("*.md")):
        if md.name in {"_index.md", "index.md", "README.md"}:
            continue
        if ensure_frontmatter(md):
            n += 1
            print(f"+ {md.relative_to(NOTES)}")
    print(f"updated {n} files")


if __name__ == "__main__":
    main()
