#!/usr/bin/env python3
"""Reject wait claims that lack a concrete wake-up handle nearby."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PREFIX_CHARS = frozenset("上中下高初優劣同相平均次頭末一二三四五六七八九十")
SUFFIX_RE = re.compile(r"價|同|於|級|號|式|比|分|距|差|溫|高|長|量|效|閒|候室|待器|等")
IDIOM_RE = re.compile(
    r"不用等|別等|不等|免等|等一下我(?:先|講|說|補)|等我一下|等下"
    r"|等等我|等等再|等等(?=[，。、,.;；!！?？）)\s]*$)"
)
IDENTIFIER = r"[A-Za-z0-9][A-Za-z0-9_-]{5,}"
HANDLE_RE = re.compile(
    rf"(?:(?:監看|背景|until|Monitor|task[-_ ]?id)[^\n]{{0,40}}\b{IDENTIFIER}\b|ScheduleWakeup"
    rf"|(?-i:herdr\s+agent\s+wait\s+w\d+[A-Z]?:p\d+\b))",
    re.IGNORECASE,
)
SENTENCE_END_RE = re.compile(r"(?<=[。！？!?；;])")
MENTION_RE = re.compile(
    r"(?:「(?:等等|等)」|『(?:等等|等)』|\"(?:等等|等)\"|'(?:等等|等)'|`(?:等等|等)`)"
    r"(?=\s*(?:這|字|的|是|不|也|[，。、,.;；!！?？）)]|$))"
)


def _wait_positions(sentence: str) -> list[int]:
    idioms = [match.span() for match in IDIOM_RE.finditer(sentence)]
    mention_spans = [match.span() for match in MENTION_RE.finditer(sentence)]

    positions: list[int] = []
    for match in re.finditer("等", sentence):
        start, end = match.span()
        if any(lo <= start < hi for lo, hi in idioms):
            continue
        if any(lo <= start < hi for lo, hi in mention_spans):
            continue
        if start and sentence[start - 1] in PREFIX_CHARS:
            continue
        if SUFFIX_RE.match(sentence, end):
            continue
        positions.append(start)
    return positions


def _sentences(text: str) -> list[tuple[int, str]]:
    sentences: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        sentences.extend(
            (line_number, part)
            for part in SENTENCE_END_RE.split(line)
            if part
        )
    return sentences


def find_violations(text: str) -> list[tuple[int, str]]:
    """A handle must be in the wait sentence or its immediately next sentence."""
    sentences = _sentences(text)
    bad_lines: set[int] = set()
    for index, (line_number, sentence) in enumerate(sentences):
        if not _wait_positions(sentence):
            continue
        following = sentences[index + 1][1] if index + 1 < len(sentences) else ""
        if not HANDLE_RE.search(f"{sentence}\n{following}"):
            bad_lines.add(line_number)
    lines = text.splitlines()
    return [(number, lines[number - 1]) for number in sorted(bad_lines)]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: lint_wait_claim.py [message-file]", file=sys.stderr)
        return 2
    text = Path(args[0]).read_text(encoding="utf-8") if args else sys.stdin.read()
    violations = find_violations(text)
    for number, line in violations:
        print(f"line {number}: {line}")
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
