"""
Build the frozen data for Migration B (EL-D-016, EL-D-017) from the D1-D4 CSVs.

    python alembic/data/build_el_migration_b.py \
        --prod-export prod_exercises_20Nov.csv \
        --desc-p0-mapped desc_p0_mapped.csv \
        --d4 D4_descriptions.csv \
        --out alembic/data/el_descriptions_20nov.py \
        D1_descriptions.csv D2_descriptions.csv D3_descriptions.csv

Steps (Onkar 20 Nov 10:30):
1. D1-D4 through build_el_descriptions.build(): refuse > 30 words and
   "prescribed", skip EDIT-SUGGEST, empty and test-clinic rows; D1-D3 wins
   over D4 for a prod row.
2. desc_p0 (169 rows, exact AV-EX -> prod id in desc_p0_mapped.csv) wins over
   the D chats' hand match: a mapped row whose D text is another mapped row's
   desc_p0 text gets its own desc_p0 text. A row outside the map that carries
   a mapped row's desc_p0 text keeps it only when it is a "(seated)" /
   "(supported)" copy of that same exercise; otherwise it takes the D4 text
   of its matched bank row, and with no D4 text it is left without a
   description and listed for Onkar.
3. Running and agility prod rows matched to a bank row take the D4 text.
4. QA: refuse "the therapist" in a PATIENT row.
5. HIDDEN: "(seated)" copies that cannot be done seated (list below, D2 flags
   plus the same rule on D1 / D3 ranges, reviewed by hand).
6. Body part fixes (D2 flags) and the one rename (row 660).
7. Extra BLOCKED rows: head-down postural drainage (RES-THO-01340, 01341).
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import pprint
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_el_descriptions", HERE / "build_el_descriptions.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

RENAME = (B.LATERAL_FLEXION_ID, "Neck side-bend isometric (right)")
# (prod title, new body part) from D2_flags.csv; row 660's body part moved in e7c3a9f1b5d2.
BODY_PART = [
    ("Hamstring stretch standing (supported)", "Legs"),  # D2 flags
    # D1 / D3 notes (20 Nov): copies disagreed with their base row; the odd
    # value (one-off SQL row or wrong region) moves to the family's value.
    ("Biceps curl", "Elbow"), ("Double-leg heel raise", "Ankle & Foot"), ("Cat-camel", "Thoracic"),
    ("Glute set", "Hip"), ("Glute set (supported)", "Hip"),
    ("Calf raise", "Ankle & Foot"), ("Calf raise (supported)", "Ankle & Foot"),
    ("Wall push-up", "Shoulder"), ("Wall angels (seated)", "Shoulder"), ("Wall angels (supported)", "Shoulder"),
    ("Sit-to-stand (supported)", "Knee"),
]
# Onkar 20 Nov 17:47: text for the 8 rows left empty (prod title or bank key).
DESC_OVERRIDE = {
    "Open book (seated)": "Sit tall with your arms crossed on your chest. Turn your upper body to one side, opening the chest and following with your eyes. Keep your hips facing forward.",
    "Prone T": "Lie face down with your arms out to the sides at shoulder level, thumbs up. Squeeze your shoulder blades together and lift both arms slightly, then lower slowly.",
    "Hip hinge drill (supported)": "Stand holding a counter with one hand. Push your hips back with a flat back and soft knees, then squeeze your buttocks to stand tall again.",
    "McGill side plank (supported)": "Lie on your side propped on your elbow, knees bent, top hand on a chair for balance. Lift your hips into a straight line, then lower slowly.",
    "Lateral raise": "Stand holding light weights at your sides. Raise your arms out to the sides up to shoulder height, elbows slightly bent, then lower slowly.",
    "Lumbar rotation stretch (seated)": "Sit tall, feet flat, arms crossed. Gently turn your trunk to one side until you feel a stretch in your back. Return and repeat to the other side.",
    "Hip flexor stretch": "Kneel on one knee with the other foot in front. Tuck your pelvis under and shift forward until you feel a stretch at the front of the back hip.",
    "NMC-SHO-00806-v1": "Stand tall, hand beside the same-side hip, palm facing back. Lift the arm diagonally across your body to above the opposite shoulder, turning the palm towards you. Lower slowly.",
}
EXTRA_BLOCKED = ["RES-THO-01340-v1", "RES-THO-01341-v1"]
RUNNING = re.compile(
    r"\b(run|running|sprint|shuttle|agility|carioca|bound|bounding|skip|hop|hopping|pogo|jog|cutting)\b", re.I
)

# "(seated)" copies whose exercise cannot be done seated (Onkar 20 Nov: HIDDEN).
# D2 rows from D2_flags.csv; D1 / D3 rows by the same test (title needs lying,
# kneeling, hands and knees, standing on the legs or walking), checked by hand.
HIDDEN_SEATED = [
    # D2 (rows 501-1000), D2_flags.csv
    "Half-kneeling hip flexor stretch", "Hip airplane", "Hip extension active ROM", "Hip extension band standing",
    "Hip thrust", "Kettlebell deadlift", "Lateral band walk", "Lateral lunge", "Lateral step-up", "McGill side plank",
    "Modified front plank", "Modified side plank", "Monster walk", "Prone hip extension", "Prone horizontal abduction",
    "Prone on elbows", "Prone press-up", "Prone shoulder extension", "Prone T raise", "Prone W raise", "Prone Y raise",
    "Push-up plus at wall", "Push-up plus incline", "Quadruped hip extension", "Quadruped scapular protraction",
    "Quadruped scapular retraction", "Quadruped thoracic rotation", "Reverse clamshell", "Reverse lunge",
    "Romanian deadlift", "Piriformis stretch supine",
    # D1 (rows 1-500)
    "Banded hip thrust", "Bird dog", "Bird dog arm only", "Bird dog leg only", "Bottoms-up carry", "Bridge march",
    "Bridge with abdominal brace", "Bridge with band", "Child's pose", "Chin tuck with head lift", "Clamshell",
    "Copenhagen plank", "Curl-up", "Dead bug", "Dead bug arm/leg", "Dead bug heel tap", "Farmer carry", "Fire hydrant",
    "Foam roller thoracic rotation", "Forward lunge", "Front plank", "Glute bridge",
    # D3 (rows 1001-end)
    "Side plank", "Side-lying hip abduction", "Side-lying hip adduction", "Sidelying external rotation",
    "Sidelying internal rotation", "Single-leg bridge", "Single-leg Romanian deadlift",
    "Single-leg Romanian deadlift reach", "Split squat", "Standing hip flexor stretch", "Standing hip hike",
    "Step-up", "Suitcase carry", "Suitcase carry march", "Supine trunk rotation", "Thoracic extension over foam roller",
    "Thread-the-needle", "Wall hip hinge", "Wall push-up", "Wall triceps press",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod-export", required=True, type=Path)
    ap.add_argument("--desc-p0-mapped", required=True, type=Path)
    ap.add_argument("--d4", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("files", nargs="+", type=Path)
    a = ap.parse_args(argv)
    st = B._structure()
    norm = lambda s: " ".join((s or "").split())  # noqa: E731

    desc, _tf, report, rejected, warned, unknown, conflicts = B.build(a.files + [a.d4], a.prod_export)
    text = {i: t for i, t, _o in desc}
    old = {i: o for i, _t, o in desc}
    prod = [r for r in csv.DictReader(open(a.prod_export, encoding="utf-8")) if r["clinic_id"] in ("null", "")]
    title = {r["id"]: r["title"] for r in prod}
    base = {i: re.sub(r"\s*\((seated|supported)\)\s*$", "", t) for i, t in title.items()}
    bank_of = {i: k for i, _c, k in st.PROD if k}
    d4 = {r["key"]: " ".join(r["new_description"].split()) for r in csv.DictReader(open(a.d4, encoding="utf-8-sig"))}
    log = Counter()
    listed: list[tuple] = []

    # 2. desc_p0 mapped
    mapped = list(csv.DictReader(open(a.desc_p0_mapped, encoding="utf-8-sig")))
    p0 = {m["prod_id"]: norm(m["description"]) for m in mapped}
    owner = {t: i for i, t in p0.items()}
    placed: dict[str, set] = {}
    for i, t in text.items():
        placed.setdefault(norm(t), set()).add(i)
    for i, t in p0.items():
        cur = norm(text.get(i))
        if cur != t and placed.get(t, set()) - {i}:
            text[i] = t
            log["desc_p0: D chat put this text on another row, mapped row set"] += 1
        elif cur in owner and owner[cur] != i:
            text[i] = t
            log["desc_p0: mapped row had another row's text, set own"] += 1
        elif not cur:
            text[i] = t
            log["desc_p0: mapped row had no text, set"] += 1
    for i in list(text):
        cur = norm(text[i])
        if i in p0 or cur not in owner:
            continue
        a_id = owner[cur]
        if base.get(i) == title.get(a_id):
            log["desc_p0 text on its own seated/supported copy: kept"] += 1
            continue
        k = bank_of.get(i)
        if k and d4.get(k):
            text[i] = d4[k]
            log["desc_p0 text on another exercise: D4 text used"] += 1
        else:
            del text[i]
            listed.append(("no description (desc_p0 text belonged to another exercise)", title.get(i), title.get(a_id)))
            log["desc_p0 text on another exercise: left empty, listed"] += 1

    # 3. running / agility with a bank match
    for i, t in title.items():
        k = bank_of.get(i)
        if k and RUNNING.search(t) and d4.get(k):
            text[i] = d4[k]
            log["running/agility: D4 text"] += 1

    # 3b. Onkar's text for the rows left empty
    by_t = {t: i for i, t in title.items()}
    by_k = {r[1]: r[0] for r in st.NEW}
    for key, t in DESC_OVERRIDE.items():
        text[by_t.get(key) or by_k[key]] = t
        log["Onkar text for empty row"] += 1

    # 4. QA on the final set
    new_mode = {r[0]: r[5] for r in st.NEW}
    qa = []
    for i, t in list(text.items()):
        n = B.words(t)
        mode = new_mode.get(i, "PATIENT")
        if n > B.MAX_WORDS or "prescribed" in t.lower() or (mode == "PATIENT" and re.search(r"\bthe therapist\b", t, re.I)):
            qa.append((title.get(i) or i, mode, n, t))
            del text[i]
    # 5. hidden
    hidden_titles = {f"{h} (seated)" for h in HIDDEN_SEATED}
    hidden = sorted(i for i, t in title.items() if t in hidden_titles)
    missing_hidden = sorted(hidden_titles - {title[i] for i in hidden})
    # 6. body part + rename
    bp = []
    by_title = {}
    for r in prod:
        by_title.setdefault(r["title"], r)
    for t, new in BODY_PART:
        r = by_title[t]
        bp.append([r["id"], new, r["body_part"]])
    rename = (RENAME[0], RENAME[1], title[RENAME[0]])
    blocked = [r[0] for r in st.NEW if r[1] in EXTRA_BLOCKED]

    rows = sorted([i, t, old.get(i)] for i, t in text.items())
    with open(a.out, "w", encoding="utf-8") as f:
        f.write('"""Data for Migration B (EL-D-016 / EL-D-017). Generated by build_el_migration_b.py; do not edit."""\n\n')
        f.write("# [exercise id, description, description before (prod 20 Nov export) or None]\n")
        f.write("DESCRIPTIONS = " + pprint.pformat(rows, width=200) + "\n\n")
        f.write("# (id, new title, old title)\nTITLE_FIX = " + pprint.pformat(rename) + "\n\n")
        f.write("# [id, new body part, old body part]\nBODY_PART_FIX = " + pprint.pformat(bp) + "\n\n")
        f.write("# '(seated)' copies that cannot be done seated -> rx_mode HIDDEN\nHIDDEN = " + pprint.pformat(hidden) + "\n\n")
        f.write("# new bank rows that become BLOCKED (head-down postural drainage)\nBLOCKED = " + pprint.pformat(blocked) + "\n")

    print("builder report:", dict(report))
    print("steps:", dict(log))
    print("descriptions:", len(rows), "| hidden:", len(hidden), "| missing hidden titles:", missing_hidden)
    for name, items in (("refused", rejected), ("warned", warned), ("unknown", unknown), ("conflicts", conflicts),
                        ("QA refused", qa), ("listed", listed)):
        print(f"{name}: {len(items)}")
        for it in items[:80]:
            print("   ", it)
    return 0


if __name__ == "__main__":
    sys.exit(main())
