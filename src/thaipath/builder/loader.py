"""Course and lesson loading services."""

from __future__ import annotations

import re
from pathlib import Path

from thaipath.models import Course, Lesson
from thaipath.parser import LessonMarkdownParser


class LessonLoader:
    """Load Markdown lessons from a directory in lesson-number order."""

    def __init__(self, parser: LessonMarkdownParser | None = None) -> None:
        self._parser = parser or LessonMarkdownParser()

    def load_directory(self, lesson_dir: Path) -> list[Lesson]:
        """Load canonical Markdown lessons from ``lesson_dir`` in lesson-number order.

        The canonical source format uses undashed numeric filenames such as
        ``lesson001.md`` and ``lesson90.md``. If a directory still contains
        older dashed lesson files, canonical files take precedence so each
        lesson is loaded once.
        """

        paths = sorted(
            path
            for path in lesson_dir.glob("lesson*.md")
            if re.fullmatch(r"lesson\d+\.md", path.name)
        )
        if not paths:
            paths = sorted(lesson_dir.glob("*.md"))
        lessons = [self._parser.parse_file(path) for path in paths]
        return sorted(lessons, key=lambda lesson: lesson.number)

    def load_course(self, lesson_dir: Path, *, title: str = "Thai Path", version: str = "0.1.0") -> Course:
        """Load a complete course from ``lesson_dir``."""

        return Course(id="thai-path", title=title, version=version, lessons=tuple(self.load_directory(lesson_dir)))
