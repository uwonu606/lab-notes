import sys
from pathlib import Path

import docx
from docx.shared import Pt, RGBColor
from markitdown import MarkItDown

INPUT_ONLY = "--input-only" in sys.argv
POSITIONAL = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = Path(POSITIONAL[0] if POSITIONAL else "runs/01-docx-heading")
OUT.mkdir(parents=True, exist_ok=True)

HEADING_BLUE = RGBColor(0x36, 0x5F, 0x91)


def banner(name):
    print(f"\n{'=' * 20} {name} {'=' * 20}")


def styled_as_heading_looks_like_heading(d, text):
    d.add_paragraph(text, style="Heading 1")


def plain_style_dressed_as_heading(d, text):
    run = d.add_paragraph().add_run(text)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = HEADING_BLUE


def styled_as_heading_dressed_as_body(d, text):
    run = d.add_paragraph(style="Heading 1").add_run(text)
    run.bold = False
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0, 0, 0)


def resolve(paragraph, read):
    run = paragraph.runs[0] if paragraph.runs else None
    if run is not None and read(run.font) is not None:
        return read(run.font)
    style = paragraph.style
    while style is not None:
        if read(style.font) is not None:
            return read(style.font)
        style = style.base_style
    return None


def describe_look(paragraph):
    bold = bool(resolve(paragraph, lambda f: f.bold))
    size = resolve(paragraph, lambda f: f.size)
    color = resolve(paragraph, lambda f: f.color.rgb if f.color and f.color.type else None)
    size_text = f"{size.pt:g}pt" if size else "default"
    return f"bold={bold!s:5} size={size_text:7} color={color or 'default'}"


def build(path):
    d = docx.Document()
    styled_as_heading_looks_like_heading(d, "Q3 Report")
    d.add_paragraph("Sales rose 12% in Q3.")
    plain_style_dressed_as_heading(d, "Regional Results")
    d.add_paragraph("Seoul led growth.")
    styled_as_heading_dressed_as_body(d, "Outlook")
    d.add_paragraph("Q4 is expected to be flat.")
    d.save(path)


def show_hidden_state(path):
    banner("hidden state: style name vs. look")
    for i, p in enumerate(docx.Document(path).paragraphs, start=1):
        print(f"{i}. style={p.style.name!r:13} {describe_look(p)}  {p.text!r}")


def show_markdown(path):
    banner("MarkItDown output")
    print(MarkItDown().convert(str(path)).text_content)


path = OUT / "headings.docx"
build(path)
show_hidden_state(path)
if not INPUT_ONLY:
    show_markdown(path)
