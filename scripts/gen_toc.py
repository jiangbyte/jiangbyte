#!/usr/bin/env python3
"""Generate TOC.md from Notes/ markdown files under REPO_ROOT."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "Notes"
TOC_PATH = REPO_ROOT / "TOC.md"

TITLE = "个人目录笔记"
OTHER_HEADING = "其它"


def collect_notes() -> tuple[dict[str, list[tuple[str, str]]], list[tuple[str, str]]]:
    if not NOTES_DIR.is_dir():
        raise SystemExit(f"Notes directory not found: {NOTES_DIR}")

    # Top-level directories under Notes become TOC sections (sorted by name).
    categories = sorted(
        p.name for p in NOTES_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    sections: dict[str, list[tuple[str, str]]] = {k: [] for k in categories}
    other: list[tuple[str, str]] = []

    for md in sorted(NOTES_DIR.rglob("*.md")):
        if md.name in {"_index.md", "index.md"}:
            continue
        rel = md.relative_to(NOTES_DIR)
        link = f"Notes/{rel.as_posix()}"
        title = md.stem
        if len(rel.parts) == 1:
            other.append((title, link))
            continue
        top = rel.parts[0]
        if top in sections:
            sections[top].append((title, link))
        else:
            other.append((title, link))

    return sections, other


def render_toc(
    sections: dict[str, list[tuple[str, str]]],
    other: list[tuple[str, str]],
) -> str:
    lines = [f"# {TITLE}", ""]
    for cat, items in sections.items():
        if not items:
            continue
        lines.append(f"## {cat}")
        lines.append("")
        for title, link in items:
            lines.append(f"- [{title}]({link})")
        lines.append("")

    if other:
        lines.append(f"## {OTHER_HEADING}")
        lines.append("")
        for title, link in other:
            lines.append(f"- [{title}]({link})")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    sections, other = collect_notes()
    toc = render_toc(sections, other)
    TOC_PATH.write_text(toc, encoding="utf-8")
    n = sum(len(v) for v in sections.values()) + len(other)
    print(f"Wrote {TOC_PATH.relative_to(REPO_ROOT)} ({n} notes)")


if __name__ == "__main__":
    main()
