import datetime
import re
import sys
import zipfile
from pathlib import Path

import docx
import openpyxl
import pymupdf
from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.util import Inches

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/00-samples")
OUT.mkdir(parents=True, exist_ok=True)

TITLE = "Q3 Report"
PARAGRAPH = "Sales rose 12% in Q3."
TABLE = [("Region", "Sales"), ("Seoul", "120"), ("Busan", "80")]
BULLETS = ["Seoul led growth", "Busan was flat"]


def banner(name):
    print(f"\n{'=' * 20} {name} {'=' * 20}")


def readable_xml(xml, limit):
    xml = re.sub(r'\s+xmlns(:\w+)?="[^"]*"', "", xml)
    xml = re.sub(r"<\?xml[^>]*\?>", "", xml)
    xml = re.sub(r"(<[^/][^>]*>)", r"\n\1", xml)
    lines = [line for line in xml.splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def show_zip_part(path, part, limit=40, pattern=None):
    with zipfile.ZipFile(path) as z:
        xml = z.read(part).decode()
    if pattern:
        xml = "".join(re.findall(pattern, xml, re.S))
    print(f"--- {part}")
    print(readable_xml(xml, limit))


def list_zip(path):
    with zipfile.ZipFile(path) as z:
        print("zip parts:", ", ".join(n for n in z.namelist() if not n.endswith(".rels")))


def make_docx():
    path = OUT / "sample.docx"
    d = docx.Document()
    d.add_heading(TITLE, level=1)
    d.add_paragraph(PARAGRAPH)
    table = d.add_table(rows=len(TABLE), cols=2)
    for r, row in enumerate(TABLE):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    for item in BULLETS:
        d.add_paragraph(item, style="List Bullet")
    d.save(path)
    banner("DOCX")
    list_zip(path)
    show_zip_part(path, "word/document.xml", limit=70, pattern=r"<w:body>.*</w:body>")


def make_xlsx():
    path = OUT / "sample.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = TITLE
    ws.merge_cells("A1:B1")
    for r, row in enumerate(TABLE, start=3):
        ws.cell(r, 1, row[0])
        ws.cell(r, 2, int(row[1]) if row[1].isdigit() else row[1])
    ws["A6"] = "Total"
    ws["B6"] = "=SUM(B4:B5)"
    ws["D3"] = datetime.date(2026, 9, 30)
    wb.save(path)
    banner("XLSX")
    list_zip(path)
    show_zip_part(path, "xl/worksheets/sheet1.xml", limit=40, pattern=r"<sheetData>.*</mergeCells>")


def make_pptx():
    path = OUT / "sample.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = TITLE
    body = slide.shapes.add_textbox(Inches(5), Inches(2), Inches(4), Inches(1))
    body.text_frame.text = PARAGRAPH
    a = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(4), Inches(2), Inches(1))
    a.text_frame.text = "Collect"
    b = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(4), Inches(4), Inches(2), Inches(1))
    b.text_frame.text = "Report"
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, 0, 0, 0, 0)
    line.begin_connect(a, 3)
    line.end_connect(b, 1)
    prs.save(path)
    banner("PPTX")
    list_zip(path)
    show_zip_part(path, "ppt/slides/slide1.xml", limit=200, pattern=r"<p:spTree>.*</p:spTree>")


def make_pdf():
    path = OUT / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), TITLE, fontsize=20)
    page.insert_text((72, 110), PARAGRAPH, fontsize=11)
    y = 140
    for row in TABLE:
        page.insert_text((80, y + 14), row[0], fontsize=11)
        page.insert_text((200, y + 14), row[1], fontsize=11)
        page.draw_rect(pymupdf.Rect(72, y, 300, y + 20))
        y += 20
    doc.save(path)
    banner("PDF")
    doc = pymupdf.open(path)
    page = doc[0]
    stream = b"".join(page.read_contents().splitlines(keepends=True)[:40]).decode("latin-1")
    print("--- page content stream (first 40 lines)")
    print(stream)
    print("--- glyph runs pymupdf recovers: (x0, y0) size text")
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                x0, y0 = span["bbox"][:2]
                print(f"({x0:6.1f}, {y0:6.1f}) {span['size']:4.1f} {span['text']!r}")
    return path


def make_scan(pdf_path):
    banner("SCAN (image)")
    pix = pymupdf.open(pdf_path)[0].get_pixmap(dpi=100)
    png = OUT / "sample.png"
    pix.save(png)
    print(f"{png.name}: {pix.width}x{pix.height} pixels, {pix.n} channels")
    red = [pix.samples[i] for i in range(0, len(pix.samples), pix.n)]
    first_ink = next(i for i, v in enumerate(red) if v < 128)
    row, col = divmod(first_ink, pix.width)
    print(f"first dark pixel at row {row}, col {col}; next 30 values in that row:")
    print(red[first_ink : first_ink + 30])


make_docx()
make_xlsx()
make_pptx()
make_scan(make_pdf())
