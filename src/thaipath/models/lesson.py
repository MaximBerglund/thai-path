"""Typed Thai Path domain models.

The model layer is independent of any output format. Lessons remain the single
source of truth while builders can render Anki decks now and PDFs, websites,
images, audio, review lessons, or progress features later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LessonMetadata:
    """YAML front matter that identifies and organizes a lesson."""

    id: str
    number: int
    title: str
    slug: str
    level: str = "beginner"
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GrammarConcept:
    """A grammar concept introduced or reviewed by a lesson."""

    id: str
    lesson_id: str
    explanation: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class VocabularyItem:
    """A vocabulary entry owned by a lesson and usable by card builders."""

    id: str
    lesson_id: str
    thai: str
    english: str
    transliteration: str | None = None
    part_of_speech: str | None = None
    audio: Path | None = None
    image: Path | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Sentence:
    """A sentence pair owned separately from vocabulary entries."""

    id: str
    lesson_id: str
    thai: str
    english: str
    transliteration: str | None = None
    note: str | None = None
    audio: Path | None = None


@dataclass(frozen=True, slots=True)
class Exercise:
    """A lesson exercise retained for future deck/PDF/site outputs."""

    id: str
    lesson_id: str
    prompt: str
    answer: str | None = None


@dataclass(frozen=True, slots=True)
class DialogueLine:
    """One line of dialogue retained for future outputs."""

    id: str
    lesson_id: str
    speaker: str
    thai: str
    english: str
    transliteration: str | None = None
    audio: Path | None = None


@dataclass(frozen=True, slots=True)
class Lesson:
    """A complete Markdown lesson parsed into structured data."""

    metadata: LessonMetadata
    grammar_concepts: tuple[GrammarConcept, ...] = field(default_factory=tuple)
    vocabulary: tuple[VocabularyItem, ...] = field(default_factory=tuple)
    sentences: tuple[Sentence, ...] = field(default_factory=tuple)
    exercises: tuple[Exercise, ...] = field(default_factory=tuple)
    dialogue: tuple[DialogueLine, ...] = field(default_factory=tuple)

    @property
    def id(self) -> str:
        """Stable lesson identifier."""

        return self.metadata.id

    @property
    def number(self) -> int:
        """Lesson number convenience accessor."""

        return self.metadata.number

    @property
    def title(self) -> str:
        """Lesson title convenience accessor."""

        return self.metadata.title

    @property
    def grammar(self) -> tuple[str, ...]:
        """Backward-compatible grammar text accessor."""

        return tuple(concept.explanation for concept in self.grammar_concepts)

    @property
    def deck_tag(self) -> str:
        """Stable Anki tag for cards generated from this lesson."""

        return f"lesson_{self.number:02d}"


@dataclass(frozen=True, slots=True)
class Course:
    """A collection of lessons ready for output builders."""

    id: str
    title: str
    version: str
    lessons: tuple[Lesson, ...]

    @property
    def tags(self) -> tuple[str, ...]:
        """Unique lesson tags in first-seen order."""

        seen: set[str] = set()
        ordered: list[str] = []
        for lesson in self.lessons:
            for tag in lesson.metadata.tags:
                if tag not in seen:
                    seen.add(tag)
                    ordered.append(tag)
        return tuple(ordered)
