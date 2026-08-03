from pathlib import Path

import pytest

from thaipath.parser import LessonMarkdownParser, MarkdownLessonError


def test_parser_loads_front_matter_and_required_lesson_sections() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson-01.md"))

    assert lesson.id == "lesson-01-greetings-and-polite-particles"
    assert lesson.number == 1
    assert lesson.title == "Greetings and Polite Particles"
    assert lesson.metadata.slug == "greetings-and-polite-particles"
    assert lesson.metadata.tags == ("beginner", "greetings")
    assert lesson.grammar_concepts[0].id == "grammar-01-politeness-particles"
    assert lesson.grammar[0].startswith("Thai statements often end")
    assert lesson.vocabulary[0].id == "vocab-01-sawatdii"
    assert lesson.vocabulary[0].lesson_id == lesson.id
    assert lesson.vocabulary[0].thai == "สวัสดี"
    assert lesson.sentences[0].id == "sentence-01-hello-khrap"
    assert lesson.sentences[0].lesson_id == lesson.id
    assert lesson.sentences[0].english == "Hello."
    assert lesson.exercises[0].id == "exercise-01-hello-khrap"
    assert lesson.exercises[0].answer == "สวัสดีครับ"
    assert lesson.dialogue[0].id == "dialogue-01-a-hello"
    assert lesson.dialogue[0].speaker == "A"
    assert lesson.deck_tag == "lesson_01"


def test_parser_keeps_backward_compatibility_for_legacy_grammar_bullets() -> None:
    markdown = """---
number: 9
title: Legacy Grammar
slug: legacy-grammar
---

# Lesson 9: Legacy Grammar

## Grammar
- A legacy grammar bullet.

## Vocabulary
| Thai | English |
| --- | --- |
| ไป | go |

## Example Sentences
| Thai | English |
| --- | --- |
| ไปครับ | I go. |

## Exercises
| Prompt | Answer |
| --- | --- |
| Say go. | ไป |

## Dialogue
| Speaker | Thai | English |
| --- | --- | --- |
| A | ไปครับ | I go. |
"""

    lesson = LessonMarkdownParser().parse(markdown)

    assert lesson.id == "lesson-09-legacy-grammar"
    assert lesson.grammar == ("A legacy grammar bullet.",)
    assert lesson.grammar_concepts[0].id == "lesson-09-legacy-grammar-grammar-001"
    assert lesson.vocabulary[0].id == "lesson-09-legacy-grammar-vocabulary-001"


def test_parser_accepts_optional_audio_columns(tmp_path: Path) -> None:
    audio = tmp_path / "hello.mp3"
    audio.write_bytes(b"audio")
    markdown = f"""---
number: 9
title: Audio Lesson
slug: audio-lesson
---

# Lesson 9: Audio Lesson

## Grammar
- A grammar bullet.

## Vocabulary
| Thai | English | Audio |
| --- | --- | --- |
| ไป | go | {audio.name} |

## Example Sentences
| Thai | English | Audio |
| --- | --- | --- |
| ไปครับ | I go. | {audio} |

## Exercises
| Prompt | Answer |
| --- | --- |
| Say go. | ไป |

## Dialogue
| Speaker | Thai | English |
| --- | --- | --- |
| A | ไปครับ | I go. |
"""

    lesson = LessonMarkdownParser().parse(markdown, base_dir=tmp_path)

    assert lesson.vocabulary[0].audio == audio
    assert lesson.sentences[0].audio == audio


def test_parser_rejects_missing_front_matter() -> None:
    markdown = "# Lesson 9: Incomplete\n\n## Grammar\n- One note\n"

    with pytest.raises(MarkdownLessonError):
        LessonMarkdownParser().parse(markdown)



def test_parser_loads_canonical_lesson_format() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson001.md"))

    assert lesson.id == "lesson-001-building-your-first-thai-sentences"
    assert lesson.number == 1
    assert lesson.metadata.slug == "building-your-first-thai-sentences"
    assert lesson.metadata.level == "A0"
    assert len(lesson.grammar_concepts) == 2
    assert lesson.grammar_concepts[0].title == "Thai Word Order"
    assert len(lesson.vocabulary) == 15
    assert lesson.vocabulary[0].transliteration == "chan"
    assert lesson.vocabulary[0].note == "Neutral and commonly used in beginner material."
    assert len(lesson.sentences) == 5
    assert len(lesson.exercises) == 5
    assert len(lesson.dialogue) == 2


def test_parser_loads_second_canonical_lesson_fully() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson002.md"))

    assert lesson.id == "lesson-002-questions-negation-and-to-be"
    assert lesson.number == 2
    assert len(lesson.grammar_concepts) == 3
    assert len(lesson.vocabulary) == 9
    assert len(lesson.sentences) == 9
    assert len(lesson.exercises) == 6
    assert len(lesson.dialogue) == 4
