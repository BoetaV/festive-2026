"""Development seed: demo accounts for each role plus synthetic deliveries.

    python -m app.seed            # add demo data
    python -m app.seed --reset    # wipe deliveries + audit log first

Refuses to run when ENVIRONMENT=production.
"""

import random
import sys
from datetime import date, time, timedelta

from sqlalchemy import delete, select

from .config import get_settings
from .db import SessionLocal
from .locations import FACILITY_TYPES, LOCATION_DATA
from .models import AuditLog, Baby, Delivery, Role, User
from .schemas import BIRTH_MODES, TIME_SLOTS
from .security import hash_password
from .services.deliveries import time_slot_for

DEMO_PASSWORD = "Festive2026!"
DEMO_USERS = [
    ("10000001", "Sipho", "Ndlovu", Role.superuser, {}),
    ("10000002", "Ayanda", "Mahlangu", Role.province, {}),
    ("10000003", "Lindiwe", "Dlamini", Role.admin, {"district": "Amathole DM"}),
    ("10000004", "Nomsa", "Khumalo", Role.user, {"district": "Amathole DM", "local_municipality": "Mnquma LM",
                                                 "facility": "Butterworth Hospital"}),
]
FIRST = ["Thandeka", "Zanele", "Nokuthula", "Anele", "Busisiwe", "Lerato", "Ntombi", "Siphokazi", "Yonela", "Aviwe"]
LAST = ["Mbeki", "Sisulu", "Tshabalala", "Ngcobo", "Mthembu", "Zulu", "Botha", "Jacobs", "Petersen", "Mavuso"]
MODE_WEIGHTS = [62, 10, 18, 5, 2, 3]


def main(reset: bool) -> None:
    s = get_settings()
    if s.is_production:
        sys.exit("Refusing to seed demo data in production.")
    rng = random.Random(2026)
    with SessionLocal() as db:
        if reset:
            db.execute(delete(Baby))
            db.execute(delete(Delivery))
            db.execute(delete(AuditLog))

        users = {}
        for persal, first, last, role, loc in DEMO_USERS:
            u = db.scalar(select(User).where(User.persal_number == persal))
            if not u:
                u = User(persal_number=persal, first_name=first, last_name=last, role=role,
                         title="Ms", hashed_password=hash_password(DEMO_PASSWORD),
                         must_change_password=False, **loc)
                db.add(u)
            users[role] = u
        db.flush()

        facilities = [(d, m, f) for d, ms in LOCATION_DATA["municipalities"].items()
                      for m in ms for f in LOCATION_DATA["facilities"].get(m, [])]
        count = 0
        for report_date in s.report_dates:
            for d, m, f in facilities:
                busy = 3 if FACILITY_TYPES.get(f, "").endswith(("Regional Hospital", "Tertiary Hospital",
                                                                   "Academic Hospital")) else 1
                n = rng.choices([0, 1, 2, 3, 4, 6], weights=[25, 25, 20, 15, 10, 5])[0] * busy
                if n == 0:
                    for slot in rng.sample(TIME_SLOTS, k=rng.randint(1, 4)):
                        db.add(Delivery(district=d, local_municipality=m, facility=f,
                                        facility_type=FACILITY_TYPES.get(f), report_date=report_date,
                                        time_slot=slot, no_births_to_report=True,
                                        captured_by_id=users[Role.user].id))
                    continue
                for _ in range(n):
                    t = time(rng.randint(0, 23), rng.randint(0, 59))
                    age = rng.choices([13, 17, 25, 38], weights=[2, 14, 70, 14])[0] + rng.randint(-1, 1)
                    dob = report_date - timedelta(days=age * 365 + rng.randint(0, 364))
                    babies = rng.choices([1, 2, 3], weights=[96, 3.6, 0.4])[0]
                    gravidity = rng.randint(1, 5)
                    dl = Delivery(
                        district=d, local_municipality=m, facility=f, facility_type=FACILITY_TYPES.get(f),
                        report_date=report_date, time_slot=time_slot_for(t), delivery_time=t,
                        born_before_arrival=rng.random() < 0.04,
                        mother_name=rng.choice(FIRST), mother_surname=rng.choice(LAST), mother_dob=dob,
                        birth_mode=rng.choices(BIRTH_MODES, weights=MODE_WEIGHTS)[0],
                        gravidity=gravidity, parity=rng.randint(1, gravidity),
                        captured_by_id=users[Role.user].id,
                    )
                    for _ in range(babies):
                        w = int(rng.gauss(3150 if babies == 1 else 2350, 520))
                        dl.babies.append(Baby(gender=rng.choice(["Male", "Female"]), weight=max(450, min(5200, w))))
                    db.add(dl)
                    count += 1
        db.commit()
    print(f"Seeded {count} deliveries across {len(facilities)} facilities.")
    print(f"Demo logins (password {DEMO_PASSWORD}):")
    for persal, first, last, role, _ in DEMO_USERS:
        print(f"  {persal}  {role.value:<9} {first} {last}")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
