from sqlalchemy.orm import Session
from models import BoatProfile, SailProfile


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
    return "Fredericia"


def get_home_port_coords(db: Session, account_id):
    if account_id:
        bp = get_boat_profile_for_account(db, account_id)
        if bp and bp.home_port_lat is not None and bp.home_port_lon is not None:
            return bp.home_port_lat, bp.home_port_lon
    return None, None
