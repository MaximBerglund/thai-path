"""Parser for Thai Path Markdown lesson files with YAML front matter."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from thaipath.models import DialogueLine, Exercise, GrammarConcept, Lesson, LessonMetadata, Sentence, VocabularyItem

_SECTION_NAMES = {"grammar", "vocabulary", "example sentences", "exercises", "dialogue"}
_SECTION_ALIASES = {
    "function words": "vocabulary",
    "function words and core verbs": "vocabulary",
    "practice": "exercises",
    "mini dialogue": "dialogue",
    "mini dialogue – at a café": "dialogue",
}


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

        return self.parse(path.read_text(encoding="utf-8"), source=str(path), base_dir=path.parent)

    def parse(self, markdown: str, *, source: str = "<memory>", base_dir: Path | None = None) -> Lesson:
        """Parse a lesson from Markdown text."""

        front_matter, body = self._split_front_matter(markdown, source)
        metadata = self._metadata(front_matter, source)
        sections = self._sections(body.splitlines())
        lesson = Lesson(
            metadata=metadata,
            grammar_concepts=tuple(self._grammar(sections.get("grammar", []), metadata.id)),
            vocabulary=tuple(self._vocabulary(sections.get("vocabulary", []), metadata.id, base_dir)),
            sentences=tuple(self._sentences(sections.get("example sentences", []), metadata.id, base_dir)),
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
        if "title" not in data:
            raise MarkdownLessonError(f"{source}: missing front matter keys: title")
        number_key = "lesson" if "lesson" in data else "number"
        if number_key not in data:
            raise MarkdownLessonError(f"{source}: missing front matter keys: lesson")
        tags = data.get("tags", ())
        if isinstance(tags, str):
            tags = (tags,)
        lesson_number = int(data[number_key])
        slug = str(data.get("slug") or self._slugify(str(data["title"])))
        id_width = 3 if number_key == "lesson" and "slug" not in data else 2
        lesson_id = str(data.get("id") or f"lesson-{lesson_number:0{id_width}d}-{slug}")
        return LessonMetadata(
            id=lesson_id,
            number=lesson_number,
            title=str(data["title"]),
            slug=slug,
            level=str(data.get("level") or data.get("difficulty") or "beginner"),
            tags=tuple(str(tag) for tag in tags),
        )

    def _slugify(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
        return slug or "lesson"

    def _sections(self, lines: list[str]) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in lines:
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                name = heading.group(2).strip().lower()
                canonical = _SECTION_ALIASES.get(name, name)
                # Official lessons qualify dialogue headings with their setting
                # (for example, "Mini Dialogue – At a Restaurant").  Treat
                # every such heading as dialogue rather than maintaining an
                # ever-growing list of venue-specific aliases.
                if name.startswith("mini dialogue"):
                    canonical = "dialogue"
                if canonical in _SECTION_NAMES:
                    current = canonical
                    sections.setdefault(current, [])
                    continue
                if current is None:
                    continue
                if len(heading.group(1)) == 1:
                    current = None
                    continue
            if current is not None:
                sections[current].append(line)
        return sections

    def _bullets(self, lines: list[str]) -> list[str]:
        return [line[2:].strip() for line in lines if line.startswith("- ") and line[2:].strip()]

    def _table(self, lines: list[str]) -> list[dict[str, str]]:
        output: list[dict[str, str]] = []
        current: list[str] = []

        def flush() -> None:
            nonlocal current
            if len(current) >= 2:
                headers = [cell.strip().lower() for cell in current[0].strip("|").split("|")]
                for row in current[2:]:
                    cells = [cell.strip() for cell in row.strip("|").split("|")]
                    if len(cells) != len(headers):
                        raise MarkdownLessonError("table row has a different number of cells than its header")
                    output.append(dict(zip(headers, cells, strict=True)))
            current = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                current.append(stripped)
            else:
                flush()
        flush()
        return output

    def _grammar(self, lines: list[str], lesson_id: str) -> list[GrammarConcept]:
        rows = self._table(lines)
        has_subheadings = any(re.match(r"^#{2,6}\s+", line) for line in lines)
        if rows and not has_subheadings:
            return [
                GrammarConcept(
                    id=row.get("id") or self._stable_child_id(lesson_id, "grammar", index),
                    lesson_id=lesson_id,
                    title=row.get("title") or None,
                    explanation=row.get("explanation") or row.get("grammar") or row.get("note") or "",
                )
                for index, row in enumerate(rows, start=1)
            ]
        if has_subheadings:
            return self._prose_grammar(lines, lesson_id)
        bullets = self._bullets(lines)
        if bullets:
            return [
                GrammarConcept(
                    id=self._stable_child_id(lesson_id, "grammar", index),
                    lesson_id=lesson_id,
                    explanation=bullet,
                )
                for index, bullet in enumerate(bullets, start=1)
            ]
        return self._prose_grammar(lines, lesson_id)

    def _prose_grammar(self, lines: list[str], lesson_id: str) -> list[GrammarConcept]:
        concepts: list[GrammarConcept] = []
        title: str | None = None
        body: list[str] = []

        def flush() -> None:
            nonlocal body, title
            explanation = "\n".join(line for line in body if line.strip() and line.strip() != "---").strip()
            if explanation:
                concepts.append(
                    GrammarConcept(
                        id=self._stable_child_id(lesson_id, "grammar", len(concepts) + 1),
                        lesson_id=lesson_id,
                        title=title,
                        explanation=explanation,
                    )
                )
            body = []

        for line in lines:
            heading = re.match(r"^#{2,6}\s+(.+?)\s*$", line)
            if heading:
                flush()
                title = heading.group(1).strip()
            else:
                body.append(line)
        flush()
        return concepts

    def _vocabulary(self, lines: list[str], lesson_id: str, base_dir: Path | None) -> list[VocabularyItem]:
        items = [
            VocabularyItem(
                id=row.get("id") or self._stable_child_id(lesson_id, "vocabulary", index),
                lesson_id=lesson_id,
                thai=row.get("thai", ""),
                english=row.get("english", ""),
                transliteration=row.get("transliteration") or row.get("romanization") or None,
                part_of_speech=row.get("part of speech") or row.get("pos") or None,
                audio=self._optional_media_path(self._audio_value(row), base_dir),
                note=row.get("note") or row.get("notes") or None,
            )
            for index, row in enumerate(self._table(lines), start=1)
        ]
        # Some official vocabulary sections finish with entries written as
        # three-line Markdown blocks instead of table rows:
        #
        #   ขวด
        #   **khùat**
        #   bottle
        #
        # Capture those blocks as first-class vocabulary too, so changing the
        # presentation in the source lesson cannot silently drop deck cards.
        for thai, transliteration, english in self._vocabulary_blocks(lines):
            items.append(
                VocabularyItem(
                    id=self._stable_child_id(lesson_id, "vocabulary", len(items) + 1),
                    lesson_id=lesson_id,
                    thai=thai,
                    english=english,
                    transliteration=transliteration,
                )
            )
        return items

    def _vocabulary_blocks(self, lines: list[str]) -> list[tuple[str, str, str]]:
        """Return non-table Thai/romanization/English vocabulary blocks."""

        output: list[tuple[str, str, str]] = []
        # Blocks before the final table can be illustrative examples embedded
        # in an aliased section (such as "Function Words"), not vocabulary
        # entries. Official prose entries are appended after the tabular list.
        final_table_line = max((index for index, line in enumerate(lines) if line.strip().startswith("|")), default=-1)
        prose_marker = next(
            (index for index, line in enumerate(lines) if line.strip().lower() == "previously learned and reused:"),
            len(lines),
        )
        for index in range(max(final_table_line, prose_marker) + 1, len(lines) - 2):
            thai = lines[index].strip()
            romanization = lines[index + 1].strip()
            english = lines[index + 2].strip()
            if not re.fullmatch(r"[\u0e00-\u0e7f][\u0e00-\u0e7f\s]*", thai):
                continue
            match = re.fullmatch(r"\*\*(.+?)\*\*", romanization)
            if match is None or not english or english.startswith(("#", "|", "**")):
                continue
            output.append((thai, match.group(1).strip(), english))
        return output

    def _sentences(self, lines: list[str], lesson_id: str, base_dir: Path | None) -> list[Sentence]:
        return [
            Sentence(
                id=row.get("id") or self._stable_child_id(lesson_id, "sentence", index),
                lesson_id=lesson_id,
                thai=row.get("thai", ""),
                english=row.get("english", ""),
                transliteration=row.get("transliteration") or row.get("romanization") or None,
                note=row.get("note") or row.get("notes") or None,
                audio=self._optional_media_path(self._audio_value(row), base_dir),
            )
            for index, row in enumerate(self._table(lines), start=1)
        ]

    def _audio_value(self, row: dict[str, str]) -> str | None:
        return row.get("audio") or row.get("audio file") or row.get("audio filename") or row.get("sound")

    def _optional_media_path(self, value: str | None, base_dir: Path | None) -> Path | None:
        if not value:
            return None
        path = Path(value)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        return path

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
        prompts = self._bullets(lines)
        prompts.extend(match.group(1).strip() for line in lines if (match := re.match(r"^\d+\.\s+(.+)$", line.strip())))
        return [
            Exercise(id=self._stable_child_id(lesson_id, "exercise", index), lesson_id=lesson_id, prompt=prompt)
            for index, prompt in enumerate(prompts, start=1)
        ]

    def _dialogue(self, lines: list[str], lesson_id: str) -> list[DialogueLine]:
        rows = self._table(lines)
        if rows:
            return [
                DialogueLine(
                    id=row.get("id") or self._stable_child_id(lesson_id, "dialogue", index),
                    lesson_id=lesson_id,
                    speaker=row.get("speaker", ""),
                    thai=row.get("thai", ""),
                    english=row.get("english", ""),
                    transliteration=row.get("transliteration") or row.get("romanization") or None,
                )
                for index, row in enumerate(rows, start=1)
            ]
        compact = [line.strip() for line in lines if line.strip() and line.strip() != "---"]
        output: list[DialogueLine] = []
        speaker_indexes = [index for index, line in enumerate(compact) if line.endswith(":")]
        for position, speaker_index in enumerate(speaker_indexes):
            next_speaker_index = speaker_indexes[position + 1] if position + 1 < len(speaker_indexes) else len(compact)
            speaker = compact[speaker_index][:-1]
            content = compact[speaker_index + 1 : next_speaker_index]
            if not content:
                continue
            thai = content[0]
            transliteration = content[1] if len(content) >= 3 else None
            english = content[2] if len(content) >= 3 else ""
            if len(content) == 2:
                thai = "\n".join(content)
            output.append(
                DialogueLine(
                    id=self._stable_child_id(lesson_id, "dialogue", len(output) + 1),
                    lesson_id=lesson_id,
                    speaker=speaker,
                    thai=thai,
                    english=english,
                    transliteration=transliteration,
                )
            )
        return output

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
