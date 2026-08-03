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


def test_parser_rejects_missing_front_matter() -> None:
    markdown = "# Lesson 9: Incomplete\n\n## Grammar\n- One note\n"

    with pytest.raises(MarkdownLessonError):
        LessonMarkdownParser().parse(markdown)
