"""Generate the one-page Round 1 PDF. ReportLab is a development-only dependency."""
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def build():
    entries = json.loads((ROOT / "docs/proposal.json").read_text(encoding="utf-8"))
    count = len(re.findall(r"\S+", " ".join(e["text"] for e in entries)))
    assert len(entries) == 10 and count <= 500
    output = ROOT / "output/pdf/vaultmind-ai-round1-proposal.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=(612, 792), pageCompression=1, invariant=1)
    c.setTitle("VaultMind AI - Round 1 Proposal")
    c.setAuthor("VaultMind AI")
    green = colors.HexColor("#1d493f")
    c.setFillColor(green)
    c.rect(0, 682, 612, 110, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#bfd7c7"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, 759, "UGREEN AI NAS HACKATHON 2026 / ROUND 1")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(36, 720, "VaultMind AI")
    c.setFont("Helvetica", 10)
    c.drawString(36, 700, "Find your files. Review changes before they happen.")
    heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=green)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.3, leading=13, textColor=colors.HexColor("#293e36"))
    bottoms = []
    for column in range(2):
        x, y = 36 + column * 282, 657
        for i in range(column * 5, column * 5 + 5):
            entry = entries[i]
            p = Paragraph(f'{i+1:02d} / {escape(entry["title"])}', heading)
            _, height = p.wrap(258, 700)
            p.drawOn(c, x, y - height)
            y -= height + 5
            p = Paragraph(escape(entry["text"]), body)
            _, height = p.wrap(258, 700)
            p.drawOn(c, x, y - height)
            y -= height + 12
        bottoms.append(y)
    assert min(bottoms) > 105, f"Proposal content overlaps disclosure: {bottoms}"
    c.setStrokeColor(colors.HexColor("#d3ded3"))
    c.line(36, 104, 576, 104)
    foot = ParagraphStyle("foot", fontSize=7.3, leading=10, textColor=colors.HexColor("#5f7368"))
    note = "Third-party disclosure: UGREEN creation kit 0.7.3 and platform experts, under UGREEN terms; used for authoring/validation and runtime respectively. No third-party executable code is included in the Skill ZIP. Local tooling only: Python (PSF), SQLite (public domain), Node.js (MIT), ReportLab (BSD), pypdf (BSD). Sources: ai.ugreen.com/pages/hackathon-starter-kit and ugreenhackathon.devpost.com."
    p = Paragraph(escape(note), foot)
    _, height = p.wrap(540, 90)
    p.drawOn(c, 36, 92 - height)
    c.setFont("Helvetica", 7)
    c.drawString(36, 28, f"{count} response words | Pre-test submission | NAS validation pending")
    c.drawRightString(576, 28, "1 / 1")
    c.save()
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) == 1 and output.stat().st_size < 1_000_000
    for entry in entries:
        assert entry["title"] in text
    result = {"response_words": count, "pages": len(reader.pages), "bytes": output.stat().st_size, "path": output.relative_to(ROOT).as_posix(), "column_bottoms": bottoms}
    (ROOT / "artifacts/proposal-check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    build()
