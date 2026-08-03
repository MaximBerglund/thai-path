# Thai Path Architecture

Thai Path uses lesson Markdown files with YAML front matter as the single source of truth. The parser turns those files into typed lesson models with stable IDs, the loader aggregates lessons into a `Course`, and builders render that course into outputs such as Anki packages, future PDFs, and a future website.

## Boundaries

- `src/thaipath/models`: pure dataclasses that describe courses, lessons, first-class grammar concepts, separately owned vocabulary and sentences, and future-ready media hooks.
- `src/thaipath/parser`: Markdown body and YAML front matter parsing and validation.
- `src/thaipath/builder`: application services that load courses and build outputs.
- `src/thaipath/templates`: Anki card templates and styling, with room for future PDF and website templates.
- `lessons`: authored Markdown lesson files.
- `src/thaipath/output`: generated artifacts such as `ThaiPath.apkg`.

## Future design points

The domain models include stable IDs plus optional fields for audio, images, notes, and tags, but builders do not require or generate those assets yet. Review lessons and progress tracking should be added as new domain concepts that reference existing course and lesson data instead of duplicating vocabulary or sentence content.
