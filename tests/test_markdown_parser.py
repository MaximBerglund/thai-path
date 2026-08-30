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


def test_parser_loads_new_official_lessons_fully() -> None:
    expected = {
        "lesson003.md": (3, 7, 8),
        "lesson004.md": (4, 14, 12),
        "lesson005.md": (5, 26, 18),
        "lesson006.md": (6, 29, 12),
        "lesson007.md": (7, 25, 21),
    }

    for filename, (number, vocabulary_count, sentence_count) in expected.items():
        lesson = LessonMarkdownParser().parse_file(Path("lessons") / filename)

        assert lesson.number == number
        assert len(lesson.vocabulary) == vocabulary_count
        assert len(lesson.sentences) == sentence_count
        assert lesson.exercises
        assert lesson.dialogue


def test_parser_includes_lesson_six_function_words_as_vocabulary() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson006.md"))

    assert lesson.vocabulary[0].thai == "อยู่"
    assert lesson.vocabulary[0].english == "to be located / stay"
    assert lesson.vocabulary[0].part_of_speech == "verb"
    assert lesson.vocabulary[-1].thai == "สอง"
    assert lesson.vocabulary[-1].english == "two"


def test_parser_includes_all_lesson_seven_content() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson007.md"))

    assert lesson.vocabulary[0].thai == "มี"
    assert lesson.vocabulary[0].english == "have / there is"
    assert lesson.vocabulary[-1].thai == "อีก"
    assert lesson.vocabulary[-1].english == "another / more"
    assert lesson.sentences[0].thai == "ผมมีรถ"
    assert lesson.sentences[-1].thai == "ผมจะไปประเทศไทยพรุ่งนี้"
    assert len(lesson.dialogue) == 6


def test_parser_includes_all_lesson_eight_content() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson008.md"))

    assert lesson.number == 8
    assert len(lesson.vocabulary) == 35
    assert len(lesson.sentences) == 20
    assert lesson.vocabulary[0].thai == "หนึ่ง"
    assert lesson.vocabulary[-1].thai == "มาก"
    assert lesson.vocabulary[-1].english == "a lot / very"
    assert lesson.sentences[0].thai == "ขอกาแฟสองแก้วครับ"
    assert lesson.sentences[-1].thai == "ทั้งหมดหนึ่งพันห้าร้อยหกสิบเจ็ดบาทครับ"
    assert len(lesson.dialogue) == 8


def test_parser_includes_all_lesson_ninety_supplement_vocabulary() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson90.md"))

    assert lesson.number == 90
    assert len(lesson.vocabulary) == 159
    assert lesson.vocabulary[0].thai == "ผู้หญิง"
    assert lesson.vocabulary[0].english == "woman"
    assert lesson.vocabulary[-1].thai == "ตรงข้ามกับ"
    assert lesson.vocabulary[-1].english == "opposite / across from"
    assert lesson.sentences == ()


def test_parser_includes_all_lesson_nine_content_from_wrapped_markdown() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson009.md"))

    assert lesson.number == 9
    assert len(lesson.vocabulary) == 36
    assert len(lesson.sentences) == 17
    assert lesson.vocabulary[0].thai == "ตอน"
    assert lesson.vocabulary[-1].thai == "เสร็จ"
    assert lesson.sentences[0].thai == "ผมตื่นตอนเช้า"
    assert lesson.sentences[-1].thai == "เรากินข้าวกันตอนเย็น"
    assert len(lesson.dialogue) == 6


def test_parser_includes_all_lesson_ten_content_from_wrapped_markdown() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson010.md"))

    assert lesson.number == 10
    assert len(lesson.vocabulary) == 31
    assert len(lesson.sentences) == 34
    assert lesson.vocabulary[0].thai == "หนาว"
    assert lesson.vocabulary[-1].thai == "ห้องสมุด"
    assert lesson.vocabulary[-1].english == "library"
    assert lesson.sentences[0].thai == "โรงแรมนี้สวยมาก"
    assert lesson.sentences[-1].thai == "คุณอยู่ในห้องไหน"
    assert len(lesson.dialogue) == 8


def test_parser_includes_all_lesson_eleven_content_from_wrapped_markdown() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson011.md"))

    assert lesson.number == 11
    assert len(lesson.vocabulary) == 26
    assert len(lesson.sentences) == 29
    assert lesson.vocabulary[0].thai == "ต้อง"
    assert lesson.vocabulary[-1].thai == "ภาษาไทยกลาง"
    assert lesson.vocabulary[-1].english == "Standard/Central Thai"
    assert lesson.sentences[0].thai == "ผมพูดภาษาไทยได้"
    assert lesson.sentences[-1].thai == "ขอโทษครับ ผมพูดภาษาไทยได้นิดหน่อย"
    assert len(lesson.exercises) == 20
    assert len(lesson.dialogue) == 5


def test_parser_includes_all_lesson_twelve_content_from_wrapped_markdown() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson012.md"))

    assert lesson.number == 12
    assert len(lesson.vocabulary) == 31
    assert len(lesson.sentences) == 37
    assert lesson.vocabulary[0].thai == "ก่อน"
    assert lesson.vocabulary[-1].thai == "ทีหลัง"
    assert lesson.vocabulary[-1].english == "later / afterwards"
    assert lesson.sentences[0].thai == "ผมกินข้าวก่อน"
    assert lesson.sentences[-1].thai == "ถ้าฝนตก ผมไม่ไป"
    assert len(lesson.exercises) == 20
    assert len(lesson.dialogue) == 6


def test_parser_includes_all_lesson_thirteen_content() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson013.md"))

    assert lesson.number == 13
    assert len(lesson.vocabulary) == 23
    assert len(lesson.sentences) == 39
    assert lesson.vocabulary[0].thai == "วันจันทร์"
    assert lesson.vocabulary[-1].thai == "ชั่วโมง"
    assert lesson.vocabulary[-1].english == "hour / duration of an hour"
    assert lesson.sentences[0].thai == "วันนี้วันอะไรครับ"
    assert lesson.sentences[-1].thai == "ประมาณหนึ่งพันบาท"
    assert lesson.sentences[-1].english == "Around 1,000 baht."
    assert len(lesson.exercises) == 25
    assert len(lesson.dialogue) == 6


def test_parser_includes_all_lesson_fourteen_card_content() -> None:
    lesson = LessonMarkdownParser().parse_file(Path("lessons/lesson014.md"))

    assert lesson.number == 14
    assert len(lesson.vocabulary) == 28
    assert len(lesson.sentences) == 44
    assert lesson.vocabulary[0].thai == "ว่า"
    assert lesson.vocabulary[0].english == "that / introduce reported thought or speech"
    assert lesson.vocabulary[-1].thai == "หน้าต่าง"
    assert lesson.vocabulary[-1].english == "window"
    assert lesson.sentences[0].thai == "ผมคิดว่าร้านนี้ดี"
    assert lesson.sentences[0].english == "I think this restaurant is good."
    assert lesson.sentences[-1].thai == "กุญแจอยู่บนโต๊ะ"
    assert lesson.sentences[-1].english == "The key is on the table."
    assert len(lesson.exercises) == 31
    assert len(lesson.dialogue) == 5
