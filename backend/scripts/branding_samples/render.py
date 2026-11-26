"""
Branding sample PDFs from the current tree, dummy data only (fictional
clinic, patients and line drawings; no network, no database).

    cd backend && python scripts/branding_samples/render.py <output folder>

Writes Rx.pdf (3 exercises per page), Invoice.pdf, Receipt-part-payment.pdf,
Posture.pdf, Psychosocial.pdf and Logo-contact-sheet.pdf. "SAMPLE" appears
only as a tiny muted line above the clinic block (invoice / receipt: in the
footer line).
"""
import base64, sys, os, tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from app.core.upload_limits import MAX_LOGO_BYTES
from app.services import report_letterhead as rl
from app.services import prescription_pdf as rx
import assets as _assets
A = tempfile.mkdtemp(prefix="branding-assets-"); _assets.OUT = A
OUT = ""
IST = ZoneInfo("Asia/Kolkata")

def uri(fn):
    mime = "image/jpeg" if fn.endswith(".jpg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(open(f"{A}/{fn}", "rb").read()).decode()

def stored_logo(fn):
    return rl.prepare_uploaded_logo(uri(fn), MAX_LOGO_BYTES)

CLINIC = dict(clinic_name="Sukoon Physiotherapy & Rehabilitation Centre", phone="+91 98110 42375",
    email="care@sukoonphysio.in", address_line="Plot 14, Sector 50 Market, Near Metro Gate 2", city="Noida",
    state="Uttar Pradesh", pincode="201301", website="https://www.sukoonphysio.in/", display_doctor_name="Dr. Meera Raghavan (PT)")

def sample(html):
    """Tiny muted SAMPLE line above the clinic block (on the report number line)."""
    return html.replace('<p class="reportno">', '<p class="reportno"><span style="float: right; font-size: 6.5pt; letter-spacing: 1px">SAMPLE</span>', 1)

def rx_doc(logo="logo_round.png", mode="as_is"):
    items = [
        ("glute bridge", "Hips", "Lie on your back with knees bent and feet flat. Squeeze your buttocks and lift your hips until your body is in a straight line from shoulders to knees. Lower slowly.", 3, 12, 5, "Twice daily", None, "bridge", None),
        ("wall supported mini squat", "Knee", "Stand with your back against a wall, feet hip width apart. Slide down slowly until your knees are bent to about 45 degrees, keep knees over toes, then slide back up.", 3, 10, 3, "Once daily", "Stop at a smaller bend if the front of the knee hurts.", "squat", None),
        ("chin tuck", "Neck", "Sit tall. Gently draw your chin straight back, as if making a double chin, without tipping the head down. Feel the stretch at the base of the skull.", 2, 10, 5, "3 times a day", None, "chin", None),
        ("side lying clamshell", "Hip", "Lie on your side with knees bent and heels together. Keeping the feet together, lift the top knee as far as you can without rolling the pelvis back. Lower with control.", 3, 15, 2, "Once daily", None, "clam", "left"),
        ("standing calf stretch", "Ankle", "Face a wall with hands on it. Step one leg back, keep the heel down and knee straight, and lean forward until you feel the stretch in the calf.", 2, 3, 30, "Twice daily", None, "stretch", "right"),
    ]
    its = []
    for t, part, ins, s, r, h, fq, note, img, side in items:
        it = rx.RxItem(title=t, body_part=part, instructions=ins, sets=s, reps=r, hold=h, frequency=fq, note=note, image_url=None, side=side)
        it.image_src = rx._shrink_to_data_uri(open(f"{A}/ex_{img}.jpg", "rb").read())
        its.append(it)
    d = rx.RxDoc(rx_id="7b825459-1111-2222-3333-444455556666", physio_name="Dr. Arjun Mehta (PT)", patient_name="Kavita Sharma",
        patient_phone=None, patient_dob=None, patient_age=46, patient_sex="female", prescribed_on=datetime(2026, 11, 26, 11, 30, tzinfo=IST),
        physio_notes="Start with the lower number of repetitions for the first three days. Apply a warm pack for 10 minutes before the session if the back feels stiff.",
        items=its, patient_id="SPC-000128", document_number="SPC-RX-000042", logo_bg_mode=mode, **CLINIC)
    d.clinic_logo_src = rl.render_logo_for_mode(stored_logo(logo), mode)
    return d

def render_rx(name):
    html = sample(rx.build_prescription_html(rx_doc()))
    open(f"{OUT}/{name}", "wb").write(rx._render(html))


from app.services import invoice_pdf as inv
from decimal import Decimal as D

def inv_doc(kind):
    pays = [inv.ReceiptPayment(paid_on=datetime(2026, 11, 20, 18, 5, tzinfo=IST), method="upi", reference="UPI 432918776521", amount=D("3000.00"), receipt_number="RCP-2627-000017"),
            inv.ReceiptPayment(paid_on=datetime(2026, 11, 26, 12, 40, tzinfo=IST), method="cash", reference=None, amount=D("2000.00"), receipt_number="RCP-2627-000019")]
    d = inv.InvoiceDoc(kind=kind, invoice_number="INV-2627-000031", status="partially_paid", issue_date=datetime(2026, 11, 20, 17, 50, tzinfo=IST),
        due_date=datetime(2026, 12, 5, 12, 0, tzinfo=IST), clinic_name=CLINIC["clinic_name"], patient_name="Rohit Verma", patient_phone="+91 98990 51234",
        patient_id="SPC-000131", address_line=CLINIC["address_line"], city="Noida", state="Uttar Pradesh", pincode="201301", phone=CLINIC["phone"],
        email=CLINIC["email"], registration_number="UP/PT/2019/0457", gstin="09ABCDE1234F1Z5", authorised_person="Dr. Meera Raghavan",
        subtotal=D("8200.00"), discount_amount=D("820.00"), discount_percent=D("10"), tax_amount=D("0"), total_amount=D("7380.00"), paid_amount=D("5000.00"),
        items=[inv.InvoiceLine("Physiotherapy session (45 min)", 6, D("1200.00"), D("7200.00")), inv.InvoiceLine("Initial assessment", 1, D("1000.00"), D("1000.00"))],
        payments=pays)
    d.payment = pays[1] if kind == "receipt" else None
    d.clinic_logo_src = rl.render_logo_for_mode(stored_logo("logo_round.png"), "as_is")
    return d

def render_inv():
    for k, n in (("invoice", "Invoice.pdf"), ("receipt", "Receipt-part-payment.pdf")):
        html = inv.build_invoice_html(inv_doc(k)).replace('@bottom-center { content: "Powered by', '@bottom-center { content: "SAMPLE  ·  Powered by', 1)
        open(f"{OUT}/{n}", "wb").write(inv._render(html))


def posture_report():
    from app.services.posture import report_builder as rb
    from app.services.posture.synthesizer import generate_synthesis
    M = rb.measurement
    side = [M("PT-L01", "Head Position (ear–shoulder angle)", 48.2, "°", "under_review"), M("PT-L05", "Knee Hyperextension", 4.1, "°", "none"),
            M("PT-L06", "Trunk Lean", 6.8, "°", "mild", "forward")]
    front = [M("PT-A01", "Head Tilt", 3.9, "°", "mild", "right"), M("PT-A04", "Pelvic Obliquity", 2.2, "°", "none"),
             M("PT-A05", "Left Knee Alignment", 9.6, "°", "moderate", "valgus"), M("PT-A06", "Right Knee Alignment", 5.4, "°", "mild", "valgus")]
    back = [M("PT-P01", "Shoulder Level Asymmetry", 11.0, "mm", "under_review"), M("PT-P02", "Trunk Shift", 7.5, "mm", "mild", "left")]
    v = lambda ms, k: rb.build_side_view_result(ms, uri(f"posture_{k}.jpg"), 0.93, "camera")
    findings = {m["paramId"]: m["severity"] for m in side + front + back}
    patient = {"name": "Anil Kapoor", "age": 52, "gender": "Male", "heightCm": 171, "caseRef": "SPC-000119",
               "assessmentDate": "2026-11-26", "clinician": "Dr. Arjun Mehta (PT)"}
    r = rb.build_report_response(patient, v(side, "side"), v(front, "front"), v(back, "back"), generate_synthesis(findings))
    r["reportId"] = "SPC-POS-000017"
    return r

def render_posture():
    from app.services.posture import pdf_service as ps
    brand = rl.ClinicBrand(name=CLINIC["clinic_name"], logo_src=rl.render_logo_for_mode(stored_logo("logo_round.png"), "as_is"),
        doctor_name=CLINIC["display_doctor_name"], phone=CLINIC["phone"], email=CLINIC["email"],
        address=rl.format_address(CLINIC["address_line"], "Noida", "Uttar Pradesh", "201301"), website=CLINIC["website"])
    html = sample(ps.build_report_html(posture_report(), {"brand": brand}))
    from weasyprint import HTML
    open(f"{OUT}/Posture.pdf", "wb").write(HTML(string=html).write_pdf())


def render_psy():
    import dataclasses, uuid
    from datetime import timedelta
    from types import SimpleNamespace as NS
    from app.services import psychosocial_report as ps
    from app.screening.registry import get_instrument
    from app.screening.scoring import score
    from app.screening.trend import build_series
    plans = [("phq9", [2, 2, 1, 2, 1, 2, 1, 1, 0], 0), ("gad7", [2, 2, 2, 1, 2, 1, 1], 0),
             ("phq9", [1, 2, 1, 1, 1, 1, 1, 1, 0], 21), ("gad7", [1, 1, 2, 1, 1, 1, 1], 21),
             ("phq9", [1, 1, 1, 1, 0, 1, 0, 1, 0], 42), ("gad7", [1, 1, 1, 0, 1, 1, 0], 42)]
    start = datetime(2026, 10, 15, 11, 0, tzinfo=IST)
    sessions, rows = [], []
    for iid, vals, day in plans:
        inst = get_instrument(iid)
        items = [it.id for it in inst.items]
        resp = {k: (vals[i] if i < len(vals) else 0) for i, k in enumerate(items)}
        r = score(inst, resp)
        res = {"scales": [dataclasses.asdict(x) for x in r.scales]}
        s_ = NS(id=uuid.uuid4(), instrument_id=iid, instrument_version=inst.version, completed_at=start + timedelta(days=day), result=res,
                referral_flag=r.referral_flag, risk_item_flag=r.risk_item_flag)
        sessions.append(s_)
        rows.append(ps.SessionRow(completed_at=s_.completed_at, short_name=inst.short_name,
            scales=[(x["label"].replace("DASS-21 ", ""), x["score"], x["max_score"], x["band_label"]) for x in res["scales"]], referral=r.referral_flag, risk=r.risk_item_flag))
    refs = [ps.ReferralRow(recorded_at=start + timedelta(days=1), screener="PHQ-9", screener_date=start, action=ps.REFERRAL_LABELS["referred_psychologist"],
            note="Patient agreed to a consultation; shared the clinic's referral letter.", by="Dr. Arjun Mehta (PT)", contact="Ms. Neha Iyer (Clinical psychologist)"),
            ps.ReferralRow(recorded_at=start + timedelta(days=43), screener="PHQ-9", screener_date=start + timedelta(days=42), action=ps.REFERRAL_LABELS["monitor_and_rescreen"],
            note=None, by="Dr. Arjun Mehta (PT)")]
    brand = rl.ClinicBrand(name=CLINIC["clinic_name"], logo_src=rl.render_logo_for_mode(stored_logo("logo_round.png"), "as_is"),
        doctor_name=CLINIC["display_doctor_name"], phone=CLINIC["phone"], email=CLINIC["email"],
        address=rl.format_address(CLINIC["address_line"], "Noida", "Uttar Pradesh", "201301"), website=CLINIC["website"])
    data = ps.ReportData(report_id="SPC-PSY-000008", clinic_name=CLINIC["clinic_name"], patient_name="Kavita Sharma", patient_details=[],
        generated_at=datetime(2026, 11, 26, 16, 10, tzinfo=IST), generated_by="Dr. Arjun Mehta (PT)", own_scope=False, series=build_series(sessions),
        sessions=rows, referrals=refs, brand=brand, patient_code="SPC-000128", age_sex=rl.age_sex_text(46, "female"))
    open(f"{OUT}/Psychosocial.pdf", "wb").write(ps._render(sample(ps.build_report_html(data))))


def render_sheet():
    from app.services.brand import font_faces
    from weasyprint import HTML
    css = rl.clinical_page_css(rl.ClinicBrand(), watermark=False).replace("position: running(clinicalBand);", "")
    rows = []
    for fn, label in (("logo_round.png", "Round (white background, PNG)"), ("logo_square.png", "Square (transparent, PNG)"),
                      ("logo_wide.png", "Wide 3.75:1 (transparent, dark text)"), ("logo_tall.jpg", "Tall 1:3 (cream background, JPG)")):
        stored = stored_logo(fn)
        for mode in rl.LOGO_BG_MODES:
            src = rl.render_logo_for_mode(stored, mode)
            c = int(rl.logo_low_contrast_share(src) * 100)
            warn = " | Settings warns" if rl.logo_needs_contrast_warning(src, mode) else ""
            b = rl.ClinicBrand(name="x", logo_src=src, logo_bg_mode=mode, doctor_name=CLINIC["display_doctor_name"], phone=CLINIC["phone"], email=CLINIC["email"])
            rows.append(f'<p class="cap">{label} &middot; mode <b>{mode}</b> &middot; outline under 3:1: {c}%{warn}</p>{rl.clinical_band_html(b)}')
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{font_faces()}{css}
    @page {{ margin: 10mm 0 10mm 0; @top-center {{ content: none; }} @bottom-center {{ content: "SAMPLE  ·  Logo contact sheet: 4 shapes x 3 background modes"; font-size: 7pt; color: #555; }} }}
    .cap {{ font-size: 8pt; margin: 2.2mm 14mm 1mm 14mm; color: #333; }} .cl-band {{ page-break-inside: avoid; }}</style></head><body style="padding:0">{''.join(rows)}</body></html>"""
    open(f"{OUT}/Logo-contact-sheet.pdf", "wb").write(HTML(string=html).write_pdf())



def main() -> None:
    global OUT
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/branding_samples/render.py <output folder>")
    OUT = os.path.abspath(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    _assets.logos()
    for pose in ("bridge", "squat", "chin", "clam", "stretch"):
        _assets.figure(pose, pose)
    for view in ("side", "front", "back"):
        _assets.posture_photo(view)
    render_rx("Rx.pdf")
    render_inv()
    render_posture()
    render_psy()
    render_sheet()
    print("\n".join(sorted(f for f in os.listdir(OUT) if f.endswith(".pdf"))))


if __name__ == "__main__":
    main()
