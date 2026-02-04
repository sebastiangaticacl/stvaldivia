#!/usr/bin/env python3
"""
Exporta un archivo Markdown a PDF usando markdown + reportlab (sin dependencias del sistema).
Uso: python scripts/export_md_to_pdf.py [archivo.md] [salida.pdf]
Por defecto: docs/AUDITORIA_TECNICA_DESCRIPTIVA.md -> docs/AUDITORIA_TECNICA_DESCRIPTIVA.pdf
"""
import os
import re
import sys

try:
    import markdown
except ImportError:
    print("Instala: pip install markdown")
    sys.exit(1)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("Instala: pip install reportlab")
    sys.exit(1)


def md_to_story(md_path: str, styles):
    """Convierte Markdown a una lista de elementos Platypus (Paragraph, Spacer, etc.)."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Normalizar saltos de línea
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    story = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # HR: --- o ***
        if stripped in ("---", "***", "___"):
            story.append(Spacer(1, 0.4 * cm))
            i += 1
            continue

        # H1: # título
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            story.append(Paragraph(_escape(title), styles["Heading1"]))
            story.append(Spacer(1, 0.3 * cm))
            i += 1
            continue

        # H2: ## título
        if line.startswith("## ") and not line.startswith("### "):
            title = line[3:].strip()
            story.append(Paragraph(_escape(title), styles["Heading2"]))
            story.append(Spacer(1, 0.25 * cm))
            i += 1
            continue

        # H3: ### título
        if line.startswith("### "):
            title = line[4:].strip()
            story.append(Paragraph(_escape(title), styles["Heading3"]))
            story.append(Spacer(1, 0.2 * cm))
            i += 1
            continue

        # Lista con - o *
        if stripped.startswith("- ") or stripped.startswith("* "):
            items = []
            while i < len(lines):
                ln = lines[i]
                st = ln.strip()
                if st.startswith("- ") or st.startswith("* "):
                    item_text = st[2:].strip()
                    items.append(ListItem(Paragraph(_escape(item_text), styles["Normal"])))
                    i += 1
                elif st == "":
                    i += 1
                    break
                else:
                    break
            if items:
                story.append(ListFlowable(items, bulletType="bullet"))
                story.append(Spacer(1, 0.2 * cm))
            continue

        # Lista numerada
        num_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if num_match:
            items = []
            while i < len(lines):
                ln = lines[i]
                num_m = re.match(r"^(\d+)\.\s+(.+)$", ln.strip())
                if num_m:
                    items.append(ListItem(Paragraph(_escape(num_m.group(2).strip()), styles["Normal"])))
                    i += 1
                elif ln.strip() == "":
                    i += 1
                    break
                else:
                    break
            if items:
                story.append(ListFlowable(items, bulletType="1"))
                story.append(Spacer(1, 0.2 * cm))
            continue

        # Párrafo normal
        if stripped:
            # Unir líneas del mismo párrafo
            para_lines = [stripped]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].strip().startswith("- ") and not lines[i].strip().startswith("* ") and not re.match(r"^\d+\.\s+", lines[i].strip()):
                para_lines.append(lines[i].strip())
                i += 1
            story.append(Paragraph(_escape(" ".join(para_lines)), styles["Normal"]))
            story.append(Spacer(1, 0.15 * cm))
        else:
            i += 1

    return story


def _escape(s: str) -> str:
    """Escapa HTML para ReportLab (acepta un subconjunto de tags)."""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Restaurar negrita **texto** -> <b>texto</b>
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r'<font name="Courier" size="9">\1</font>', s)
    return s


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_md = os.path.join(base, "docs", "AUDITORIA_TECNICA_DESCRIPTIVA.md")
    default_pdf = os.path.join(base, "docs", "AUDITORIA_TECNICA_DESCRIPTIVA.pdf")

    md_path = sys.argv[1] if len(sys.argv) > 1 else default_md
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else default_pdf

    if not os.path.exists(md_path):
        print(f"No existe el archivo: {md_path}")
        sys.exit(1)

    styles = getSampleStyleSheet()
    styles["Heading1"].fontSize = 16
    styles["Heading1"].spaceAfter = 8
    styles["Heading2"].fontSize = 13
    styles["Heading2"].spaceAfter = 6
    styles["Heading3"].fontSize = 11
    styles["Heading3"].spaceAfter = 4

    print(f"Leyendo: {md_path}")
    story = md_to_story(md_path, styles)
    print(f"Generando PDF: {pdf_path}")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    doc.build(story)
    print(f"Listo: {pdf_path}")


if __name__ == "__main__":
    main()
