from pathlib import Path

from thaipath.builder import AnkiDeckBuilder, LessonLoader


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
