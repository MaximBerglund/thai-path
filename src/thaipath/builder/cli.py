"""Command line entry point for building Thai Path outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from thaipath.builder import AnkiDeckBuilder, LessonLoader


def main() -> None:
    """Build the initial Anki deck from Markdown lessons."""

    parser = argparse.ArgumentParser(description="Build ThaiPath.apkg from Markdown lessons.")
    parser.add_argument("--lessons", type=Path, default=Path("lessons"))
    parser.add_argument("--output", type=Path, default=Path("src/thaipath/output"))
    args = parser.parse_args()

    course = LessonLoader().load_course(args.lessons)
    output_path = AnkiDeckBuilder().build(course, args.output)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
