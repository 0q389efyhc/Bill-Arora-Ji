import base64
import json
import sqlite3
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import streamlit as st
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
DB = ROOT / "bills.db"
PDF_DIR = ROOT / "pdfs"
PDF_DIR.mkdir(exist_ok=True)
FONT_DIR = ROOT / "fonts"

pdfmetrics.registerFont(TTFont("Sans", str(FONT_DIR / "NotoSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Sans-Bold", str(FONT_DIR / "NotoSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("Hi", str(FONT_DIR / "NotoSansDevanagari-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Hi-Bold", str(FONT_DIR / "NotoSansDevanagari-Bold.ttf")))

COMPANY = {
    "name": "ARORA ROAD CARRIER",
    "tag": "TRANSPORT CONTRACTOR & COMMISSION AGENT",
    "address": "Main Road, Ramdev Ji Ka Chanderiya, Chittorgarh (Raj.)",
    "pan": "ALUPK7249J",
    "mob1": "98292 45536",
    "mob2": "8209137649",
    "blessing": "|| श्री गणेशाय नमः ||",
    "jurisdiction": "All Subject to Chittorgarh Jurisdiction Only",
    "bank": "IDBI Bank, Chittorgarh (Raj.)",
    "ac": "111102000010423",
    "ifsc": "IBKL0000111",
}

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gr_no TEXT UNIQUE,
                bill_date TEXT,
                consignor_name TEXT,
                consignor_addr TEXT,
                consignor_gstin TEXT,
                consignee_name TEXT,
                consignee_addr TEXT,
                consignee_gstin TEXT,
                from_place TEXT,
                to_place TEXT,
                value_of_goods TEXT,
                truck_no TEXT,
                gst_paid_by TEXT,
                note_goods TEXT,
                lines_json TEXT,
                total_packages TEXT,
                total_weight TEXT,
                total_freight REAL,
                total_advance REAL,
                total_balance REAL,
                created_at TEXT
            )
        """)

def next_gr():
    with conn() as c:
        row = c.execute("SELECT MAX(CAST(gr_no AS INTEGER)) FROM bills").fetchone()
    last = row[0] or 1278
    return str(int(last) + 1)

def save_bill(data):
    with conn() as c:
        c.execute("""
            INSERT INTO bills (
                gr_no, bill_date, consignor_name, consignor_addr, consignor_gstin,
                consignee_name, consignee_addr, consignee_gstin, from_place, to_place,
                value_of_goods, truck_no, gst_paid_by, note_goods, lines_json,
                total_packages, total_weight, total_freight, total_advance, total_balance, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["gr_no"], data["bill_date"], data["consignor_name"], data["consignor_addr"], data["consignor_gstin"],
            data["consignee_name"], data["consignee_addr"], data["consignee_gstin"], data["from_place"], data["to_place"],
            data["value_of_goods"], data["truck_no"], data["gst_paid_by"], data["note_goods"], json.dumps(data["lines"]),
            data["total_packages"], data["total_weight"], data["total_freight"], data["total_advance"], data["total_balance"],
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))

def list_bills(q=""):
    with conn() as c:
        if q:
            like = f"%{q}%"
            rows = c.execute("""
                SELECT * FROM bills
                WHERE gr_no LIKE ? OR consignor_name LIKE ? OR consignee_name LIKE ?
                   OR from_place LIKE ? OR to_place LIKE ? OR truck_no LIKE ?
                ORDER BY id DESC
            """, (like, like, like, like, like, like)).fetchall()
        else:
            rows = c.execute("SELECT * FROM bills ORDER BY id DESC").fetchall()
    return rows

def get_bill(gr_no):
    with conn() as c:
        return c.execute("SELECT * FROM bills WHERE gr_no = ?", (gr_no,)).fetchone()

def show_pdf(pdf_bytes, height=640):
    b64 = base64.b64encode(pdf_bytes).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" '
        'style="border:1px solid #ccc;"></iframe>',
        unsafe_allow_html=True,
    )

def num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0

def pdf_for(data):
    buf = BytesIO()
    page = landscape(A4)
    c = canvas.Canvas(buf, pagesize=page)
    w, h = page
    m = 16
    navy = (0.08, 0.16, 0.38)
    c.setStrokeColorRGB(*navy)
    c.setLineWidth(1.1)
    c.rect(m, 12, w - 2 * m, h - 24)

    top = h - 22
    c.setFont("Sans", 8)
    c.drawString(m + 8, top, f"PAN No. {COMPANY['pan']}")
    c.setFont("Hi", 9)
    c.drawCentredString(w / 2, top, COMPANY["blessing"])
    c.setFont("Sans", 8)
    c.drawRightString(w - m - 8, top, f"Mob. {COMPANY['mob1']}")
    c.drawRightString(w - m - 8, top - 10, COMPANY["mob2"])
    c.drawCentredString(w / 2, top - 12, COMPANY["jurisdiction"])

    c.setFont("Sans-Bold", 20)
    c.drawCentredString(w / 2, top - 32, COMPANY["name"])
    c.setFont("Sans-Bold", 9)
    c.drawCentredString(w / 2, top - 46, COMPANY["tag"])
    c.setFont("Sans", 8)
    c.drawCentredString(w / 2, top - 58, COMPANY["address"])
    c.line(m, top - 64, w - m, top - 64)

    y = top - 64
    left_w = 250
    mid_w = 250
    right_x = m + left_w + mid_w
    right_w = w - m - right_x
    head_h = 14
    box_h = 72

    c.setFillColorRGB(*navy)
    c.rect(m, y - head_h, left_w + mid_w, head_h, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Sans-Bold", 8)
    c.drawCentredString(m + left_w / 2, y - 10, "CONSIGNOR")
    c.drawCentredString(m + left_w + mid_w / 2, y - 10, "CONSIGNEE")
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(*navy)
    c.rect(m, y - box_h, left_w, box_h)
    c.rect(m + left_w, y - box_h, mid_w, box_h)
    c.rect(right_x, y - box_h, right_w, box_h)

    def party_block(x, name, addr, gstin):
        c.setFont("Sans", 8)
        c.drawString(x + 6, y - 28, "M/s.")
        c.setFont("Sans-Bold", 8)
        c.drawString(x + 28, y - 28, (name or "")[:42])
        c.setFont("Sans", 8)
        yy = y - 40
        for line in (addr or "").splitlines()[:2]:
            c.drawString(x + 6, yy, line[:48])
            yy -= 11
        c.drawString(x + 6, y - box_h + 6, "GSTIN")
        c.setFont("Sans-Bold", 8)
        c.drawString(x + 38, y - box_h + 6, (gstin or "")[:24])

    party_block(m, data["consignor_name"], data["consignor_addr"], data["consignor_gstin"])
    party_block(m + left_w, data["consignee_name"], data["consignee_addr"], data["consignee_gstin"])

    c.setFont("Sans", 8)
    c.drawString(right_x + 8, y - 16, "GR No.")
    c.setFillColorRGB(0.65, 0.08, 0.08)
    c.setFont("Sans-Bold", 12)
    c.drawString(right_x + 46, y - 16, str(data["gr_no"]))
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Sans", 8)
    c.drawString(right_x + 110, y - 16, "Date")
    c.setFont("Sans-Bold", 8)
    c.drawString(right_x + 136, y - 16, data["bill_date"])
    yy = y - 32
    for label, value in [
        ("From", data["from_place"]), ("To", data["to_place"]),
        ("Value of Goods", data["value_of_goods"]), ("Truck No.", data["truck_no"]),
    ]:
        c.setFont("Sans", 8)
        c.drawString(right_x + 8, yy, label)
        c.setFont("Sans-Bold", 8)
        c.drawString(right_x + 82, yy, str(value or "")[:28])
        c.line(right_x + 80, yy - 2, w - m - 8, yy - 2)
        yy -= 12

    table_top = y - box_h
    cols = [70, 240, 70, 70, 80, 75, 80]
    spare = (w - 2 * m) - sum(cols)
    cols[1] += spare
    headers = ["No. of\nPackage", "Contains", "Weight\n(MT)", "Rate\nP.M.T.", "Freight", "Advance", "Balance"]
    footer_top = 86
    c.rect(m, footer_top, w - 2 * m, table_top - footer_top)
    xs = [m]
    for cw in cols[:-1]:
        xs.append(xs[-1] + cw)
    c.setFont("Sans-Bold", 8)
    for i, (cw, head) in enumerate(zip(cols, headers)):
        if i:
            c.line(xs[i], footer_top, xs[i], table_top)
        parts = head.split("\n")
        c.drawCentredString(xs[i] + cw / 2, table_top - 12, parts[0])
        if len(parts) > 1:
            c.drawCentredString(xs[i] + cw / 2, table_top - 22, parts[1])
    c.line(m, table_top - 28, w - m, table_top - 28)

    c.setFont("Sans", 8)
    row_y = table_top - 42
    for row in data["lines"][:6]:
        vals = [
            str(row.get("packages") or ""),
            str(row.get("contains") or ""),
            str(row.get("weight") or ""),
            str(row.get("rate") or ""),
            str(row.get("freight") or ""),
            str(row.get("advance") or ""),
            str(row.get("balance") or ""),
        ]
        for i, val in enumerate(vals):
            if i == 1:
                c.drawString(xs[i] + 4, row_y, val[:48])
            else:
                c.drawCentredString(xs[i] + cols[i] / 2, row_y, val[:16])
        row_y -= 16

    c.setFont("Sans", 8)
    # keep the GST block inside the Contains column, clear of the package line
    contains_x = xs[1] + 16
    c.drawString(contains_x, footer_top + 52, "GST Tax will be Paid by")
    paid = (data.get("gst_paid_by") or "").lower()
    c.drawString(contains_x + 8, footer_top + 36, "+ Consignee")
    c.rect(contains_x + 90, footer_top + 32, 11, 11)
    if "consignee" in paid:
        c.setFont("Sans-Bold", 9)
        c.drawString(contains_x + 92, footer_top + 34, "X")
        c.setFont("Sans", 8)
    c.drawString(contains_x + 8, footer_top + 20, "+ Consignor")
    c.rect(contains_x + 90, footer_top + 16, 11, 11)
    if "consignor" in paid:
        c.setFont("Sans-Bold", 9)
        c.drawString(contains_x + 92, footer_top + 18, "X")

    # Total row: keep the "Total" label in the Contains column, not
    # in the Weight column, so it cannot overlap the total weight.
    total_y = footer_top + 4
    c.line(xs[2], footer_top + 14, w - m, footer_top + 14)
    c.setFont("Sans-Bold", 8)
    c.drawCentredString(xs[1] + cols[1] / 2, total_y, "Total")

    # Each total is drawn only in its matching column.
    total_values = {
        2: data.get("total_weight") or "",  # Weight (MT)
        4: f"{data['total_freight']:.2f}" if data["total_freight"] else "",
        5: f"{data['total_advance']:.2f}" if data["total_advance"] else "",
        6: f"{data['total_balance']:.2f}" if data["total_balance"] else "",
    }
    for col_index, value in total_values.items():
        c.drawCentredString(
            xs[col_index] + cols[col_index] / 2,
            total_y,
            str(value)[:18],
        )

    c.setFont("Hi", 7)
    note = data.get("note_goods") or "______________"
    c.drawString(m + 6, 70, f"नोट: हमने इस गाड़ी में {note} भरवाया है इसके अलावा")
    c.drawString(m + 6, 59, "यदि कोई दूसरा माल भरता है तो इसकी जिम्मेदारी गाड़ी मालिक/ड्राईवर की होगी।")
    c.drawString(m + 6, 48, "वजन 50 किग्रा. से कम होने पर भाड़ा नहीं कटेगा।")

    c.setFont("Sans", 8)
    c.drawString(360, 70, f"Bank    : {COMPANY['bank']}")
    c.drawString(360, 58, f"A/c No. : {COMPANY['ac']}")
    c.drawString(360, 46, f"IFSC    : {COMPANY['ifsc']}")

    c.setStrokeColorRGB(*navy)
    box_w, box_h, box_y = 155, 32, 16
    gap = 10
    box2_x = w - m - 8 - box_w
    box1_x = box2_x - gap - box_w
    c.rect(box1_x, box_y, box_w, box_h)
    c.rect(box2_x, box_y, box_w, box_h)
    if data.get("consignee_sign"):
        try:
            c.drawImage(data["consignee_sign"], box1_x + 18, box_y + 12, width=box_w - 36, height=16, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    if data.get("other_sign"):
        try:
            c.drawImage(data["other_sign"], box2_x + 18, box_y + 12, width=box_w - 36, height=16, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFont("Sans", 7)
    c.drawCentredString(box1_x + box_w / 2, box_y + 3, "Consignee signature")
    c.drawCentredString(box2_x + box_w / 2, box_y + 3, f"For {COMPANY['name']}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()

init_db()
st.set_page_config(page_title="Arora Road Carrier", layout="wide")
st.title("Arora Road Carrier")
st.caption("Landscape GR bill. Fill the form, then Generate Bill.")

def clear_form():
    st.session_state.gr = next_gr()
    st.session_state.gr_input = st.session_state.gr
    st.session_state.truck_no = ""
    st.session_state.from_place = ""
    st.session_state.to_place = ""
    st.session_state.value_of_goods = ""
    st.session_state.bill_date = date.today()
    st.session_state.note_goods = ""
    st.session_state.cr_name = ""
    st.session_state.cr_addr = ""
    st.session_state.cr_gst = ""
    st.session_state.ce_name = ""
    st.session_state.ce_addr = ""
    st.session_state.ce_gst = ""
    st.session_state.gst_paid_by = "Consignee"
    st.session_state.lines = [{"packages": "", "contains": "", "weight": 0.0, "rate": 0.0, "advance": 0.0}]
    st.session_state.line_editor = st.session_state.lines
    st.session_state.generated = None
    st.session_state.form_ver = st.session_state.get("form_ver", 0) + 1

tab_new, tab_hist = st.tabs(["New bill", "History"])

with tab_new:
    if "gr" not in st.session_state:
        st.session_state.gr = next_gr()
    if "form_ver" not in st.session_state:
        st.session_state.form_ver = 0
    ver = st.session_state.form_ver

    top1, top2 = st.columns([1, 1])
    if top1.button("Clear all fields"):
        clear_form()
        st.rerun()

    c1, c2, c3 = st.columns(3)
    gr_no = c1.text_input("GR No.", value=st.session_state.gr, key="gr_input")
    bill_date = c2.date_input("Date", value=date.today(), format="DD-MM-YYYY", key="bill_date")
    truck_no = c3.text_input("Truck No.", key="truck_no")

    left, mid, right = st.columns(3)
    with left:
        st.subheader("Consignor")
        consignor_name = st.text_input("M/s.", key="cr_name")
        consignor_addr = st.text_area("Address", height=80, key="cr_addr")
        consignor_gstin = st.text_input("GSTIN", key="cr_gst")
    with mid:
        st.subheader("Consignee")
        consignee_name = st.text_input("M/s.", key="ce_name")
        consignee_addr = st.text_area("Address", height=80, key="ce_addr")
        consignee_gstin = st.text_input("GSTIN", key="ce_gst")
    with right:
        st.subheader("Trip")
        from_place = st.text_input("From", key="from_place")
        to_place = st.text_input("To", key="to_place")
        value_of_goods = st.text_input("Value of Goods (enter yourself)", placeholder="e.g. 85000", key="value_of_goods")
        gst_paid_by = st.radio("GST Tax will be Paid by", ["Consignee", "Consignor"], horizontal=True, key="gst_paid_by")
        note_goods = st.text_input("Note: हमने इस गाड़ी में ... भरवाया है", placeholder="goods loaded", key="note_goods")

    st.subheader("Signatures")
    s1, s2 = st.columns(2)
    consignee_sign = s1.file_uploader("Consignee signature", type=["png", "jpg", "jpeg"], key=f"sig_ce_{ver}")
    other_sign = s2.file_uploader("Authorised / other signature", type=["png", "jpg", "jpeg"], key=f"sig_ot_{ver}")

    st.subheader("Packages")
    st.caption("Weight is in metric tonne. Freight = weight × rate. Balance = freight − advance.")
    if "lines" not in st.session_state:
        st.session_state.lines = [{"packages": "", "contains": "", "weight": 0.0, "rate": 0.0, "advance": 0.0}]
    edited = st.data_editor(
        st.session_state.lines,
        num_rows="dynamic",
        width='stretch',
        column_config={
            "packages": "No. of Package",
            "contains": "Contains",
            "weight": st.column_config.NumberColumn("Weight (MT)", min_value=0.0, format="%.3f"),
            "rate": st.column_config.NumberColumn("Rate P.M.T.", min_value=0.0, format="%.2f"),
            "advance": st.column_config.NumberColumn("Advance", min_value=0.0, format="%.2f"),
        },
        key="line_editor",
    )

    clean = []
    tf = ta = tb = 0.0
    pkgs, weights = [], []
    for row in edited:
        if not any(str(row.get(k) or "").strip() for k in ("packages", "contains", "weight", "rate")):
            continue
        weight = num(row.get("weight"))
        rate = num(row.get("rate"))
        advance = num(row.get("advance"))
        freight = round(weight * rate, 2)
        balance = round(freight - advance, 2)
        clean.append({
            "packages": row.get("packages") or "",
            "contains": row.get("contains") or "",
            "weight": f"{weight:.3f}" if weight else "",
            "rate": f"{rate:.2f}" if rate else "",
            "freight": f"{freight:.2f}",
            "advance": f"{advance:.2f}",
            "balance": f"{balance:.2f}",
        })
        tf += freight
        ta += advance
        tb += balance
        if row.get("packages"):
            pkgs.append(str(row["packages"]))
        if weight:
            weights.append(f"{weight:.3f}")

    if clean:
        st.dataframe(
            [{"Contains": r["contains"], "MT": r["weight"], "Rate": r["rate"],
              "Freight": r["freight"], "Advance": r["advance"], "Balance": r["balance"]} for r in clean],
            width='stretch', hide_index=True,
        )
    m1, m2, m3 = st.columns(3)
    m1.metric("Total freight", f"{tf:,.2f}")
    m2.metric("Total advance", f"{ta:,.2f}")
    m3.metric("Total balance", f"{tb:,.2f}")

    sig_dir = ROOT / "signatures"
    sig_dir.mkdir(exist_ok=True)
    ce_path = ot_path = ""
    if consignee_sign:
        ce_path = str(sig_dir / f"ce_{gr_no.strip() or 'draft'}.{consignee_sign.name.split('.')[-1]}")
        Path(ce_path).write_bytes(consignee_sign.getvalue())
    if other_sign:
        ot_path = str(sig_dir / f"ot_{gr_no.strip() or 'draft'}.{other_sign.name.split('.')[-1]}")
        Path(ot_path).write_bytes(other_sign.getvalue())

    data = {
        "gr_no": gr_no.strip(),
        "bill_date": bill_date.strftime("%d-%m-%Y"),
        "consignor_name": consignor_name,
        "consignor_addr": consignor_addr,
        "consignor_gstin": consignor_gstin,
        "consignee_name": consignee_name,
        "consignee_addr": consignee_addr,
        "consignee_gstin": consignee_gstin,
        "from_place": from_place,
        "to_place": to_place,
        "value_of_goods": value_of_goods,
        "truck_no": truck_no,
        "gst_paid_by": gst_paid_by,
        "note_goods": note_goods,
        "lines": clean,
        "total_packages": ", ".join(pkgs),
        "total_weight": ", ".join(weights),
        "total_freight": tf,
        "total_advance": ta,
        "total_balance": tb,
        "consignee_sign": ce_path,
        "other_sign": ot_path,
    }

    if st.button("Generate Bill", type="primary"):
        if not data["gr_no"]:
            st.error("GR No. is required.")
        elif not data["value_of_goods"]:
            st.error("Enter the value of goods.")
        elif get_bill(data["gr_no"]):
            st.error("This GR No. is already generated. Change the GR number.")
        else:
            pdf_bytes = pdf_for(data)
            (PDF_DIR / f"GR-{data['gr_no']}.pdf").write_bytes(pdf_bytes)
            save_bill(data)
            st.session_state.generated = {"gr": data["gr_no"], "pdf": pdf_bytes}
            st.session_state.gr = next_gr()
            st.success(f"Bill generated. GR {data['gr_no']} is saved in History.")

    generated = st.session_state.get("generated")
    if generated:
        st.subheader(f"GR {generated['gr']}")
        st.download_button("Download PDF", data=generated["pdf"], file_name=f"GR-{generated['gr']}.pdf", mime="application/pdf")
        show_pdf(generated["pdf"])

with tab_hist:
    q = st.text_input("Search GR, party, place or truck")
    rows = list_bills(q.strip())
    if not rows:
        st.info("No bills yet.")
    else:
        st.dataframe([{
            "GR": r["gr_no"], "Date": r["bill_date"], "Consignor": r["consignor_name"],
            "Consignee": r["consignee_name"], "From": r["from_place"], "To": r["to_place"],
            "Truck": r["truck_no"], "Balance": r["total_balance"], "Saved": r["created_at"],
        } for r in rows], width='stretch', hide_index=True)
        pick = st.selectbox("Open a saved bill", [r["gr_no"] for r in rows])
        bill = get_bill(pick)
        if bill:
            st.write(f"**{bill['consignor_name']} → {bill['consignee_name']}**  ·  {bill['from_place']} to {bill['to_place']}")
            path = PDF_DIR / f"GR-{pick}.pdf"
            if path.exists():
                pdf_bytes = path.read_bytes()
            else:
                old = dict(bill)
                old["lines"] = json.loads(old["lines_json"] or "[]")
                old["consignee_sign"] = ""
                old["other_sign"] = ""
                pdf_bytes = pdf_for(old)
                path.write_bytes(pdf_bytes)
            st.download_button(f"Download GR {pick} PDF", data=pdf_bytes, file_name=f"GR-{pick}.pdf", mime="application/pdf", key=f"dl-{pick}")
            if st.button("View online", key=f"view-{pick}"):
                st.session_state.view_gr = pick
            if st.session_state.get("view_gr") == pick:
                show_pdf(pdf_bytes)
