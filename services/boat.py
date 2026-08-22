from sqlalchemy import func
from sqlalchemy.orm import Session
from models import BoatProfile, SailProfile, Trip, LogbookEntry


def get_or_create_boat_profile(db: Session, account_id: int) -> BoatProfile:
    bp = db.query(BoatProfile).filter(BoatProfile.account_id == account_id).first()
    if bp:
        if not bp.sail_profile:
            sp = SailProfile(boat_profile_id=bp.id)
            db.add(sp)
            db.commit()
            db.refresh(bp)
        return bp

    bp = BoatProfile(account_id=account_id, boat_name="My Boat", boat_name_is_default=True)
    db.add(bp)
    db.flush()

    sp = SailProfile(boat_profile_id=bp.id)
    db.add(sp)
    db.commit()
    db.refresh(bp)
    return bp


def get_boat_profile_for_account(db: Session, account_id: int):
    return db.query(BoatProfile).filter(BoatProfile.account_id == account_id).first()


def get_default_home_port(db: Session, account_id) -> str:
    if account_id:
        bp = get_boat_profile_for_account(db, account_id)
        if bp and bp.home_port_name:
            return bp.home_port_name
    return ""


def get_home_port_coords(db: Session, account_id):
    if account_id:
        bp = get_boat_profile_for_account(db, account_id)
        if bp and bp.home_port_lat is not None and bp.home_port_lon is not None:
            return bp.home_port_lat, bp.home_port_lon
    return None, None


def compute_boat_stats(db: Session, account_id: int) -> dict:
    """Cumulative main-boat stats: lifetime NM, motor hours, trip count, and
    the most recent trip's start date. Aggregates only trips flagged
    use_main_boat=True so charter / friend's-boat trips don't skew the
    numbers. Shared by the boat-profile page and the maintenance log, which
    both need these totals to compare against service-due thresholds."""
    main_boat_trips = db.query(Trip).filter(
        Trip.account_id == account_id,
        Trip.use_main_boat == True,
    ).order_by(Trip.start_date.desc()).all()
    main_boat_trip_ids = [t.id for t in main_boat_trips]

    total_nm = 0.0
    if main_boat_trip_ids:
        total_nm = float(
            db.query(func.coalesce(func.sum(LogbookEntry.dist_day_nm), 0))
            .filter(LogbookEntry.trip_id.in_(main_boat_trip_ids))
            .scalar() or 0
        )

    # Motor hours per trip = max(eng_hours_total) - min(eng_hours_total).
    # Trips with <2 readings contribute 0 (no measurable runtime).
    total_motor_h = 0.0
    for tid in main_boat_trip_ids:
        readings = db.query(LogbookEntry.eng_hours_total).filter(
            LogbookEntry.trip_id == tid,
            LogbookEntry.eng_hours_total.isnot(None),
        ).all()
        vals = [r[0] for r in readings if r[0] is not None]
        if len(vals) >= 2:
            total_motor_h += max(vals) - min(vals)

    return {
        "total_nm":      round(total_nm, 1),
        "total_motor_h": round(total_motor_h, 1),
        "trip_count":    len(main_boat_trip_ids),
        "last_trip":     main_boat_trips[0].start_date if main_boat_trips else None,
    }
