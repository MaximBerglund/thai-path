# Thai Path

Thai Path is a long-term Thai language learning platform. Version `0.1.0` provides the foundation for generating `ThaiPath.apkg` from structured Markdown lesson files.

The project is intentionally designed around a single source of truth: lesson authors edit Markdown files in `lessons/`, and every generated output reads from the same parsed course model.

## Architecture goals

- Keep lesson content independent from output formats.
- Use modern, typed Python with small modules and clear boundaries.
- Parse Markdown lessons into immutable dataclass models with stable IDs.
- Build Anki decks now while leaving room for audio, images, PDFs, and a website later.
- Avoid duplicated data across lessons, cards, future documents, and future web pages.

## Project layout

```text
thai-path/
  src/
    thaipath/
      builder/     # Application services and output builders
      parser/      # Markdown + YAML front matter parsing
      models/      # Typed domain dataclasses
      templates/   # Anki templates and styling
      output/      # Generated artifacts such as ThaiPath.apkg
  lessons/         # Single source of truth lesson Markdown files
  tests/           # Automated parser and builder tests
  docs/            # Supporting architecture notes
  pyproject.toml   # Packaging, dependencies, and test configuration
  README.md        # Project and architecture overview
```

## Architectural layers

### 1. Lesson source layer

The `lessons/` directory contains human-authored Markdown files. Each lesson starts with YAML front matter for metadata such as lesson number, title, slug, level, and tags. The Markdown body contains the required learning sections:

- Grammar
- Vocabulary
- Example sentences
- Exercises
- Dialogue

This source layer is the only place where course content should be authored.

### 2. Parser layer

`src/thaipath/parser/` converts lesson Markdown into structured Python objects. The parser is deliberately constrained: it supports YAML front matter, bullet lists, and Markdown tables that map cleanly into domain models.

Parser responsibilities:

- Read lesson files as UTF-8 Markdown.
- Parse YAML front matter.
- Extract required lesson sections.
- Convert tables and bullets into typed data.
- Validate that each lesson contains the required sections.

The parser should not know anything about Anki, PDFs, websites, or other output formats.

### 3. Domain model layer

`src/thaipath/models/` contains immutable dataclasses for the core Thai Path concepts:

- `Course`
- `Lesson`
- `LessonMetadata`
- `GrammarConcept`
- `VocabularyItem`
- `Sentence`
- `Exercise`
- `DialogueLine`

These models are the internal representation shared by every builder. Every domain object has a stable ID, and vocabulary items and sentences each retain explicit lesson ownership so future review, media, and progress systems can refer to them without conflating their lifecycles. The models include future-ready fields for audio, images, notes, and tags, but Version `0.1.0` does not implement media generation or media attachment.

### 4. Builder layer

`src/thaipath/builder/` contains application services. The loader reads lesson files and creates a `Course`; the Anki builder turns a `Course` into `ThaiPath.apkg`.

Builder responsibilities:

- Load lessons from disk.
- Sort lessons by lesson number.
- Create a complete `Course` model.
- Render output artifacts from the course model.

The current output builder is the Anki deck builder.

### 5. Template layer

`src/thaipath/templates/` stores presentation templates and styling. Version `0.1.0` includes Anki templates for four card types:

1. Vocabulary Thai → English
2. Vocabulary English → Thai
3. Sentence Thai → English
4. Sentence English → Thai

Future PDF and website templates should be added here or in adjacent output-specific template modules without changing the lesson source format.

## Data flow

```text
lessons/*.md
    ↓
LessonMarkdownParser
    ↓
Lesson dataclasses
    ↓
LessonLoader
    ↓
Course dataclass
    ↓
AnkiDeckBuilder
    ↓
src/thaipath/output/ThaiPath.apkg
```

## Version 0.1.0 scope

Implemented:

- Source-layout Python package.
- `pyproject.toml` project metadata.
- Markdown lesson loading.
- YAML front matter parsing.
- Stable IDs for course, lessons, grammar concepts, vocabulary, sentences, exercises, and dialogue lines.
- First-class `GrammarConcept` domain objects with backward-compatible grammar text access.
- Internal `Course` model.
- Anki deck generation using a `genanki` writer when available.
- `ThaiPath.apkg` export.
- Lessons 1 through 7 lesson files.
- Four Anki card templates.
- Optional audio attachment for vocabulary items and example sentences when referenced files exist.
- Parser and builder tests.

Not implemented yet:

- Audio generation.
- Images.
- PDF export.
- Website generation.
- Review lessons.
- Progress tracking.

The architecture leaves room for these features by keeping content, parsing, domain models, templates, and builders separate.

## Build the deck

From a checkout without installing the package:

```bash
PYTHONPATH=src python -m thaipath.builder.cli
```

After installing the project:

```bash
thai-path-build
```

Both commands write:

```text
src/thaipath/output/ThaiPath.apkg
```

## Development

```bash
python -m pip install -e '.[dev]'
pytest
```

If local network access prevents installing dependencies, parser tests and the offline deck-writing fallback can still validate the core architecture with `PYTHONPATH=src python -m pytest`.
