# miembros_app/pdf_reportlab.py

from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def _bool_si_no(valor):
    return "Sí" if bool(valor) else "No"


def generar_pdf_listado_miembros_reportlab(
    miembros,
    filtros=None,
    titulo="Listado de miembros (SOID)",
):
    """
    Genera un PDF (bytes) con ReportLab: tabla + encabezado + pie con paginación.
    Compatible con Render (sin dependencias del sistema).
    """
    filtros = filtros or {}

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title=titulo,
        author="SOID",
    )

    styles = getSampleStyleSheet()
    style_h = styles["Heading2"]
    style_n = styles["Normal"]

    story = []

    # Encabezado
    story.append(Paragraph(titulo, style_h))
    story.append(Spacer(1, 6))

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Generado: {fecha}", style_n))

    # Resumen de filtros (si hay)
    if any(v for v in filtros.values()):
        partes = []
        if filtros.get("q"):
            partes.append(f'Búsqueda: <b>{filtros["q"]}</b>')
        if filtros.get("estado"):
            partes.append(f'Estado: <b>{filtros["estado"]}</b>')
        if filtros.get("genero"):
            partes.append(f'Género: <b>{filtros["genero"]}</b>')
        if filtros.get("bautizado") in ("0", "1"):
            partes.append(f'Bautizado: <b>{"Sí" if filtros["bautizado"]=="1" else "No"}</b>')

        story.append(Spacer(1, 4))
        story.append(Paragraph(" | ".join(partes), style_n))

    story.append(Spacer(1, 10))

    # Tabla
    data = [
        ["#", "Nombre", "Cédula", "Estado", "Género", "Bautizado"]
    ]

    # Importante: si 'miembros' es QuerySet, esto itera sin cargarlo todo de golpe
    for idx, m in enumerate(miembros, start=1):
        nombre = f"{getattr(m, 'nombres', '')} {getattr(m, 'apellidos', '')}".strip()
        cedula = getattr(m, "cedula", "") or ""
        estado = getattr(m, "estado_membresia", "") or ""
        genero = getattr(m, "genero", "") or ""
        bautizado = _bool_si_no(getattr(m, "bautizado_confirmado", False))

        data.append([str(idx), nombre, cedula, estado, genero, bautizado])

    # Anchos (Carta vertical)
    col_widths = [1.0 * cm, 6.2 * cm, 3.5 * cm, 3.0 * cm, 2.4 * cm, 2.7 * cm]

    table = Table(data, colWidths=col_widths, repeatRows=1)

    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (2, 1), (2, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),

        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))

    # Zebra (filas alternas)
    for r in range(1, len(data)):
        if r % 2 == 0:
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#FAFAFA")),
            ]))

    story.append(table)

    def _on_page(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawRightString(
            letter[0] - 1.2 * cm,
            0.8 * cm,
            f"Página {_doc.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
