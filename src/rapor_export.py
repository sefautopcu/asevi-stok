"""Report serialization helpers isolated from the Streamlit UI."""
from html import escape
from io import BytesIO

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def excel_raporu_bytes(veri_listesi, baslik, rapor_zamani):
    """Build an Excel report; inject time so the helper remains deterministic/testable."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Rapor"
    sheet.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="04110C")
    title_font = Font(name="Calibri", size=14, bold=True, color="000000")
    regular_font = Font(name="Calibri", size=11)
    thin_border = Border(
        left=Side(style="thin", color="e2e8f0"),
        right=Side(style="thin", color="e2e8f0"),
        top=Side(style="thin", color="e2e8f0"),
        bottom=Side(style="thin", color="e2e8f0"),
    )

    sheet.cell(row=1, column=1, value=baslik).font = title_font
    sheet.cell(row=2, column=1, value=f"Rapor Tarihi ve Saati: {rapor_zamani}").font = Font(
        name="Calibri", size=11, italic=True, color="6b7280"
    )

    if veri_listesi:
        headers = list(veri_listesi[0].keys())
        for column, header in enumerate(headers, 1):
            cell = sheet.cell(row=4, column=column, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row_index, item in enumerate(veri_listesi, 5):
            for column, header in enumerate(headers, 1):
                cell = sheet.cell(row=row_index, column=column, value=item.get(header, ""))
                if cell.data_type == "f":
                    cell.data_type = "s"
                cell.font = regular_font
                cell.border = thin_border

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def html_raporu_bytes(baslik, veri_listesi, rapor_zamani, tema):
    """Build escaped, printable HTML with theme values explicitly provided."""
    text_color = tema["text_color"]
    bg_color = tema["bg_color"]
    subtext_color = tema["subtext_color"]
    card_bg = tema["card_bg"]
    border_color = tema["border_color"]
    sidebar_bg = tema["sidebar_bg"]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{escape(str(baslik))}</title>
        <style>
            body {{ font-family: 'Plus Jakarta Sans', sans-serif; margin: 30px; color: {text_color}; background: {bg_color}; }}
            h2 {{ color: {text_color}; margin-bottom: 5px; }}
            p {{ color: {subtext_color}; font-size: 14px; margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: {card_bg}; }}
            th {{ background-color: #10B981; color: #04110C; padding: 12px; text-align: left; font-size: 13px; }}
            td {{ border: 1px solid {border_color}; padding: 10px 12px; font-size: 13px; color: {subtext_color}; }}
            tr:nth-child(even) {{ background-color: {sidebar_bg}; }}
        </style>
    </head>
    <body>
        <h2>{escape(str(baslik))}</h2>
        <p>Rapor Tarihi ve Saati: {escape(str(rapor_zamani))}</p>
        <hr style="border: 0; border-top: 1px solid {border_color};"/>
    """
    if veri_listesi:
        headers = list(veri_listesi[0].keys())
        html += "<table><tr>"
        for header in headers:
            html += f"<th>{escape(str(header))}</th>"
        html += "</tr>"
        for item in veri_listesi:
            html += "<tr>"
            for header in headers:
                html += f"<td>{escape(str(item.get(header, '')))}</td>"
            html += "</tr>"
        html += "</table>"
    else:
        html += "<p>Kayıt bulunamadı.</p>"
    return (html + "</body></html>").encode("utf-8")
