"""Pour report/REPORT.md into the official Apart template (Swarm Alignment version, downloaded 7 Nov 2026), then export
PDF via Word. PREEXISTING: adapted from contrib/apart-collusion/report/build_report.py (Oct 2026); changes: source file,
optional figure width '{{FIG:path|caption|width_in}}'.

  python report/build_report.py            # -> report/report.docx, report/report.pdf
Markdown subset: '## ', '### ', paragraphs, '- ' bullets, '1. ' items, pipe tables,
'**bold**', '*italic*', '`code`', and a line '{{FIG:path|caption}}' for a figure.
"""
import copy
import pathlib
import re
import subprocess
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE / "template.docx"
SRC = HERE / "REPORT.md"
FONT = "Old Standard TT"
BODY_PT = 10.5


def set_t(t_el, text):
    t_el.text = text
    t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def header(doc, title, author, affil, abstract):
    body = doc.element.body
    ts = [t for t in body.iter() if t.tag.endswith("}t")]
    for t in ts:
        if t.text == "PROJECT TITLE":
            set_t(t, title)
    # authors: the template's 6-slot author sub-table collapses around one filled slot,
    # so replace that sub-table with two centred lines (name, affiliation).
    first = next(t for t in ts if t.text == "Author name 1")
    grid = first
    while not grid.tag.endswith("}tbl"):
        grid = grid.getparent()
    parent = grid.getparent()
    idx = list(parent).index(grid)
    parent.remove(grid)
    tmp = docx.Document()
    if isinstance(author, list):   # 7 Nov 2026: side-by-side author columns (name, role lines, email)
        from docx.enum.table import WD_TABLE_ALIGNMENT
        tbl = tmp.add_table(rows=1, cols=len(author))
        tbl.autofit = False
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, lines in enumerate(author):
            cell = tbl.cell(0, j); cell.text = ""
            cell.width = Inches(2.15)
            tbl.columns[j].width = Inches(2.15)
            for k, line in enumerate(lines):
                p = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(line); r.font.name = FONT
                r.font.size = Pt(11 if k == 0 else 9.5)
                r.bold = k == 0
        parent.insert(idx, copy.deepcopy(tbl._tbl))
    else:
        for k, (text, size) in enumerate([(author, 11), (affil, 10)]):
            p = tmp.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(text); r.font.name = FONT; r.font.size = Pt(size)
            parent.insert(idx + k, copy.deepcopy(p._p))
    for t in ts:
        if t.text and t.text.startswith("Summarize your project in 150"):
            set_t(t, abstract)
            # drop the remaining guidance runs in the same paragraph
            p = t.getparent().getparent()
            for r in list(p):
                if r.tag.endswith("}r") and r is not t.getparent():
                    for tt in r.iter():
                        if tt.tag.endswith("}t") and tt is not t:
                            tt.text = ""


def strip_guidance(doc):
    """Remove everything after the header table (info box + guidance), keep sectPr.
    Also drop empty paragraphs that trail the abstract inside the header table: they are
    invisible but push the table's bottom edge down and force the Introduction to page 2."""
    body = doc.element.body
    kids = list(body)
    first_tbl = next(i for i, e in enumerate(kids) if e.tag.endswith("}tbl"))
    hdr = kids[first_tbl]
    last_tc = [e for e in hdr.iter() if e.tag.endswith("}tc")][-1] if False else None
    rows = [e for e in hdr if e.tag.endswith("}tr")]
    for tc in [c for c in rows[-1] if c.tag.endswith("}tc")]:
        items = list(tc)
        last_tbl = max((i for i, e in enumerate(items) if e.tag.endswith("}tbl")), default=None)
        if last_tbl is None:
            continue
        trailing = [e for e in items[last_tbl + 1:] if e.tag.endswith("}p")
                    and not "".join(x.text or "" for x in e.iter() if x.tag.endswith("}t")).strip()]
        for e in trailing[:-1] if len(trailing) > 1 else []:
            tc.remove(e)  # a cell must keep at least one paragraph after a table
    for e in kids[first_tbl + 1:]:
        if not e.tag.endswith("}sectPr"):
            body.remove(e)


INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


def add_runs(p, text, size=BODY_PT, italic=False):
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2]); r.bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(size - 1)
            continue
        elif part.startswith("*"):
            r = p.add_run(part[1:-1]); r.italic = True
        else:
            r = p.add_run(part)
        r.font.name = FONT
        r.font.size = Pt(size)
        if italic:
            r.italic = True


def para(doc, text, style="normal", size=BODY_PT, indent=None, align=None, space_after=4):
    p = doc.add_paragraph(style=style)
    add_runs(p, text, size)
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    pf.line_spacing = 1.08
    if indent is not None:
        pf.left_indent = Inches(indent)
        pf.first_line_indent = Inches(-0.17)
    if align:
        p.alignment = align
    return p


def _borders(table):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "BFBFBF")
        b.append(e)
    tblPr.append(b)


def table(doc, rows):
    hdr = [c.strip() for c in rows[0].strip("|").split("|")]
    body = [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]
    t = doc.add_table(rows=1 + len(body), cols=len(hdr))
    t.autofit = False
    _borders(t)
    total = 6.5
    # width per column, proportional to its longest token (headers wrap at spaces, so count words not whole strings)
    need = []
    for j in range(len(hdr)):
        col = [hdr[j]] + [r[j] for r in body if j < len(r)]
        longest_word = max(len(w) for c in col for w in (re.sub(r"[*`]", "", c).split() or [""]))
        longest_cell = max(len(re.sub(r"[*`]", "", c)) for c in col[1:]) if body else longest_word
        need.append(max(7, longest_word + 3, min(longest_cell, 24)))
    scale = total / sum(need)
    for j in range(len(hdr)):
        for cell in t.columns[j].cells:
            cell.width = Inches(need[j] * scale)
    for i, r in enumerate([hdr] + body):
        for j, v in enumerate(r):
            c = t.cell(i, j); c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            add_runs(p, f"**{v}**" if i == 0 else v, 8)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def build():
    md = []
    for l in SRC.read_text(encoding="utf-8").splitlines():   # '{{INCLUDE:file}}' pulls a generated appendix in
        m = re.match(r"\{\{INCLUDE:(.+)\}\}$", l.strip())
        md += (HERE / m.group(1)).read_text(encoding="utf-8").splitlines() if m else [l]
    meta = {m.group(1): m.group(2) for l in md if (m := re.match(r"% (\w+): (.*)", l))}
    doc = docx.Document(str(TEMPLATE))
    authors = [[x.strip() for x in v.split("|")] for k, v in sorted(meta.items()) if re.fullmatch(r"AUTHOR\d", k)]
    header(doc, meta["TITLE"], authors or meta["AUTHOR"], meta.get("AFFILIATION", ""), meta["ABSTRACT"])
    strip_guidance(doc)
    lines = [l for l in md if not l.startswith("% ")]
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("## "):
            h = doc.add_paragraph(style="Heading 2"); add_runs(h, l[3:], 13)
            h.paragraph_format.space_before = Pt(8); h.paragraph_format.space_after = Pt(3)
        elif l.startswith("### "):
            h = doc.add_paragraph(style="Heading 3"); add_runs(h, l[4:], 11.5)
            h.paragraph_format.space_before = Pt(4); h.paragraph_format.space_after = Pt(2)
        elif l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            table(doc, rows)
            continue
        elif l.startswith("{{FIG:"):
            parts = l[6:-2].split("|")
            path, cap = parts[0], parts[1]
            wid = float(parts[2]) if len(parts) > 2 else 5.6
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(HERE / path), width=Inches(wid))
            para(doc, cap, size=9, space_after=8)
        elif l.startswith("- "):
            para(doc, "•  " + l[2:], indent=0.25, space_after=2)
        elif re.match(r"\d+\. ", l):
            para(doc, l, indent=0.25, space_after=2)
        elif l.startswith("[") and re.match(r"\[\d+\]", l):
            para(doc, l, size=9, indent=0.3, space_after=1)
        elif l.strip():
            para(doc, l)
        i += 1
    out = HERE / "report.docx"
    doc.save(str(out))
    return out


def to_pdf(docx_path):
    pdf = docx_path.with_suffix(".pdf")
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$d = $w.Documents.Open('{docx_path}'); $d.SaveAs([ref]'{pdf}', [ref]17); $d.Close(); $w.Quit()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return pdf


if __name__ == "__main__":
    d = build()
    print("docx", d)
    if "--no-pdf" not in sys.argv:
        print("pdf", to_pdf(d))
