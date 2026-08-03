"""Build Anki decks from parsed Thai Path courses."""

from __future__ import annotations

import importlib
import json
import sqlite3
import tempfile
import time
import zipfile
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Protocol

from thaipath.models import Course, Lesson
from thaipath.templates.anki import CSS, SENTENCE_CARD_TEMPLATES, VOCABULARY_CARD_TEMPLATES


@dataclass(frozen=True, slots=True)
class DeckBuildConfig:
    """Configuration for Anki deck generation."""

    deck_id: int = 2_026_080_201
    model_id: int = 2_026_080_202
    deck_name: str = "Thai Path"
    output_file: str = "ThaiPath.apkg"


class DeckWriter(Protocol):
    """Output adapter protocol for writing Anki packages."""

    def write(self, course: Course, output_path: Path, config: DeckBuildConfig) -> None:
        """Write ``course`` to ``output_path``."""


class AnkiDeckBuilder:
    """Create a complete Anki package from a Course model."""

    def __init__(self, config: DeckBuildConfig | None = None, writer: DeckWriter | None = None) -> None:
        self._config = config or DeckBuildConfig()
        self._writer = writer or self._default_writer()

    def build(self, course: Course, output_dir: Path) -> Path:
        """Build ``ThaiPath.apkg`` into ``output_dir`` and return its path."""

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self._config.output_file
        self._writer.write(course, output_path, self._config)
        return output_path

    def _default_writer(self) -> DeckWriter:
        if find_spec("genanki") is not None:
            return GenankiDeckWriter()
        return SQLiteApkgDeckWriter()


@dataclass(frozen=True, slots=True)
class _NoteData:
    thai: str
    english: str
    transliteration: str
    notes: str
    lesson: str
    card_type: str
    source_id: str
    tags: str
    audio: Path | None = None


class GenankiDeckWriter:
    """Anki package writer backed by the external ``genanki`` library."""

    _fields = ["Thai", "English", "Transliteration", "Notes", "Audio", "Lesson", "CardType", "SourceId"]

    def write(self, course: Course, output_path: Path, config: DeckBuildConfig) -> None:
        """Write ``course`` using genanki."""

        genanki = importlib.import_module("genanki")
        vocabulary_model = self._model(genanki, config.model_id, "Thai Path Vocabulary Model", VOCABULARY_CARD_TEMPLATES)
        sentence_model = self._model(genanki, config.model_id + 1, "Thai Path Sentence Model", SENTENCE_CARD_TEMPLATES)
        deck = genanki.Deck(config.deck_id, config.deck_name)
        media_files: list[str] = []
        for lesson in course.lessons:
            self._add_lesson(genanki, deck, {"vocabulary": vocabulary_model, "sentence": sentence_model}, lesson, media_files)
        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(output_path)

    def _model(self, genanki: object, model_id: int, name: str, templates: list[dict[str, str]]) -> object:
        return genanki.Model(
            model_id,
            name,
            fields=[{"name": field} for field in self._fields],
            templates=templates,
            css=CSS,
        )

    def _add_lesson(self, genanki: object, deck: object, models: dict[str, object], lesson: Lesson, media_files: list[str]) -> None:
        for note_data in _collect_notes(lesson):
            audio_field = _audio_field(note_data.audio)
            if audio_field and note_data.audio is not None:
                media_files.append(str(note_data.audio))
            note = genanki.Note(
                model=models[note_data.card_type],
                fields=[
                    note_data.thai,
                    note_data.english,
                    note_data.transliteration,
                    note_data.notes,
                    audio_field,
                    note_data.lesson,
                    note_data.card_type,
                    note_data.source_id,
                ],
                tags=note_data.tags.split(),
            )
            deck.add_note(note)


class SQLiteApkgDeckWriter:
    """Small fallback writer used only when genanki is unavailable locally.

    Production installations use ``GenankiDeckWriter`` through the declared
    dependency. The fallback keeps the test suite useful in constrained offline
    environments without changing the public architecture.
    """

    _fields = ["Thai", "English", "Transliteration", "Notes", "Audio", "Lesson", "CardType", "SourceId"]

    def write(self, course: Course, output_path: Path, config: DeckBuildConfig) -> None:
        notes = [note for lesson in course.lessons for note in _collect_notes(lesson)]
        media = [note.audio for note in notes if note.audio is not None]
        with tempfile.TemporaryDirectory() as temp_dir:
            collection_path = Path(temp_dir) / "collection.anki2"
            self._write_collection(collection_path, notes, config)
            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as package:
                package.write(collection_path, "collection.anki2")
                media_manifest = {}
                for index, media_path in enumerate(media):
                    package.write(media_path, str(index))
                    media_manifest[str(index)] = media_path.name
                package.writestr("media", json.dumps(media_manifest))

    def _write_collection(self, path: Path, notes: list[_NoteData], config: DeckBuildConfig) -> None:
        conn = sqlite3.connect(path)
        try:
            self._create_schema(conn)
            now = int(time.time())
            conn.execute(
                "INSERT INTO col VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (1, now, now, 11, 0, now, self._models_json(config), self._decks_json(config), json.dumps({}), json.dumps({}), json.dumps([])),
            )
            for index, note in enumerate(notes, start=1):
                note_id = config.deck_id * 1000 + index
                fields = "\x1f".join([note.thai, note.english, note.transliteration, note.notes, _audio_field(note.audio), note.lesson, note.card_type, note.source_id])
                conn.execute(
                    "INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (note_id, f"thaipath-{note_id}", self._model_id(config, note.card_type), now, -1, note.tags, fields, note.thai, 0, 0, ""),
                )
                for ordinal, _template in enumerate(_templates_for(note.card_type)):
                    conn.execute(
                        "INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (note_id * 10 + ordinal, note_id, config.deck_id, ordinal, now, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ""),
                    )
            conn.commit()
        finally:
            conn.close()

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE col (id integer primary key, crt integer not null, mod integer not null, scm integer not null, ver integer not null, dty integer not null, models text not null, decks text not null, dconf text not null, tags text not null, conf text not null);
            CREATE TABLE notes (id integer primary key, guid text not null, mid integer not null, mod integer not null, usn integer not null, tags text not null, flds text not null, sfld text not null, csum integer not null, flags integer not null, data text not null);
            CREATE TABLE cards (id integer primary key, nid integer not null, did integer not null, ord integer not null, mod integer not null, usn integer not null, type integer not null, queue integer not null, due integer not null, ivl integer not null, factor integer not null, reps integer not null, lapses integer not null, left integer not null, odue integer not null, odid integer not null, flags integer not null, data text not null);
            CREATE TABLE revlog (id integer primary key, cid integer not null, usn integer not null, ease integer not null, ivl integer not null, lastIvl integer not null, factor integer not null, time integer not null, type integer not null);
            CREATE TABLE graves (usn integer not null, oid integer not null, type integer not null);
            """
        )

    def _models_json(self, config: DeckBuildConfig) -> str:
        vocabulary_model = self._model_json(config.model_id, "Thai Path Vocabulary Model", VOCABULARY_CARD_TEMPLATES)
        sentence_model = self._model_json(config.model_id + 1, "Thai Path Sentence Model", SENTENCE_CARD_TEMPLATES)
        return json.dumps({str(config.model_id): vocabulary_model, str(config.model_id + 1): sentence_model})

    def _model_json(self, model_id: int, name: str, templates: list[dict[str, str]]) -> dict[str, object]:
        return {
            "id": model_id,
            "name": name,
            "type": 0,
            "mod": int(time.time()),
            "usn": -1,
            "css": CSS,
            "flds": [{"name": name, "ord": index} for index, name in enumerate(self._fields)],
            "tmpls": [dict(template, ord=index) for index, template in enumerate(templates)],
            "req": [[index, "all", [0, 1]] for index in range(len(templates))],
        }

    def _model_id(self, config: DeckBuildConfig, card_type: str) -> int:
        return config.model_id if card_type == "vocabulary" else config.model_id + 1

    def _decks_json(self, config: DeckBuildConfig) -> str:
        deck = {"id": config.deck_id, "name": config.deck_name, "mod": int(time.time()), "usn": -1, "collapsed": False, "browserCollapsed": False, "desc": "Generated by Thai Path", "dyn": 0, "conf": 1}
        return json.dumps({str(config.deck_id): deck})


def _collect_notes(lesson: Lesson) -> list[_NoteData]:
    notes: list[_NoteData] = []
    for item in lesson.vocabulary:
        tags = " ".join([lesson.deck_tag, "vocabulary", *lesson.metadata.tags])
        notes.append(_NoteData(item.thai, item.english, item.transliteration or "", item.note or "", str(lesson.number), "vocabulary", item.id, tags, item.audio if item.audio and item.audio.exists() else None))
    for sentence in lesson.sentences:
        tags = " ".join([lesson.deck_tag, "sentence", *lesson.metadata.tags])
        notes.append(
            _NoteData(
                sentence.thai,
                sentence.english,
                sentence.transliteration or "",
                sentence.note or "",
                str(lesson.number),
                "sentence",
                sentence.id,
                tags,
                sentence.audio if sentence.audio and sentence.audio.exists() else None,
            )
        )
    return notes


def _templates_for(card_type: str) -> list[dict[str, str]]:
    return VOCABULARY_CARD_TEMPLATES if card_type == "vocabulary" else SENTENCE_CARD_TEMPLATES


def _audio_field(audio: Path | None) -> str:
    if audio is None:
        return ""
    return f"[sound:{audio.name}]"
