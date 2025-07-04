# app.py
from flask import Flask, render_template, request, send_from_directory
from fpdf import FPDF
import qrcode
from datetime import datetime
from pathlib import Path
import uuid, os

BASE_DIR   = Path(__file__).parent.resolve()
FONTS_DIR  = BASE_DIR / "fonts"
STATIC_DIR = BASE_DIR / "static"
GEN_DIR    = BASE_DIR / "generated"
QR_DIR     = STATIC_DIR / "qr"

app = Flask(__name__)

# Папки гарантовано існують
GEN_DIR.mkdir(exist_ok=True)
QR_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────
#  FPDF‑шаблон: додає PNG‑фон, уся верстка робиться координатами
# ──────────────────────────────────────────────────────────────────────────
class CertificatePDF(FPDF):
    def header(self):
        # Повний фон (A4 портрет 210×297 мм)
        self.image(str(STATIC_DIR / "img" / "template.png"), x=0, y=0, w=210)

    def footer(self):
        pass  # фон уже має нижній блок — зайве не друкуємо

# ──────────────────────────────────────────────────────────────────────────
#  Функція генерації PDF
# ──────────────────────────────────────────────────────────────────────────
def build_certificate(data: dict, filename: str) -> Path:
    pdf = CertificatePDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    # Шрифт із кирилицею
    pdf.add_font("Main", "", str(FONTS_DIR / "DejaVuSans.ttf"), uni=True)
    pdf.add_font("Veles", "", str(FONTS_DIR / "VelesRegular.ttf"), uni=True)
    pdf.set_auto_page_break(auto=False)

       # ——— ПІБ ———
    pdf.set_font("Veles", "", 28)            # <-- тут Veles
    pdf.set_xy(0, 60)
    pdf.cell(210, 12, data["full_name"], align="C")

    # ——— Блок «за успішне закінчення…» ———
    pdf.set_font("Main", "", 16)
    pdf.set_xy(0, 80)
    pdf.multi_cell(210, 9,
        f'за успішне закінчення курсу «{data["course"]}»',
        align="C")

    # ——— Деталі: тривалість і дати ———
    pdf.set_xy(0, 105)
    pdf.multi_cell(210, 8,
        f'Тривалість: {data["hours"]} годин\n'
        f'Початок: {data["start_date"]}\n'
        f'Кінець: {data["end_date"]}',
        align="C")

    # ——— Підписи викладачів ———
    pdf.set_xy(25, 165)
    pdf.cell(0, 8, data["lecturer"], align="L")
    pdf.set_xy(140, 165)
    pdf.cell(0, 8, data["assistant"], align="L")

    # ——— QR‑код із текстовими даними ———
    serial = str(uuid.uuid4())[:8]      # короткий серійний, якщо треба
    qr_text = (
        f"Сертифікат № {serial}\n"
        f"ПІБ: {data['full_name']}\n"
        f"Курс: {data['course']}\n"
        f"Тривалість: {data['hours']} год.\n"
        f"Початок: {data['start_date']}\n"
        f"Кінець: {data['end_date']}\n"
        f"Викладач: {data['lecturer']}\n"
        f"Асистент: {data['assistant']}"
    )
    qr_path = QR_DIR / f"{serial}.png"
    qrcode.make(qr_text).save(qr_path)

    pdf.image(str(qr_path), x=165, y=240, w=30)
    pdf.set_font("Main", "", 10)
    pdf.set_xy(0, 275)
    pdf.cell(210, 5, f"Серійний № {serial}", align="C")

    # ——— Зберігаємо PDF і чистимо QR‑png ———
    pdf_path = GEN_DIR / filename
    pdf.output(str(pdf_path))
    qr_path.unlink(missing_ok=True)

    return pdf_path

# ──────────────────────────────────────────────────────────────────────────
#  Flask маршрути
# ──────────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = {
            "full_name":  request.form["full_name"],
            "course":     request.form["course"],
            "hours":      request.form["hours"],
            "start_date": request.form["start_date"],
            "end_date":   request.form["end_date"],
            "lecturer":   request.form["lecturer"],
            "assistant":  request.form["assistant"]
        }

        file_name = f"{data['full_name'].replace(' ', '_')}_{datetime.now().date()}.pdf"
        pdf_path  = build_certificate(data, file_name)

        # Віддаємо файл (і залишаємо копію у generated/)
        return send_from_directory(GEN_DIR, file_name, as_attachment=True)

    return render_template("form.html")

# ——— Просто для демонстрації, що перевірка може існувати, ———
#     але у QR тепер вшитий сам текст, тому verify не критичний.
@app.route("/verify/<serial>")
def verify(serial):
    return f"Сертифікат № {serial} було створено цією системою."

# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
