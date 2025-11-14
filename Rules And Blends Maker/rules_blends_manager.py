#!/usr/bin/env python3
"""Small utility to split and rejoin Project Zomboid rule/blend fragments."""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Sequence

BLOCK_START_PATTERN = re.compile(
    r"(?mi)^[ \t]*(alias|rule(?:s)?[ \t-]*entries?|ruleentries?)\b"
)


def normalize_newlines(text: str) -> str:
    """Turn CRLF/CR into LF for easier parsing."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_alias_rule_sections(text: str) -> tuple[list[str], list[str]]:
    """Return the alias and rule-entry blocks that start with expected keywords."""
    normalized = normalize_newlines(text)
    matches = list(BLOCK_START_PATTERN.finditer(normalized))
    alias_blocks: list[str] = []
    rule_blocks: list[str] = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        block = normalized[start:end].rstrip("\n")
        if not block.strip():
            continue
        keyword = match.group(1).lower()
        target = alias_blocks if keyword.startswith("alias") else rule_blocks
        target.append(block)

    return alias_blocks, rule_blocks


def join_blocks(blocks: Sequence[str]) -> str:
    """Join multiple fragments and ensure the result ends with a newline."""
    if not blocks:
        return ""
    merged = "\n\n".join(block.rstrip("\n") for block in blocks)
    return merged.rstrip("\n") + "\n"


def ensure_dir(path: Path) -> None:
    """Create directories when needed."""
    path.mkdir(parents=True, exist_ok=True)


def resolve_source(source: str, original_dir: Path) -> Path:
    """Try to resolve the input into an existing file path."""
    candidate = Path(source)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    alternatives = [
        Path.cwd() / source,
        original_dir / source,
    ]
    if not candidate.suffix:
        alternatives.extend(
            original_dir / f"{source}{suffix}" for suffix in (".txt", ".text", ".blend", ".blends")
        )

    for candidate in alternatives:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Could not find '{source}' in {original_dir} or the current folder.")


def write_text(path: Path, text: str, encoding: str) -> None:
    """Write using LF line endings so files stay consistent across platforms."""
    ensure_dir(path.parent)
    with path.open("w", encoding=encoding, newline="\n") as handle:
        handle.write(text)


def read_text(path: Path, encoding: str) -> str:
    """Read text and normalize line endings."""
    return normalize_newlines(path.read_text(encoding=encoding))


def classify_fragment(filename: Path, encoding: str) -> str | None:
    """Simple heuristics to decide if a file contains aliases or rule entries."""
    stem = filename.stem.lower()
    alias_endings = ("_alias", "_aliases")
    rule_endings = ("_rules_entry", "_rules_entries", "_rule_entry", "_ruleentries")

    for candidate in alias_endings:
        if stem.endswith(candidate):
            return "alias"
    for candidate in rule_endings:
        if stem.endswith(candidate):
            return "rule"
    if "alias" in stem and "rule" not in stem:
        return "alias"
    if "rule" in stem:
        return "rule"

    try:
        first_line = read_text(filename, encoding).strip()
    except OSError:
        return None

    if first_line.lower().startswith("alias"):
        return "alias"
    if "rule" in first_line.lower():
        return "rule"
    return None


def build_master_content(
    fragments: Sequence[str], prefix: str, suffix: str
) -> str:
    """Wrap the concatenated fragments with the provided prefix and suffix."""
    parts: list[str] = []
    if prefix:
        parts.append(prefix.rstrip("\n"))
    if fragments:
        parts.append("\n\n".join(fragment.rstrip("\n") for fragment in fragments))
    if suffix:
        parts.append(suffix.rstrip("\n"))

    if not parts:
        return ""

    return "\n".join(parts).rstrip() + "\n"


def handle_prep(args: argparse.Namespace) -> None:
    original_dir = Path(args.original_dir)
    alias_dir = Path(args.alias_dir)
    source = resolve_source(args.source, original_dir)
    logging.info("Preparing fragments from %s", source)

    alias_blocks, rule_blocks = split_alias_rule_sections(read_text(source, args.encoding))
    base = source.stem
    alias_path = alias_dir / f"{base}{args.alias_suffix}"
    rule_path = alias_dir / f"{base}{args.rules_suffix}"

    if not args.dry_run:
        ensure_dir(alias_dir)

    if alias_blocks:
        alias_text = join_blocks(alias_blocks)
        if not args.dry_run:
            write_text(alias_path, alias_text, args.encoding)
        logging.info("Extracted %d alias section(s) → %s", len(alias_blocks), alias_path)
    else:
        logging.info("No alias sections found in %s", source)

    if rule_blocks:
        rule_text = join_blocks(rule_blocks)
        if not args.dry_run:
            write_text(rule_path, rule_text, args.encoding)
        logging.info("Extracted %d rule entry section(s) → %s", len(rule_blocks), rule_path)
    else:
        logging.info("No rule entry sections found in %s", source)

    if args.dry_run:
        logging.info("Dry run mode, no files were written.")


def handle_compile(args: argparse.Namespace) -> None:
    fragment_dir = Path(args.fragment_dir)
    if not fragment_dir.exists():
        logging.error("Fragment directory %s does not exist.", fragment_dir)
        raise SystemExit(1)

    alias_fragments: list[str] = []
    rule_fragments: list[str] = []

    fragment_files = sorted(
        (file for file in fragment_dir.iterdir() if file.is_file() and not file.name.startswith(".")),
        key=lambda path: path.name.lower(),
    )

    for fragment in fragment_files:
        kind = classify_fragment(fragment, args.encoding)
        if not kind:
            logging.debug("Skipping %s (could not determine type)", fragment)
            continue
        content = read_text(fragment, args.encoding).strip("\n")
        if not content.strip():
            logging.debug("Skipping %s (empty)", fragment)
            continue
        collector = alias_fragments if kind == "alias" else rule_fragments
        collector.append(content)

    if not alias_fragments:
        logging.warning("No alias fragments found in %s", fragment_dir)
    if not rule_fragments:
        logging.warning("No rule fragments found in %s", fragment_dir)

    blends_output = build_master_content(alias_fragments, args.blends_prefix, args.blends_suffix)
    rules_output = build_master_content(rule_fragments, args.rules_prefix, args.rules_suffix)

    write_text(Path(args.master_blends), blends_output, args.encoding)
    logging.info("Wrote %s (%d fragment(s))", args.master_blends, len(alias_fragments))

    write_text(Path(args.master_rules), rules_output, args.encoding)
    logging.info("Wrote %s (%d fragment(s))", args.master_rules, len(rule_fragments))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Project Zomboid alias/rule fragments."
    )
    subparsers = parser.add_subparsers(dest="command")

    prep = subparsers.add_parser("prep", help="Split an original text into alias/rule fragments.")
    prep.add_argument("source", help="Path to the original rules/blends file (relative or absolute).")
    prep.add_argument(
        "--original-dir",
        default="Original",
        help="Folder that hosts the original files (defaults to %(default)s).",
    )
    prep.add_argument(
        "--alias-dir",
        default="Alias and Rule Entrys",
        help="Directory to save alias/rule fragments (defaults to %(default)s).",
    )
    prep.add_argument(
        "--alias-suffix",
        default="_alias.txt",
        help="Suffix to apply to alias fragments (defaults to %(default)s).",
    )
    prep.add_argument(
        "--rules-suffix",
        default="_rules_entry.txt",
        help="Suffix for the rule-entry fragments (defaults to %(default)s).",
    )
    prep.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding to read/write text files (defaults to %(default)s).",
    )
    prep.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without touching the filesystem.",
    )

    compile_parser = subparsers.add_parser("compile", help="Reassemble fragments into master files.")
    compile_parser.add_argument(
        "--fragment-dir",
        default="Alias and Rule Entrys",
        help="Where the prep step drops alias/rule fragments.",
    )
    compile_parser.add_argument(
        "--master-rules",
        default="MasterRules.txt",
        help="Path for the compiled rules file.",
    )
    compile_parser.add_argument(
        "--master-blends",
        default="MasterBlends.txt",
        help="Path for the compiled blends file.",
    )
    compile_parser.add_argument(
        "--rules-prefix",
        default="Rules\n{\n",
        help="Header prepended to the master rules file.",
    )
    compile_parser.add_argument(
        "--rules-suffix",
        default="}\n",
        help="Footer appended to the master rules file.",
    )
    compile_parser.add_argument(
        "--blends-prefix",
        default="Blends\n{\n",
        help="Header prepended to the master blends file.",
    )
    compile_parser.add_argument(
        "--blends-suffix",
        default="}\n",
        help="Footer appended to the master blends file.",
    )
    compile_parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding to read/write text files (defaults to %(default)s).",
    )

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        raise SystemExit(1)

    if args.command == "prep":
        handle_prep(args)
    elif args.command == "compile":
        handle_compile(args)
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
