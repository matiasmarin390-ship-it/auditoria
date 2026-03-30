from flask import Flask, request, send_file, abort
import pandas as pd
import io
import os
import math
import uuid
from html import escape
from urllib.parse import urlencode

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

app = Flask(__name__)

REPORT_CACHE = {}

# ===============================
# UTILIDADES
# ===============================
def fmt_fecha(x):
    if pd.isna(x):
        return "-"
    return pd.to_datetime(x).strftime("%Y-%m-%d %H:%M:%S")


def maps_pin_url(lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return ""
    return f"https://www.google.com/maps?q={lat},{lon}"


def html_tabla(df):
    if df is None or df.empty:
        return "<p>Sin datos</p>"
    return df.to_html(index=False, escape=False)


# ===============================
# LECTURA ARCHIVO
# ===============================
def leer_archivo(archivo):
    nombre = archivo.filename.lower()

    if nombre.endswith(".xlsx") or nombre.endswith(".xls"):
        return pd.read_excel(archivo)

    return pd.read_csv(archivo)


# ===============================
# PDF
# ===============================
def build_pdf(data):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("Informe de Auditoría", styles["Title"]))
    story.append(Spacer(1, 12))

    for k, v in data.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["BodyText"]))

    doc.build(story)

    buffer.seek(0)
    return buffer


@app.route("/pdf/<report_id>")
def descargar_pdf(report_id):
    data = REPORT_CACHE.get(report_id)

    if not data:
        abort(404)

    pdf = build_pdf(data)

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="reporte.pdf"
    )


# ===============================
# APP PRINCIPAL
# ===============================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            archivo = request.files["file"]

            df = leer_archivo(archivo)

            resumen = {
                "Filas": len(df),
                "Columnas": len(df.columns),
                "Columnas detectadas": ", ".join(df.columns)
            }

            report_id = str(uuid.uuid4())
            REPORT_CACHE[report_id] = resumen

            return f"""
            <h2>Resultado</h2>
            {html_tabla(df.head())}
            <br><br>
            <a href="/pdf/{report_id}">Descargar PDF</a>
            """

        except Exception as e:
            return f"<h3>Error</h3><pre>{escape(str(e))}</pre>"

    return """
    <h2>Auditoría de archivos</h2>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <input type="submit" value="Procesar">
    </form>
    """


# ===============================
# MAIN (Cloud Run compatible)
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
