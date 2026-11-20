"""Demo clinic seed for staging and local testing (launch-plan EN-1).

    cd backend
    python tests/seed.py --staging            # create the demo clinic
    python tests/seed.py --staging --reset    # delete the demo clinic, then create it again

One command, no forms: "AV Demo Physio" with an admin, a therapist (all three
tool checkboxes) and a front desk user, 30 leads (5 converted), 20 patients,
about 40 appointments (last 14 days and next 7), treatment notes, invoices,
payments (full, partial, none), exercise prescriptions built from exercises
already in the database, and posture sessions.

Safety (scripts/safety.py): needs --staging, refuses a production
ENVIRONMENT, and refuses any database that is not local or the confirmed
staging fingerprint. The seed never truncates or touches other clinics:
--reset deletes only the demo clinic (slug av-demo-physio) and the
@physiodemo.in accounts that belong to no other clinic.

Demo phones: one fixed series 90000 00000.. (leads 9000000000-29, patients
9000000100-114), so testers can tell demo rows from real ones.

Logins: every demo user has the same password, AV_SEED_PASSWORD if set,
else a generated one printed at the end (demo accounts only).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import secrets
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.safety import guard_or_exit  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
DEMO_SLUG = "av-demo-physio"
DEMO_DOMAIN = "physiodemo.in"
RNG_SEED = 20261120

DEMO_CONFIG = {
    "clinic": {
        "slug": DEMO_SLUG,
        "name": "AV Demo Physio",
        "branding_color": "#0d9488",
        "client_type": "clinic",
        "address_line": "B-14, Sector 63",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "pincode": "201301",
        "phone": "+91 98100 12345",
        "email": f"hello@{DEMO_DOMAIN}",
        "authorised_person": "Dr. Neha Kapoor (PT)",
    },
    "tools": [
        "crm",
        "exercise-library",
        "exercise-prescription",
        "posture-tool",
        "psycho-social-screening",
    ],
    "users": [
        {"email": f"admin@{DEMO_DOMAIN}", "first_name": "Neha", "last_name": "Kapoor", "role": "admin"},
        {
            "email": f"therapist@{DEMO_DOMAIN}",
            "first_name": "Arjun",
            "last_name": "Malhotra",
            "role": "therapist",
            "tools": ["exercise-library", "posture-tool", "psycho-social-screening"],
        },
        {"email": f"frontdesk@{DEMO_DOMAIN}", "first_name": "Pooja", "last_name": "Rawat", "role": "front_desk"},
    ],
}

FIRST = ["Aarav", "Diya", "Rohan", "Ananya", "Vikram", "Isha", "Kabir", "Meera", "Aditya", "Sneha",
         "Rahul", "Priya", "Karan", "Nisha", "Varun", "Kavya", "Siddharth", "Tanvi", "Manish", "Ritu",
         "Harsh", "Simran", "Yash", "Pallavi", "Gaurav", "Shreya", "Amit", "Neelam", "Deepak", "Anjali",
         "Sahil", "Komal", "Rajat", "Swati", "Nikhil", "Jyoti"]
LAST = ["Sharma", "Patel", "Mehta", "Verma", "Gupta", "Singh", "Iyer", "Reddy", "Chopra", "Bansal",
        "Joshi", "Nair", "Agarwal", "Malik", "Saxena", "Khanna", "Bhatia", "Rao"]
COMPLAINTS = [
    "Lower back pain after long desk hours", "Right shoulder pain on overhead reach",
    "Neck stiffness, worse in the morning", "Left knee pain on stairs", "Post ACL reconstruction rehab (week 6)",
    "Plantar heel pain, first steps in the morning", "Tennis elbow, right side", "Sciatica, left leg",
    "Frozen shoulder, left", "Ankle sprain follow-up", "Postural pain, rounded shoulders",
    "Post-natal back pain", "Hamstring strain (sports)", "Cervical radiculopathy, right arm tingling",
]
LEAD_NOTES = [
    "Asked about fees for a 10-session package.", "Wants an evening slot after 6 pm.",
    "Referred by an orthopaedic surgeon.", "Saw the clinic on Instagram.", "Called twice, prefers WhatsApp.",
    "Needs a weekend appointment.", "Asked if home visits are possible.", None,
]
FEES = [("Physiotherapy session", Decimal("800")), ("Initial assessment", Decimal("1000")),
        ("Dry needling", Decimal("600")), ("Kinesio taping", Decimal("300")),
        ("Posture assessment", Decimal("1200"))]
TREATMENTS = [
    ("IFT + lumbar mobilisation + core activation", "Pelvic tilts 2x10 twice daily. Avoid sitting over 40 min."),
    ("Shoulder mobilisation + rotator cuff strengthening", "Theraband ER/IR 3x12 daily."),
    ("Cervical traction + chin tucks", "Chin tucks hourly at work, 10 reps."),
    ("Quadriceps strengthening + patellar taping", "Straight leg raises 3x15, ice 10 min after."),
    ("Ultrasound + calf and plantar fascia stretching", "Calf stretch 3x30 s, frozen bottle roll."),
]


def _print_clean(line: str) -> None:
    print(line, flush=True)


async def demo_clinic_id():
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic

    async with AsyncSessionLocal() as db:
        return await db.scalar(select(Clinic.id).where(Clinic.slug == DEMO_SLUG))


async def reset_demo() -> None:
    """Delete the demo clinic and its own accounts. Nothing else."""
    from sqlalchemy import text

    from app.core.database import AsyncSessionLocal

    clinic_id = await demo_clinic_id()
    async with AsyncSessionLocal() as db:
        if clinic_id is not None:
            # Many child FKs are not ON DELETE CASCADE, so delete every row with
            # this clinic_id table by table, retrying in passes until the FK
            # order works out. Each delete is scoped to the demo clinic only.
            tables = (
                await db.execute(
                    text(
                        "SELECT c.table_name FROM information_schema.columns c "
                        "JOIN information_schema.tables t ON t.table_name = c.table_name "
                        "AND t.table_schema = c.table_schema "
                        "WHERE c.table_schema = 'public' AND c.column_name = 'clinic_id' "
                        "AND t.table_type = 'BASE TABLE' ORDER BY 1"
                    )
                )
            ).scalars().all()
            pending = list(tables)
            for _ in range(len(tables) + 1):
                failed = []
                for table in pending:
                    try:
                        async with db.begin_nested():
                            await db.execute(
                                text(f'DELETE FROM "{table}" WHERE clinic_id = :id'), {"id": clinic_id}
                            )
                    except Exception:  # FK order: retry in the next pass
                        failed.append(table)
                if not failed:
                    break
                if len(failed) == len(pending):
                    raise RuntimeError(f"reset: could not clear demo rows in {failed}")
                pending = failed
            await db.execute(text("DELETE FROM clinics WHERE id = :id AND slug = :slug"),
                             {"id": clinic_id, "slug": DEMO_SLUG})
        # Demo accounts that no longer belong to any clinic.
        await db.execute(
            text(
                "DELETE FROM users u WHERE u.email LIKE :pattern "
                "AND NOT EXISTS (SELECT 1 FROM memberships m WHERE m.user_id = u.id)"
            ),
            {"pattern": f"%@{DEMO_DOMAIN}"},
        )
        await db.commit()
    _print_clean(f"reset: demo clinic {DEMO_SLUG} {'deleted' if clinic_id else 'was not there'}")


def demo_phone(n: int) -> str:
    """One fixed fake series, 90000 00000 to 90000 00999: easy to spot as demo data."""
    return f"90000{n:05d}"


def ist(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm), tzinfo=IST)


async def pick_exercises(limit: int = 40) -> list[str]:
    """Exercises already in the DB: global ones with an image link first, Blogspot links last."""
    from sqlalchemy import case, select

    from app.core.database import AsyncSessionLocal
    from app.models.exercise import Exercise

    image_like = Exercise.video_url.op("~*")(r"\.(png|jpe?g|webp|gif)(\?|$)")
    blogspot = Exercise.video_url.op("~*")("blogspot|blogger")
    async with AsyncSessionLocal() as db:
        rows = (
            await db.scalars(
                select(Exercise.id)
                .where(Exercise.clinic_id.is_(None))
                .order_by(
                    case((image_like & ~blogspot, 0), else_=1),
                    case((blogspot, 1), else_=0),
                    Exercise.title,
                )
                .limit(limit)
            )
        ).all()
    return [str(r) for r in rows]


async def add_posture_sessions(clinic_id, patient_ids: list[str], rng: random.Random) -> int:
    from app.core.database import AsyncSessionLocal
    from app.schemas.posture import PostureMeasurementCreate, PostureSessionCreate
    from app.services.posture.reference_ranges import THRESHOLDS, UNITS
    from app.services.posture_service import create_posture_session

    def value_for(rule: dict) -> float:
        if rule["direction"] == "centred":
            return round(rng.uniform(rule["moderate_low"], rule["moderate_high"]), 1)
        if rule["direction"] == "lower_worse":
            return round(rng.uniform(rule["moderate_min"] - 3, rule["none_min"] + 8), 1)
        return round(rng.uniform(0, rule["moderate_max"]), 1)

    count = 0
    async with AsyncSessionLocal() as db:
        for pid in patient_ids:
            measurements = [
                PostureMeasurementCreate(metric_name=param, value=value_for(rule), unit=UNITS.get(param))
                for param, rule in THRESHOLDS.items()
            ]
            await create_posture_session(
                db,
                clinic_id,
                PostureSessionCreate(patient_id=pid, overall_confidence=round(rng.uniform(0.82, 0.97), 2),
                                     measurements=measurements),
            )
            count += 1
    return count


async def seed(password: str) -> dict[str, int]:
    from scripts.clinic_setup import Api, apply_config, parse_config

    rng = random.Random(RNG_SEED)
    today = datetime.now(IST).date()

    cfg = parse_config(DEMO_CONFIG, BACKEND_DIR)
    result = await apply_config(cfg, dry_run=False, password_for=lambda _e: password)
    clinic_id = result.clinic_id
    therapist_id = str(result.user_ids[f"therapist@{DEMO_DOMAIN}"])
    counts = {k: 0 for k in ("leads", "converted", "patients", "appointments", "treatments",
                             "invoices", "payments", "prescriptions", "posture_sessions")}

    async with Api(result.owner_id, clinic_id, "admin") as api:
        # ---- leads (30): 5 converted to patients
        names = rng.sample([(f, l) for f in FIRST for l in LAST], 50)
        stages = ["new"] * 8 + ["contacted"] * 7 + ["qualified"] * 6 + ["lost"] * 4 + ["convert"] * 5
        sources = ["website", "referral", "social_media", "walk_in", "advertisement", "other"]
        lost_reasons = ["better_price", "too_far", "timing_mismatch", "call_not_picked"]
        patient_ids: list[str] = []
        for i, stage in enumerate(stages):
            first, last = names[i]
            body = {
                "name": f"{first} {last}",
                "phone": demo_phone(i),
                "email": f"{first.lower()}.{last.lower()}{i}@example.com" if i % 3 else None,
                "source": sources[i % len(sources)],
                "stage": "qualified" if stage == "convert" else stage,
                "notes": LEAD_NOTES[i % len(LEAD_NOTES)],
                "assigned_to": therapist_id if i % 2 else None,
            }
            if stage == "lost":
                body["lost_reason"] = lost_reasons[i % len(lost_reasons)]
            lead = await api.call("POST", "/leads", json=body)
            counts["leads"] += 1
            if stage == "convert":
                converted = await api.call("POST", f"/leads/{lead['id']}/convert")
                patient_ids.append(str(converted["patient_id"]))
                counts["converted"] += 1

        # ---- patients (15 more = 20)
        for j in range(15):
            first, last = names[30 + j]
            age = rng.randint(19, 72)
            patient = await api.call(
                "POST",
                "/patients",
                json={
                    "first_name": first,
                    "last_name": last,
                    "phone": demo_phone(100 + j),
                    "gender": rng.choice(["male", "female"]),
                    "age": age,
                    "date_of_birth": date(today.year - age, rng.randint(1, 12), rng.randint(1, 28)).isoformat(),
                    "chief_complaint": rng.choice(COMPLAINTS),
                    "referral_source": rng.choice(["Google", "Doctor referral", "Friend", "Instagram"]),
                },
            )
            patient_ids.append(str(patient["id"]))
        counts["patients"] = len(patient_ids)

        # ---- appointments: 2 per patient, one past and one future/past
        completed: list[tuple[str, str, datetime]] = []
        slot_used: set[datetime] = set()

        def free_slot(day: date) -> datetime:
            while True:
                at = ist(day, rng.randint(9, 18), rng.choice([0, 30]))
                if at not in slot_used:
                    slot_used.add(at)
                    return at

        for k, pid in enumerate(patient_ids):
            past_day = today - timedelta(days=rng.randint(1, 14))
            plan = [("past", past_day)]
            plan.append(("future", today + timedelta(days=0 if k % 4 == 1 else rng.randint(1, 7))) if k % 2 else
                        ("past", today - timedelta(days=rng.randint(1, 14))))
            for kind, day in plan:
                at = free_slot(day)
                if kind == "future":
                    status_ = "scheduled"
                else:
                    status_ = "no_show" if k % 9 == 4 else "cancelled" if k % 11 == 6 else "completed"
                appt = await api.call(
                    "POST",
                    "/appointments",
                    json={
                        "patient_id": pid,
                        "therapist_id": therapist_id,
                        "scheduled_at": at.isoformat(),
                        "duration_minutes": 45,
                        "status": status_,
                    },
                )
                counts["appointments"] += 1
                if status_ == "completed":
                    completed.append((pid, str(appt["id"]), at))

        # ---- treatment notes for the first 12 completed visits
        for pid, appt_id, at in completed[:12]:
            treat, advice = rng.choice(TREATMENTS)
            await api.call(
                "POST",
                "/treatments",
                json={
                    "patient_id": pid,
                    "appointment_id": appt_id,
                    "therapist_id": therapist_id,
                    "treatment_date": at.isoformat(),
                    "pain_score": rng.randint(2, 7),
                    "treatment": treat,
                    "home_advice": advice,
                    "notes": "Tolerated well. Review next visit.",
                    "finalized": True,
                },
            )
            counts["treatments"] += 1

        # ---- invoices for 15 completed visits; payments full / partial / none
        for n, (pid, appt_id, at) in enumerate(completed[:15]):
            items = [{"description": "Physiotherapy session", "quantity": 1, "unit_price": "800"}]
            if n % 3 == 0:
                desc, price = FEES[1]
                items.append({"description": desc, "quantity": 1, "unit_price": str(price)})
            if n % 4 == 1:
                desc, price = rng.choice(FEES[2:])
                items.append({"description": desc, "quantity": 1, "unit_price": str(price)})
            body = {"patient_id": pid, "appointment_id": appt_id, "issue_date": at.isoformat(), "items": items}
            if n % 5 == 2:
                body["discount_percent"] = "10"
                body["discount_amount"] = str(
                    (sum(Decimal(i["unit_price"]) * i["quantity"] for i in items) * Decimal("0.10")).quantize(Decimal("0.01"))
                )
            invoice = await api.call("POST", "/invoices", json=body)
            counts["invoices"] += 1
            total = Decimal(str(invoice["total_amount"]))
            if n % 5 in (0, 1, 2):
                amount = total
            elif n % 5 == 3:
                amount = (total / 2).quantize(Decimal("1"))
            else:
                continue
            await api.call(
                "POST",
                f"/invoices/{invoice['id']}/payments",
                json={
                    "invoice_id": invoice["id"],
                    "patient_id": pid,
                    "amount": str(amount),
                    "payment_method": ["upi", "cash", "card"][n % 3],
                    "payment_date": at.isoformat(),
                    "transaction_reference": f"UPI{rng.randint(10**9, 10**10 - 1)}" if n % 3 == 0 else None,
                },
            )
            counts["payments"] += 1

        # ---- exercise prescriptions (exercises already in the DB)
        exercise_ids = await pick_exercises()
        if len(exercise_ids) < 3:
            _print_clean("WARNING: fewer than 3 exercises in the database; prescriptions skipped.")
        else:
            for pid in patient_ids[:8]:
                chosen = rng.sample(exercise_ids, k=min(len(exercise_ids), rng.randint(3, 5)))
                await api.call(
                    "POST",
                    "/prescriptions",
                    json={
                        "patient_id": pid,
                        "physio_notes": "Do the programme once daily. Stop if pain goes above 5/10.",
                        "items": [
                            {"exercise_id": ex, "sets": 3, "reps": rng.choice([10, 12, 15]),
                             "hold": rng.choice([0, 5, 10]), "frequency": "Once daily"}
                            for ex in chosen
                        ],
                    },
                )
                counts["prescriptions"] += 1

    # ---- posture sessions (no clinic route stores sessions today: service call)
    counts["posture_sessions"] = await add_posture_sessions(clinic_id, patient_ids[:6], rng)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the AV Demo Physio clinic (staging / local only).")
    parser.add_argument("--staging", action="store_true", help="required: confirms a staging or local database")
    parser.add_argument("--reset", action="store_true", help="delete the demo clinic first, then seed again")
    args = parser.parse_args(argv)

    target = guard_or_exit(staging_flag=args.staging)
    _print_clean(f"target database: {target.fingerprint}")

    password = os.environ.get("AV_SEED_PASSWORD") or secrets.token_urlsafe(10)

    async def run() -> int:
        if args.reset:
            await reset_demo()
        elif await demo_clinic_id() is not None:
            _print_clean(f"Demo clinic {DEMO_SLUG} already exists. Nothing written. Use --reset to rebuild it.")
            return 0
        counts = await seed(password)
        _print_clean("seeded: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
        _print_clean(f"Logins (password for all: {password}):")
        for user in DEMO_CONFIG["users"]:
            _print_clean(f"  {user['role']:<11} {user['email']}")
        return 0

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
