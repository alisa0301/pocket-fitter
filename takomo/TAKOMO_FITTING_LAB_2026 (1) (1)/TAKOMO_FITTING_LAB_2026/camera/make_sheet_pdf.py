"""Write the printable A4 measurement sheet (vector ArUco markers).

python camera/make_sheet_pdf.py camera/measurement_sheet_A4.pdf
Needs: pip install opencv-contrib-python reportlab
"""
import sys
from pathlib import Path

import cv2
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sheet as SH  # noqa: E402


def draw_marker(c, mid, x_mm, y_mm, size_mm):
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, SH.DICT))
    bits = cv2.aruco.generateImageMarker(d, mid, 6)          # 4x4 data + 1-bit border = 6 cells
    cell = size_mm / 6
    page_h = SH.A4_H
    for r in range(6):
        for col in range(6):
            if bits[r, col] < 128:
                c.rect((x_mm + col * cell) * mm, (page_h - y_mm - (r + 1) * cell) * mm, cell * mm, cell * mm,
                       stroke=0, fill=1)


def main(out):
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle("Takomo Fitting Lab - measurement sheet")
    for mid, (x, y) in SH.MARKERS.items():
        draw_marker(c, mid, x, y, SH.MARKER_MM)
    H = SH.A4_H
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(105 * mm, (H - 70) * mm, "TAKOMO FITTING LAB  ·  MEASUREMENT SHEET")
    c.setFont("Helvetica", 9.5)
    lines = [
        "Print at 100 % (actual size, no 'fit to page'). Then check the bar below with a ruler: it must be 100 mm.",
        "Keep the sheet flat. All four black squares must be visible and sharp in every photo.",
        "",
        "HAND: lay your lead hand flat down the middle of the sheet (covering this text is fine),",
        "fingers together, wrist crease on the paper, no marker covered. Photograph straight down from 40-60 cm.",
        "",
        "BODY: tape the sheet to a wall at chest height. Stand with your back flat against the same",
        "wall, in golf shoes, arms hanging relaxed. A friend photographs you straight on from 3-4 m,",
        "phone at waist height, whole body and the floor line in frame.",
    ]
    y = H - 82
    for ln in lines:
        c.drawCentredString(105 * mm, y * mm, ln)
        y -= 5.2
    # 100 mm check bar
    c.setLineWidth(1.2)
    c.line(55 * mm, (H - 150) * mm, 155 * mm, (H - 150) * mm)
    for t in range(0, 101, 10):
        c.line((55 + t) * mm, (H - 150) * mm, (55 + t) * mm, (H - 150 + (3 if t % 50 else 5)) * mm)
    c.drawCentredString(105 * mm, (H - 157) * mm, "100 mm")
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(105 * mm, 8 * mm, "Since AI Hackathon 2026 · Takomo Golf challenge · ArUco DICT_4X4_50, markers 40 mm, ids 0-3")
    c.showPage()
    c.save()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "measurement_sheet_A4.pdf")
