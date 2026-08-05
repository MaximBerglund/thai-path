from pathlib import Path
import sqlite3
import zipfile

from thaipath.builder import AnkiDeckBuilder, LessonLoader, SQLiteApkgDeckWriter


def test_loader_creates_course_model() -> None:
    course = LessonLoader().load_course(Path("lessons"))

    assert course.id == "thai-path"
    assert course.title == "Thai Path"
    assert course.version == "0.1.0"
    assert [lesson.number for lesson in course.lessons] == [1, 2, 3, 4, 5]
    assert [lesson.id for lesson in course.lessons] == [
        "lesson-001-building-your-first-thai-sentences",
        "lesson-002-questions-negation-and-to-be",
        "lesson-03-time-and-tense",
        "lesson-04-asking-questions",
        "lesson-05-describing-people-and-things",
    ]
    assert course.lessons[0].metadata.level == "A0"


def test_builder_writes_anki_package(tmp_path: Path) -> None:
    course = LessonLoader().load_course(Path("lessons"))

    output = AnkiDeckBuilder().build(course, tmp_path)

    assert output.name == "ThaiPath.apkg"
    assert output.exists()
    assert output.stat().st_size > 0


def test_builder_writes_two_cards_for_each_generated_note(tmp_path: Path) -> None:
    course = LessonLoader().load_course(Path("lessons"))

    output = AnkiDeckBuilder(writer=SQLiteApkgDeckWriter()).build(course, tmp_path)

    with zipfile.ZipFile(output) as package:
        package.extract("collection.anki2", tmp_path)
    conn = sqlite3.connect(tmp_path / "collection.anki2")
    try:
        notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    finally:
        conn.close()

    expected_notes = sum(len(lesson.grammar_concepts) + len(lesson.vocabulary) + len(lesson.sentences) + len(lesson.dialogue) for lesson in course.lessons)
    assert notes == expected_notes
    assert cards == expected_notes * 2


def test_builder_packages_existing_audio_and_skips_missing_audio(tmp_path: Path) -> None:
    lesson_dir = tmp_path / "lessons"
    lesson_dir.mkdir()
    audio = lesson_dir / "hello.mp3"
    audio.write_bytes(b"audio")
    (lesson_dir / "lesson001.md").write_text(
        """---
lesson: 1
title: Audio Deck
---

# Lesson 1: Audio Deck

## Grammar
- A grammar bullet.

## Vocabulary
| Thai | English | Audio File |
| --- | --- | --- |
| สวัสดี | hello | hello.mp3 |
| ไป | go | missing.mp3 |

## Example Sentences
| Thai | English | Sound |
| --- | --- | --- |
| สวัสดีครับ | Hello. | hello.mp3 |
| ไปครับ | I go. | missing.mp3 |

## Exercises
| Prompt | Answer |
| --- | --- |
| Say hello. | สวัสดี |

## Dialogue
| Speaker | Thai | English |
| --- | --- | --- |
| A | สวัสดีครับ | Hello. |
""",
        encoding="utf-8",
    )

    course = LessonLoader().load_course(lesson_dir)
    output = AnkiDeckBuilder(writer=SQLiteApkgDeckWriter()).build(course, tmp_path)

    with zipfile.ZipFile(output) as package:
        media = package.read("media").decode("utf-8")
        names = package.namelist()

    assert media == '{"0": "hello.mp3"}'
    assert "0" in names


def test_builder_outputs_stable_ids_card_type_and_tags(tmp_path: Path) -> None:
    course = LessonLoader().load_course(Path("lessons"))

    first = AnkiDeckBuilder(writer=SQLiteApkgDeckWriter()).build(course, tmp_path / "first")
    second = AnkiDeckBuilder(writer=SQLiteApkgDeckWriter()).build(course, tmp_path / "second")

    def rows(package_path: Path) -> list[tuple[int, str, str, str]]:
        extract_dir = package_path.parent / "extract"
        extract_dir.mkdir()
        with zipfile.ZipFile(package_path) as package:
            package.extract("collection.anki2", extract_dir)
        conn = sqlite3.connect(extract_dir / "collection.anki2")
        try:
            return conn.execute("SELECT id, guid, tags, flds FROM notes ORDER BY guid").fetchall()
        finally:
            conn.close()

    first_rows = rows(first)
    second_rows = rows(second)

    assert [(row[0], row[1]) for row in first_rows] == [(row[0], row[1]) for row in second_rows]
    first_fields = first_rows[0][3].split("\x1f")
    assert first_fields[6] in {"Vocabulary", "Sentence", "Grammar", "Dialogue"}
    all_tags = " ".join(row[2] for row in first_rows)
    assert "thai-path" in all_tags
    assert "lesson001" in all_tags
    assert "thai-eng" in all_tags
    assert "eng-thai" in all_tags
    assert any(" vocabulary " in f" {row[2]} " for row in first_rows)
    assert any(" sentence " in f" {row[2]} " and " grammar " in f" {row[2]} " for row in first_rows)
    assert any(" dialogue " in f" {row[2]} " for row in first_rows)
