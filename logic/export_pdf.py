"""Export classifica to PDF via reportlab."""

import os
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)

from logic.classifica import RigaClassifica
from utils.paths import get_export_dir, get_resource_path

# ── Colours ──────────────────────────────────────────────────────────────────
_BLUE      = colors.HexColor("#2563EB")
_BLUE_DARK = colors.HexColor("#1E40AF")
_EVEN_BG   = colors.HexColor("#EFF6FF")
_GRAY_TXT  = colors.HexColor("#94A3B8")
_HEADER_TXT = colors.white
_BORDER    = colors.HexColor("#CBD5E1")

_STATO_LABELS = {"ok": "OK", "dsq": "DSQ", "dnf": "DNF", "dns": "DNS", "": "—"}

W, H = A4
MARGIN = 18 * mm


def _build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=styles["Normal"],
            fontSize=18, fontName="Helvetica-Bold",
            textColor=_BLUE_DARK, alignment=TA_LEFT, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=styles["Normal"],
            fontSize=11, fontName="Helvetica",
            textColor=colors.HexColor("#475569"), alignment=TA_LEFT, spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "section", parent=styles["Normal"],
            fontSize=12, fontName="Helvetica-Bold",
            textColor=_BLUE_DARK, spaceBefore=10, spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "footer", parent=styles["Normal"],
            fontSize=8, fontName="Helvetica",
            textColor=_GRAY_TXT, alignment=TA_CENTER,
        ),
    }


_LOGO_PATH = get_resource_path('ui/media/logoUfens.png')
_LOGO_H = 12 * mm   # altezza logo nell'intestazione


def _page_header_footer(canvas, doc, nome_gara: str, nome_evento: str) -> None:
    canvas.saveState()

    # ── Header: logo + nome gara ──────────────────────────────────────────
    header_y = H - MARGIN + 2   # linea base dell'area header

    # Logo (opzionale — silenzioso se il file manca)
    logo_x = MARGIN
    text_x = MARGIN
    if os.path.isfile(_LOGO_PATH):
        try:
            canvas.drawImage(
                _LOGO_PATH,
                logo_x, header_y - _LOGO_H,
                height=_LOGO_H,
                width=_LOGO_H,   # quadrato, l'immagine è ritagliata/scalata
                preserveAspectRatio=True,
                mask='auto',
            )
            text_x = logo_x + _LOGO_H + 4 * mm
        except Exception:
            pass

    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(_BLUE_DARK)
    canvas.drawString(text_x, header_y - 9, nome_gara)
    if nome_evento:
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_GRAY_TXT)
        canvas.drawString(text_x, header_y - 9 - 10, nome_evento)

    # Linea separatrice
    canvas.setStrokeColor(_BLUE)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, header_y - _LOGO_H - 2, W - MARGIN, header_y - _LOGO_H - 2)

    # ── Footer ────────────────────────────────────────────────────────────
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_GRAY_TXT)
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    canvas.drawString(MARGIN, MARGIN - 8, f"UfensCrono — {ts}")
    canvas.drawRightString(W - MARGIN, MARGIN - 8, f"Pagina {doc.page}")

    canvas.restoreState()


def _table_style(n_rows: int) -> TableStyle:
    cmds = [
        # Header
        ("BACKGROUND",  (0, 0), (-1, 0), _BLUE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), _HEADER_TXT),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 9),
        ("ALIGN",       (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING",  (0, 0), (-1, 0), 5),
        # Data rows
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ALIGN",       (0, 1), (-1, -1), "CENTER"),
        ("ALIGN",       (2, 1), (2, -1), "LEFT"),  # Atleta column
        ("TOPPADDING",  (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
        # Grid
        ("GRID",        (0, 0), (-1, -1), 0.4, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _EVEN_BG]),
    ]
    return TableStyle(cmds)


def _gray_row_style(row_idx: int) -> list:
    return [
        ("TEXTCOLOR", (0, row_idx), (-1, row_idx), _GRAY_TXT),
        ("FONTNAME",  (0, row_idx), (-1, row_idx), "Helvetica-Oblique"),
    ]


def _build_table_data(
    headers: list[str],
    righe: list[RigaClassifica],
    row_getter,
) -> tuple[list[list], list[int]]:
    data = [headers]
    gray_rows = []
    for i, r in enumerate(righe, start=1):
        data.append(row_getter(r))
        if r.stato in ("dsq", "dnf", "dns"):
            gray_rows.append(i)
    return data, gray_rows


def _make_table(
    headers: list[str],
    col_widths: list[float],
    righe: list[RigaClassifica],
    row_getter,
    page_width: float,
) -> Table:
    data, gray_rows = _build_table_data(headers, righe, row_getter)
    style = _table_style(len(data))
    for ri in gray_rows:
        for cmd in _gray_row_style(ri):
            style.add(*cmd)
    return Table(data, colWidths=col_widths, style=style, repeatRows=1)


def esporta_pdf(
    righe: list[RigaClassifica],
    nome_gara: str,
    nome_evento: str = "",
    dest_path: Optional[str] = None,
) -> str:
    if not dest_path:
        safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in nome_gara)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(get_export_dir(), f"classifica_{safe}_{ts}.pdf")

    styles = _build_styles()
    usable_w = W - 2 * MARGIN

    def on_page(canvas, doc):
        _page_header_footer(canvas, doc, nome_gara, nome_evento)

    # Header occupa MARGIN + logo_h + 4mm di separatore
    top_margin = MARGIN + _LOGO_H + 6 * mm
    frame = Frame(MARGIN, MARGIN + 6, usable_w, H - top_margin - MARGIN - 6, id="body")
    page_tpl = PageTemplate(id="main", frames=[frame], onPage=on_page)
    doc = BaseDocTemplate(
        dest_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=top_margin, bottomMargin=MARGIN + 6,
        pageTemplates=[page_tpl],
    )

    story = []

    # ── Cover header ─────────────────────────────────────────────────────
    story.append(Paragraph(nome_gara, styles["title"]))
    if nome_evento:
        story.append(Paragraph(nome_evento, styles["subtitle"]))
    story.append(Spacer(1, 4 * mm))

    # ── Section 1: Classifica Assoluta ───────────────────────────────────
    story.append(Paragraph("Classifica Assoluta", styles["section"]))

    assoluta = sorted(
        righe,
        key=lambda r: (0 if r.pos_assoluta else 1, r.pos_assoluta or 9999),
    )
    cw = [usable_w * p for p in [0.07, 0.08, 0.28, 0.15, 0.08, 0.16, 0.10, 0.08]]
    t = _make_table(
        ["Pos.", "Pett.", "Atleta", "Cat.", "Sesso", "Tempo", "Stato"],
        cw[:7],
        assoluta,
        lambda r: [
            str(r.pos_assoluta) if r.pos_assoluta else "—",
            r.pettorale, r.nome_atleta, r.categoria, r.sesso,
            r.tempo_display, _STATO_LABELS.get(r.stato, "—"),
        ],
        usable_w,
    )
    story.append(t)
    story.append(PageBreak())

    # ── Section 2 & 3: Per Sesso ─────────────────────────────────────────
    cw6 = [usable_w * p for p in [0.08, 0.09, 0.35, 0.18, 0.18, 0.12]]
    for sesso_code, sesso_label in [("M", "Uomini"), ("F", "Donne")]:
        filtered = sorted(
            [r for r in righe if r.sesso.upper() == sesso_code],
            key=lambda r: (0 if r.pos_sesso else 1, r.pos_sesso or 9999),
        )
        if not filtered:
            continue
        story.append(Paragraph(f"Classifica {sesso_label}", styles["section"]))
        t2 = _make_table(
            ["Pos.", "Pett.", "Atleta", "Cat.", "Tempo", "Stato"],
            cw6,
            filtered,
            lambda r: [
                str(r.pos_sesso) if r.pos_sesso else "—",
                r.pettorale, r.nome_atleta, r.categoria,
                r.tempo_display, _STATO_LABELS.get(r.stato, "—"),
            ],
            usable_w,
        )
        story.append(t2)
        story.append(Spacer(1, 6 * mm))

    story.append(PageBreak())

    # ── Sezioni per-categoria (una per categoria, come nell'app) ─────────
    cw5 = [usable_w * p for p in [0.08, 0.09, 0.45, 0.22, 0.16]]
    categorie = sorted({r.categoria for r in righe if r.categoria})
    for nome_cat in categorie:
        cat_righe = sorted(
            [r for r in righe if r.categoria == nome_cat],
            key=lambda r: (0 if r.pos_categoria else 1, r.pos_categoria or 9999),
        )
        if not cat_righe:
            continue
        section_elems = [
            Paragraph(nome_cat, styles["section"]),
            _make_table(
                ["Pos.", "Pett.", "Atleta", "Tempo", "Stato"],
                cw5,
                cat_righe,
                lambda r: [
                    str(r.pos_categoria) if r.pos_categoria else "—",
                    r.pettorale, r.nome_atleta,
                    r.tempo_display, _STATO_LABELS.get(r.stato, "—"),
                ],
                usable_w,
            ),
            Spacer(1, 6 * mm),
        ]
        story.append(KeepTogether(section_elems))

    doc.build(story)
    return dest_path
