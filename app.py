from flask import (
    Flask, render_template, request,
    send_from_directory, url_for, redirect,
    session
)
from fpdf import FPDF
import qrcode, uuid, os
from datetime import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent.resolve()
FONTS_DIR  = BASE_DIR / "fonts"
STATIC_DIR = BASE_DIR / "static"
GEN_DIR    = BASE_DIR / "generated"
QR_DIR     = STATIC_DIR / "qr"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")
GEN_DIR.mkdir(exist_ok=True)
QR_DIR.mkdir(parents=True, exist_ok=True)

class CertificatePDF(FPDF):
    def header(self):
        self.image(str(STATIC_DIR / "img" / "template.png"), x=0, y=0, w=210)
    def footer(self): pass

def build_certificate(data: dict, filename: str) -> Path:
    pdf = CertificatePDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    pdf.add_font("Main",  "", str(FONTS_DIR / "DejaVuSans.ttf"),  uni=True)
    pdf.add_font("Arsenal", "", str(FONTS_DIR / "Arsenal-Regular.ttf"), uni=True)
    pdf.set_auto_page_break(auto=False)

    pdf.set_font("Main", "", 14)
    pdf.set_xy(1, 41.5)
    pdf.multi_cell(210, 7, f"Спеціальність: {data['specialty']}", align="C")

    pdf.set_font("Arsenal", "", 32)
    pdf.set_xy(0, 92)
    pdf.cell(210, 12, data["full_name"], align="C")

    pdf.set_font("Main", "", 16)
    pdf.set_xy(0, 114)
    pdf.multi_cell(210, 9,
        f'за успішне закінчення курсу «{data["course"]}»',
        align="C")

    pdf.set_font("Main", "", 16)
    lines = [
        f'Тривалість: {data["hours"]} годин',
        f'Початок: {data["start_date"]}',
        f'Кінець: {data["end_date"]}',
        f'Курс: {data["year"]}',
    ]
    y = 145
    for txt in lines:
        w = pdf.get_string_width(txt)
        pdf.text((210 - w) / 2, y, txt)
        y += 8

    pdf.set_font("Main", "", 16)
    pdf.set_xy(115, 214)
    pdf.cell(60, 6, data["lecturer"], align="C")
    pdf.set_xy(115, 234)
    pdf.cell(60, 6, "Ткачук В.А.", align="C")

    qr_text = (
        f"ПІБ: {data['full_name']}\n"
        f"Спеціальність: {data['specialty']}\n"
        f"Курс програми: {data['course']}\n"
        f"Тривалість: {data['hours']} год.\n"
        f"Початок: {data['start_date']}\n"
        f"Кінець: {data['end_date']}\n"
        f"Курс (рік): {data['year']}\n"
        f"Викладач: {data['lecturer']}"
    )
    qr_tmp = QR_DIR / f"{uuid.uuid4().hex}.png"
    qrcode.make(qr_text).save(qr_tmp)
    pdf.image(str(qr_tmp), x=160, y=260, w=30)
    qr_tmp.unlink(missing_ok=True)

    out_path = GEN_DIR / filename
    pdf.output(str(out_path))
    return out_path

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = {
            "full_name":  request.form["full_name"],
            "specialty":  request.form["specialty"],
            "course":     request.form["course"],
            "hours":      request.form["hours"],
            "start_date": request.form["start_date"],
            "end_date":   request.form["end_date"],
            "lecturer":   request.form["lecturer"],
            "year":       request.form["year"]
        }
        fname = f"{data['full_name'].replace(' ', '_')}_{datetime.now().date()}.pdf"
        pdf_path = build_certificate(data, fname)

        certs = session.get("cert_files", [])
        certs.append(pdf_path.name)
        session["cert_files"] = certs
        session.modified = True

        return send_from_directory(GEN_DIR, pdf_path.name, as_attachment=True)
    return render_template("form.html")


@app.route("/certificates")
def certificates():
    files = session.get("cert_files", [])
    return render_template("certificates.html", files=files)

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(GEN_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, host="0.0.0.0", port=port)