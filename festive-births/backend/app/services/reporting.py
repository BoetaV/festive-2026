"""Reporting compliance per time slot: which facilities reported births, which reported NIL and which
reported nothing, rolled up to sub-district and district so managers know whom to follow up."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..locations import DISTRICTS, FACILITY_TYPES, LOCATION_DATA
from ..models import Delivery
from ..schemas import TIME_SLOTS

SAST = timezone(timedelta(hours=2))  # South Africa has no daylight saving
STATUSES = ("births", "nil", "missing", "pending")


def _slot_end(report_date: date, slot: str) -> datetime:
    """'18:01 - 24:00' on 25 Dec ends at 00:00 on 26 Dec (SAST)."""
    hours = int(slot.split("-")[1].strip().split(":")[0])
    return datetime.combine(report_date, time(0), SAST) + timedelta(hours=hours)


def default_report_date(report_dates: list[date], now: datetime | None = None) -> date:
    """The most recent reporting day that has started, else the first one."""
    today = (now or datetime.now(SAST)).astimezone(SAST).date()
    started = [d for d in report_dates if d <= today]
    return max(started) if started else min(report_dates)


def compute_reporting(db: Session, report_date: date, *, district: str | None = None,
                      local_municipality: str | None = None, facility: str | None = None,
                      now: datetime | None = None) -> dict:
    now = now or datetime.now(SAST)
    due = [_slot_end(report_date, s) <= now for s in TIME_SLOTS]

    stmt = (select(Delivery.facility, Delivery.time_slot, Delivery.no_births_to_report, func.count())
            .where(Delivery.report_date == report_date, Delivery.facility.is_not(None))
            .group_by(Delivery.facility, Delivery.time_slot, Delivery.no_births_to_report))
    births: dict[tuple[str, str], int] = {}
    nil: set[tuple[str, str]] = set()
    for fac, slot, is_nil, n in db.execute(stmt):
        if is_nil:
            nil.add((fac, slot))
        else:
            births[(fac, slot)] = births.get((fac, slot), 0) + n

    def empty_counts() -> list[dict]:
        return [dict.fromkeys(STATUSES, 0) for _ in TIME_SLOTS]

    def add(into: list[dict], cells: list[dict]) -> None:
        for agg, cell in zip(into, cells):
            agg[cell["status"]] += 1

    districts_out, grand = [], empty_counts()
    for dist in DISTRICTS:
        if district and dist != district:
            continue
        d_counts, munis_out, d_fac = empty_counts(), [], 0
        for muni in LOCATION_DATA["municipalities"][dist]:
            if local_municipality and muni != local_municipality:
                continue
            m_counts, facs_out = empty_counts(), []
            for fac in LOCATION_DATA["facilities"].get(muni, []):
                if facility and fac != facility:
                    continue
                cells = []
                for i, slot in enumerate(TIME_SLOTS):
                    n = births.get((fac, slot), 0)
                    status = ("births" if n else "nil" if (fac, slot) in nil
                              else "missing" if due[i] else "pending")
                    cells.append({"status": status, "births": n})
                add(m_counts, cells)
                facs_out.append({"name": fac, "facility_type": FACILITY_TYPES.get(fac), "slots": cells,
                                 "outstanding": sum(c["status"] == "missing" for c in cells)})
            if not facs_out:
                continue
            for agg, m in zip(d_counts, m_counts):
                for k in STATUSES:
                    agg[k] += m[k]
            d_fac += len(facs_out)
            munis_out.append({"name": muni, "facility_count": len(facs_out), "slots": m_counts,
                              "outstanding": sum(c["missing"] for c in m_counts), "facilities": facs_out})
        if not munis_out:
            continue
        for agg, d in zip(grand, d_counts):
            for k in STATUSES:
                agg[k] += d[k]
        districts_out.append({"name": dist, "facility_count": d_fac, "slots": d_counts,
                              "outstanding": sum(c["missing"] for c in d_counts), "municipalities": munis_out})

    return {
        "report_date": report_date,
        "time_slots": TIME_SLOTS,
        "as_at": now.astimezone(SAST).isoformat(timespec="minutes"),
        "slots_due": due,
        "facility_count": sum(d["facility_count"] for d in districts_out),
        "totals": grand,
        "outstanding": sum(c["missing"] for c in grand),
        "districts": districts_out,
    }
