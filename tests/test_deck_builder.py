from pathlib import Path
import sqlite3
import zipfile

from thaipath.builder import AnkiDeckBuilder, LessonLoader, SQLiteApkgDeckWriter


def test_loader_creates_course_model() -> None:
    course = LessonLoader().load_course(Path("lessons"))

    assert course.id == "thai-path"
    assert course.title == "Thai Path"
    assert course.version == "0.1.0"
    assert [lesson.number for lesson in course.lessons] == [1, 2]
    assert "introductions" in course.tags


def test_builder_writes_anki_package(tmp_path: Path) -> None:
    course = LessonLoader().load_course(Path("lessons"))

    output = AnkiDeckBuilder().build(course, tmp_path)

    assert output.name == "ThaiPath.apkg"
    assert output.exists()
    assert output.stat().st_size > 0


def test_builder_writes_two_cards_for_each_vocabulary_and_sentence(tmp_path: Path) -> None:
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

    expected_notes = sum(len(lesson.vocabulary) + len(lesson.sentences) for lesson in course.lessons)
    assert notes == expected_notes
    assert cards == expected_notes * 2
