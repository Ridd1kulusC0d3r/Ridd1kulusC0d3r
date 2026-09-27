#!/usr/bin/env python3
"""Regenerate localized profile READMEs from canonical README.md."""

from __future__ import annotations

import os
import re
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "README.md"
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

LANGUAGES = {
    "pt-BR": {"name": "Brazilian Portuguese", "path": ROOT / "README.pt-BR.md"},
    "es": {"name": "Spanish", "path": ROOT / "README.es.md"},
    "ru": {"name": "Russian", "path": ROOT / "README.ru.md"},
}

SELECTOR_RE = re.compile(
    r"<!-- LANGUAGE_SELECTOR_START -->.*?<!-- LANGUAGE_SELECTOR_END -->\s*",
    re.DOTALL,
)


def language_selector(active: str) -> str:
    items = [
        ("en", "English", "./README.md"),
        ("pt-BR", "Português", "./README.pt-BR.md"),
        ("es", "Español", "./README.es.md"),
        ("ru", "Русский", "./README.ru.md"),
    ]
    rendered = []
    for code, label, href in items:
        if code == active:
            rendered.append(f"    <strong>{label}</strong>")
        else:
            rendered.append(f'    <a href="{href}">{label}</a>')

    return (
        "<!-- LANGUAGE_SELECTOR_START -->\n"
        '<p align="center">\n'
        "  <samp>\n"
        + " ·\n".join(rendered)
        + "\n  </samp>\n"
        "</p>\n"
        "<!-- LANGUAGE_SELECTOR_END -->\n\n"
    )


def clean_model_output(text: str) -> str:
    text = text.strip()
    fence = chr(96) * 3
    if text.startswith(fence + "markdown") and text.endswith(fence):
        text = text[len(fence + "markdown") : -len(fence)].strip()
    elif text.startswith(fence) and text.endswith(fence):
        text = text[len(fence) : -len(fence)].strip()
    return text


def translate(client: OpenAI, source: str, target_language: str) -> str:
    instructions = f"""
Translate the supplied GitHub profile README from English into {target_language}.

Requirements:
- Return ONLY the translated README content. Do not explain or summarize.
- Preserve Markdown and HTML structure so it renders correctly on GitHub.
- Preserve every URL, repository path, username, email address, image URL, HTML tag,
  table structure, code fence, Mermaid syntax, and explicit anchor such as <a id="about"></a>.
- Translate visible prose, headings, navigation labels, table labels, statuses, role descriptions,
  and <summary> text.
- Preserve proper names of institutions and brands.
- Keep established cybersecurity terms and acronyms such as OSINT, SOCMINT,
  Cyber Threat Intelligence, Detection Engineering, Digital Investigation,
  Threat Modeling, Behavioral OSINT, SOC, CTI, and certification names in English
  where that is natural professional usage.
- Do not change dates, durations, credentials, links, or factual meaning.
- Do not add claims absent from the source.
""".strip()

    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=source,
    )
    translated = clean_model_output(response.output_text)
    if not translated or '<div align="center">' not in translated:
        raise RuntimeError(f"Unexpected translation output for {target_language}")
    return translated


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")

    source = SOURCE.read_text(encoding="utf-8")
    source_body = SELECTOR_RE.sub("", source, count=1).lstrip()
    client = OpenAI()

    for code, spec in LANGUAGES.items():
        translated = translate(client, source_body, spec["name"])
        output = (
            "<!-- AUTO-GENERATED FROM README.md. DO NOT EDIT DIRECTLY. -->\n"
            + language_selector(code)
            + translated.rstrip()
            + "\n"
        )
        spec["path"].write_text(output, encoding="utf-8")
        print(f"updated {spec['path'].name} using {MODEL}")


if __name__ == "__main__":
    main()
