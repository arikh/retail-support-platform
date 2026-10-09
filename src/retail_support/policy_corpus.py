"""The policy files, cut into passages.

A passage is one "## " section of a markdown file: its heading and the text
under it. The files are short questions and answers, so a section is already
one complete thought and is never cut in the middle.

No database and no model here: text in, passages out.
"""

from dataclasses import dataclass
from pathlib import Path

HEADING_MARK = "## "


@dataclass(frozen=True)
class Passage:
    source: str  # the file name
    heading: str
    content: str  # heading and body: what is embedded and shown


def split_markdown(source: str, text: str) -> list[Passage]:
    """One passage per "## " section. Text above the first one (the file's
    title) belongs to no section and is left out."""
    passages: list[Passage] = []
    heading: str | None = None
    body: list[str] = []

    def close_section() -> None:
        if heading is None:
            return
        text_under = "\n".join(body).strip()
        if not text_under:
            raise ValueError(f"empty section in {source}: {heading!r}")
        passages.append(Passage(source, heading, f"{heading}\n{text_under}"))

    for line in text.splitlines():
        if line.startswith(HEADING_MARK):
            close_section()
            heading = line[len(HEADING_MARK) :].strip()
            body = []
        elif heading is not None:
            body.append(line.rstrip())
    close_section()
    return passages


def load_passages(directory: Path) -> list[Passage]:
    """Every passage of every .md file in the directory, in file-name order."""
    passages: list[Passage] = []
    for path in sorted(directory.glob("*.md")):
        passages += split_markdown(path.name, path.read_text(encoding="utf-8"))
    return passages
