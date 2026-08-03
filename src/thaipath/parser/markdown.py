"""Parser for Thai Path Markdown lesson files with YAML front matter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from thaipath.models import DialogueLine, Exercise, GrammarConcept, Lesson, LessonMetadata, Sentence, VocabularyItem

_SECTION_NAMES = {"grammar", "vocabulary", "example sentences", "exercises", "dialogue"}


class MarkdownLessonError(ValueError):
    """Raised when a lesson Markdown file cannot be parsed."""


class LessonMarkdownParser:
    """Parse the project's constrained Markdown lesson format.

    Front matter stores lesson identity and tags. Markdown sections store the
    human-authored learning content. This keeps lessons pleasant to edit while
    allowing builders to consume strongly typed data.
    """

    def parse_file(self, path: Path) -> Lesson:
        """Parse a lesson from ``path``."""

        return self.parse(path.read_text(encoding="utf-8"), source=str(path))

    def parse(self, markdown: str, *, source: str = "<memory>") -> Lesson:
        """Parse a lesson from Markdown text."""

        front_matter, body = self._split_front_matter(markdown, source)
        metadata = self._metadata(front_matter, source)
        sections = self._sections(body.splitlines())
        lesson = Lesson(
            metadata=metadata,
            grammar_concepts=tuple(self._grammar(sections.get("grammar", []), metadata.id)),
            vocabulary=tuple(self._vocabulary(sections.get("vocabulary", []), metadata.id)),
            sentences=tuple(self._sentences(sections.get("example sentences", []), metadata.id)),
            exercises=tuple(self._exercises(sections.get("exercises", []), metadata.id)),
            dialogue=tuple(self._dialogue(sections.get("dialogue", []), metadata.id)),
        )
        self._validate(lesson, source)
        return lesson

    def _split_front_matter(self, markdown: str, source: str) -> tuple[dict[str, Any], str]:
        lines = markdown.splitlines()
        if not lines or lines[0].strip() != "---":
            raise MarkdownLessonError(f"{source}: missing YAML front matter")
        try:
            end = lines[1:].index("---") + 1
        except ValueError as exc:
            raise MarkdownLessonError(f"{source}: unterminated YAML front matter") from exc
        front_matter = self._parse_simple_yaml(lines[1:end], source)
        return front_matter, "\n".join(lines[end + 1 :])

    def _parse_simple_yaml(self, lines: list[str], source: str) -> dict[str, Any]:
        data: dict[str, Any] = {}
        current_list: str | None = None
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if current_list and stripped.startswith("- "):
                data.setdefault(current_list, []).append(stripped[2:].strip().strip('"\''))
                continue
            current_list = None
            if ":" not in stripped:
                raise MarkdownLessonError(f"{source}: invalid front matter line: {line}")
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                data[key] = []
                current_list = key
            elif value.startswith("[") and value.endswith("]"):
                data[key] = [item.strip().strip('"\'') for item in value[1:-1].split(",") if item.strip()]
            elif value.isdigit():
                data[key] = int(value)
            else:
                data[key] = value.strip('"\'')
        return data

    def _metadata(self, data: dict[str, Any], source: str) -> LessonMetadata:
        required = ["number", "title", "slug"]
        missing = [key for key in required if key not in data]
        if missing:
            raise MarkdownLessonError(f"{source}: missing front matter keys: {', '.join(missing)}")
        tags = data.get("tags", ())
        if isinstance(tags, str):
            tags = (tags,)
        lesson_number = int(data["number"])
        slug = str(data["slug"])
        lesson_id = str(data.get("id") or f"lesson-{lesson_number:02d}-{slug}")
        return LessonMetadata(
            id=lesson_id,
            number=lesson_number,
            title=str(data["title"]),
            slug=slug,
            level=str(data.get("level", "beginner")),
            tags=tuple(str(tag) for tag in tags),
        )

    def _sections(self, lines: list[str]) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in lines:
            if line.startswith("## "):
                name = line[3:].strip().lower()
                current = name if name in _SECTION_NAMES else None
                if current is not None:
                    sections[current] = []
                continue
            if current is not None:
                sections[current].append(line)
        return sections

    def _bullets(self, lines: list[str]) -> list[str]:
        return [line[2:].strip() for line in lines if line.startswith("- ") and line[2:].strip()]

    def _table(self, lines: list[str]) -> list[dict[str, str]]:
        rows = [line.strip() for line in lines if line.strip().startswith("|") and line.strip().endswith("|")]
        if len(rows) < 2:
            return []
        headers = [cell.strip().lower() for cell in rows[0].strip("|").split("|")]
        output: list[dict[str, str]] = []
        for row in rows[2:]:
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            if len(cells) != len(headers):
                raise MarkdownLessonError("table row has a different number of cells than its header")
            output.append(dict(zip(headers, cells, strict=True)))
        return output

    def _grammar(self, lines: list[str], lesson_id: str) -> list[GrammarConcept]:
        rows = self._table(lines)
        if rows:
            return [
                GrammarConcept(
                    id=row.get("id") or self._stable_child_id(lesson_id, "grammar", index),
                    lesson_id=lesson_id,
                    title=row.get("title") or None,
                    explanation=row.get("explanation") or row.get("grammar") or row.get("note") or "",
                )
                for index, row in enumerate(rows, start=1)
            ]
        return [
            GrammarConcept(
                id=self._stable_child_id(lesson_id, "grammar", index),
                lesson_id=lesson_id,
                explanation=bullet,
            )
            for index, bullet in enumerate(self._bullets(lines), start=1)
        ]

    def _vocabulary(self, lines: list[str], lesson_id: str) -> list[VocabularyItem]:
        return [
            VocabularyItem(
                id=row.get("id") or self._stable_child_id(lesson_id, "vocabulary", index),
                lesson_id=lesson_id,
                thai=row.get("thai", ""),
                english=row.get("english", ""),
                transliteration=row.get("transliteration") or None,
                part_of_speech=row.get("part of speech") or row.get("pos") or None,
                note=row.get("note") or None,
            )
            for index, row in enumerate(self._table(lines), start=1)
        ]

    def _sentences(self, lines: list[str], lesson_id: str) -> list[Sentence]:
        return [
            Sentence(
                id=row.get("id") or self._stable_child_id(lesson_id, "sentence", index),
                lesson_id=lesson_id,
                thai=row.get("thai", ""),
                english=row.get("english", ""),
                transliteration=row.get("transliteration") or None,
                note=row.get("note") or None,
            )
            for index, row in enumerate(self._table(lines), start=1)
        ]

    def _exercises(self, lines: list[str], lesson_id: str) -> list[Exercise]:
        rows = self._table(lines)
        if rows:
            return [
                Exercise(
                    id=row.get("id") or self._stable_child_id(lesson_id, "exercise", index),
                    lesson_id=lesson_id,
                    prompt=row.get("prompt", ""),
                    answer=row.get("answer") or None,
                )
                for index, row in enumerate(rows, start=1)
            ]
        return [
            Exercise(id=self._stable_child_id(lesson_id, "exercise", index), lesson_id=lesson_id, prompt=bullet)
            for index, bullet in enumerate(self._bullets(lines), start=1)
        ]

    def _dialogue(self, lines: list[str], lesson_id: str) -> list[DialogueLine]:
        return [
            DialogueLine(
                id=row.get("id") or self._stable_child_id(lesson_id, "dialogue", index),
                lesson_id=lesson_id,
                speaker=row.get("speaker", ""),
                thai=row.get("thai", ""),
                english=row.get("english", ""),
                transliteration=row.get("transliteration") or None,
            )
            for index, row in enumerate(self._table(lines), start=1)
        ]

    def _stable_child_id(self, lesson_id: str, kind: str, index: int) -> str:
        return f"{lesson_id}-{kind}-{index:03d}"

    def _validate(self, lesson: Lesson, source: str) -> None:
        missing = []
        if not lesson.grammar_concepts:
            missing.append("grammar")
        if not lesson.vocabulary:
            missing.append("vocabulary")
        if not lesson.sentences:
            missing.append("example sentences")
        if not lesson.exercises:
            missing.append("exercises")
        if not lesson.dialogue:
            missing.append("dialogue")
        if missing:
            raise MarkdownLessonError(f"{source}: missing required section content: {', '.join(missing)}")
