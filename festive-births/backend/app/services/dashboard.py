"""KPI engine behind the public dashboard and the PDF report.

Festive-season volumes are small (thousands of rows), so the filtered rows are
loaded once and aggregated in Python; this keeps every breakdown consistent and
database-agnostic.
"""

from collections import Counter, defaultdict
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from ..locations import DISTRICTS
from ..models import Delivery
from ..schemas import BIRTH_MODES, TIME_SLOTS

AGE_GROUPS = ["10-14 yrs", "15-19 yrs", "20-35 yrs", "Over 35 yrs"]
WEIGHT_BANDS = [
    ("Extremely low (<1000g)", 0, 1000),
    ("Very low (1000-1499g)", 1000, 1500),
    ("Low (1500-2499g)", 1500, 2500),
    ("Normal (2500-3999g)", 2500, 4000),
    ("High (4000g+)", 4000, 10**6),
]
MULTIPLES = {2: "twins", 3: "triplets", 4: "quadruplets", 5: "quintuplets"}


def weight_band(w: int | None) -> str | None:
    if w is None:
        return None
    return next(label for label, lo, hi in WEIGHT_BANDS if lo <= w < hi)


def age_group(age: int | None) -> str | None:
    if age is None or age < 10:
        return None
    if age <= 14:
        return AGE_GROUPS[0]
    if age <= 19:
        return AGE_GROUPS[1]
    if age <= 35:
        return AGE_GROUPS[2]
    return AGE_GROUPS[3]


def filtered_query(
    report_date: date | None = None,
    district: str | None = None,
    local_municipality: str | None = None,
    facility: str | None = None,
) -> Select:
    stmt = select(Delivery).options(selectinload(Delivery.babies))
    if report_date:
        stmt = stmt.where(Delivery.report_date == report_date)
    if district:
        stmt = stmt.where(Delivery.district == district)
    if local_municipality:
        stmt = stmt.where(Delivery.local_municipality == local_municipality)
    if facility:
        stmt = stmt.where(Delivery.facility == facility)
    return stmt


def _mf() -> dict:
    return {"male": 0, "female": 0, "total": 0}


def _add(bucket: dict, gender: str | None) -> None:
    bucket["total"] += 1
    if gender == "Male":
        bucket["male"] += 1
    elif gender == "Female":
        bucket["female"] += 1


def _pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def compute_dashboard(db: Session, stmt: Select, *, district=None, local_municipality=None, facility=None) -> dict:
    rows: list[Delivery] = list(db.scalars(stmt))
    births = [d for d in rows if not d.no_births_to_report]
    nil = [d for d in rows if d.no_births_to_report]
    babies = [(d, b) for d in births for b in d.babies]

    # --- Summary grouping drills down one level below the active filter (as in v1) ---
    if facility or local_municipality:
        group_field, level, scope_name = "facility", "Facility", facility or local_municipality
    elif district:
        group_field, level, scope_name = "local_municipality", "Sub-district", district
    else:
        group_field, level, scope_name = "district", "District", "Eastern Cape"

    by_area: dict[str, dict] = defaultdict(_mf)
    if group_field == "district":
        for name in DISTRICTS:  # show zero rows so silent districts stand out
            by_area[name]
    age = {g: _mf() for g in AGE_GROUPS}
    modes = {m: _mf() for m in BIRTH_MODES}
    slots = {s: _mf() for s in TIME_SLOTS}
    ftypes: dict[str, dict] = defaultdict(_mf)
    weights = {label: _mf() for label, *_ in WEIGHT_BANDS}
    by_date: dict[str, dict] = defaultdict(_mf)
    by_hour = [0] * 24
    teen_by_facility: dict[str, dict] = defaultdict(lambda: {"age_10_14": 0, "age_15_19": 0})

    for d, b in babies:
        _add(by_area[getattr(d, group_field) or "Unknown"], b.gender)
        if g := age_group(d.mother_age):
            _add(age[g], b.gender)
            if g == AGE_GROUPS[0]:
                teen_by_facility[d.facility or "Unknown"]["age_10_14"] += 1
            elif g == AGE_GROUPS[1]:
                teen_by_facility[d.facility or "Unknown"]["age_15_19"] += 1
        if d.birth_mode in modes:
            _add(modes[d.birth_mode], b.gender)
        if d.time_slot in slots:
            _add(slots[d.time_slot], b.gender)
        _add(ftypes[d.facility_type or "Unknown"], b.gender)
        if band := weight_band(b.weight):
            _add(weights[band], b.gender)
        _add(by_date[d.report_date.isoformat()], b.gender)
        if d.delivery_time:
            by_hour[d.delivery_time.hour] += 1

    multiples: dict[str, Counter] = defaultdict(Counter)
    for d in births:
        if kind := MULTIPLES.get(len(d.babies)):
            multiples[d.facility or "Unknown"][kind] += 1

    total = len(babies)
    males = sum(1 for _, b in babies if b.gender == "Male")
    females = sum(1 for _, b in babies if b.gender == "Female")
    weighed = [b.weight for _, b in babies if b.weight]
    low_bw = sum(1 for w in weighed if w < 2500)
    teen = sum(age[g]["total"] for g in AGE_GROUPS[:2])
    with_mode = [d for d in births if d.birth_mode]
    caesareans = sum(1 for d in with_mode if d.birth_mode.startswith("Caesarean"))
    bba = sum(1 for d in births if d.born_before_arrival)
    facilities_reporting = len({d.facility for d in rows if d.facility})

    return {
        "scope": {"name": scope_name, "level": level},
        "kpis": {
            "total_births": total,
            "males": males,
            "females": females,
            "deliveries": len(births),
            "nil_reports": len(nil),
            "facilities_reporting": facilities_reporting,
            "multiple_birth_sets": sum(sum(c.values()) for c in multiples.values()),
            "low_birth_weight": low_bw,
            "low_birth_weight_rate": _pct(low_bw, len(weighed)),
            "teen_births": teen,
            "teen_birth_rate": _pct(teen, total),
            "caesarean_rate": _pct(caesareans, len(with_mode)),
            "born_before_arrival": bba,
            "average_weight": round(sum(weighed) / len(weighed)) if weighed else None,
        },
        "by_area": [{"name": k, **v} for k, v in sorted(by_area.items())],
        "age_groups": [{"name": k, **v} for k, v in age.items()],
        "birth_modes": [{"name": k, **v} for k, v in modes.items()],
        "time_slots": [{"name": k, **v} for k, v in slots.items()],
        "facility_types": [{"name": k, **v} for k, v in sorted(ftypes.items())],
        "weight_bands": [{"name": k, **v} for k, v in weights.items()],
        "by_date": [{"name": k, **v} for k, v in sorted(by_date.items())],
        "by_hour": [{"hour": h, "total": n} for h, n in enumerate(by_hour)],
        "teen_by_facility": sorted(
            ({"facility": k, **v} for k, v in teen_by_facility.items()),
            key=lambda r: -(r["age_10_14"] + r["age_15_19"]),
        ),
        "multiple_births": sorted(
            ({"facility": k, **{m: c.get(m, 0) for m in MULTIPLES.values()}} for k, c in multiples.items()),
            key=lambda r: r["facility"],
        ),
    }


def last_updated(db: Session):
    return db.scalar(select(func.max(Delivery.updated_at)))
