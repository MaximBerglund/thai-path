"""Anki note templates and shared styling."""

CSS = """
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 22px;
  line-height: 1.45;
  color: #1f2937;
  background: #fffaf0;
  text-align: center;
}
.thai { font-size: 40px; color: #9a3412; margin: 0.75rem; }
.english { font-size: 30px; color: #1e3a8a; margin: 0.75rem; }
.transliteration { color: #64748b; font-style: italic; }
.audio { margin: 0.75rem; }
.notes { border-top: 1px solid #fdba74; margin-top: 1rem; padding-top: 1rem; }
.label { color: #9ca3af; font-size: 14px; text-transform: uppercase; letter-spacing: 0.08em; }
"""

CARD_TEMPLATES = [
    {
        "name": "Thai → English",
        "qfmt": '<div class="label">{{CardType}} · Thai → English</div><div class="thai">{{Thai}}</div><div class="audio">{{Audio}}</div><div class="transliteration">{{Transliteration}}</div>',
        "afmt": '{{FrontSide}}<hr id="answer"><div class="english">{{English}}</div><div class="notes">{{Notes}}</div>',
    },
    {
        "name": "English → Thai",
        "qfmt": '<div class="label">{{CardType}} · English → Thai</div><div class="english">{{English}}</div>',
        "afmt": '{{FrontSide}}<hr id="answer"><div class="thai">{{Thai}}</div><div class="audio">{{Audio}}</div><div class="transliteration">{{Transliteration}}</div><div class="notes">{{Notes}}</div>',
    },
]

VOCABULARY_CARD_TEMPLATES = CARD_TEMPLATES
SENTENCE_CARD_TEMPLATES = CARD_TEMPLATES
