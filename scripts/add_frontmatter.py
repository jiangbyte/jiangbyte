#!/usr/bin/env python3
"""Ensure Notes/*.md use Hugo/Solitude frontmatter.

Title comes from the filename (Hugo ContentBaseName). Do not write `title`.
`draft` is omitted for published posts; only drafts keep `draft: true`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

NOTES = Path(__file__).resolve().parent.parent / "Notes"
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


def yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


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


def has_key(fm: str, key: str) -> bool:
    return bool(re.search(rf"^{re.escape(key)}:", fm, re.M))


def drop_key(fm: str, key: str) -> str:
    return re.sub(rf"^{re.escape(key)}:\s*.*\n?", "", fm, flags=re.M)


def is_draft_true(fm: str) -> bool:
    m = re.search(r"^draft:\s*(\S+)", fm, re.M)
    if not m:
        return False
    return m.group(1).strip().strip("\"'").lower() in {"true", "yes", "1"}


def ensure_frontmatter(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    fm_body = ""
    body = text
    m = FM_RE.match(text)
    if m:
        fm_body = m.group(1)
        body = text[m.end() :].lstrip("\n")

    rel = path.relative_to(NOTES)
    cat = category_of(rel)
    desc = first_paragraph(body) or path.stem
    date = parse_existing_date(fm_body) or datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc
    ).date().isoformat()
    draft_true = is_draft_true(fm_body)

    fm = fm_body
    fm = drop_key(fm, "title")
    fm = drop_key(fm, "draft")
    fm = drop_key(fm, "permalink")
    fm = drop_key(fm, "createTime")
    fm = drop_key(fm, "type")
    fm = fm.strip() + "\n" if fm.strip() else ""

    lines: list[str] = []
    if not has_key(fm, "date"):
        lines.append(f"date: {date}")
    if not has_key(fm, "description"):
        lines.append(f"description: {yaml_quote(desc)}")
    if not has_key(fm, "categories"):
        lines.append(f"categories: [{yaml_quote(cat)}]")
    if not has_key(fm, "tags"):
        lines.append(f"tags: [{yaml_quote(cat)}]")
    if draft_true:
        lines.append("draft: true")

    if lines:
        fm = (fm.rstrip() + "\n" if fm.strip() else "") + "\n".join(lines) + "\n"

    new_text = "---\n" + fm.strip() + "\n---\n\n" + body
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
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
