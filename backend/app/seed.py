from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import Bed, BedStatus, Hostel, HostelTiming, Room, RoomStatus


HOSTEL_NAME = "Malla Reddy Boys Hostel"
HOSTEL_CODE = "MRBH"


def seed_database(db: Session):
    """Create only permanent hostel infrastructure.

    No users, students, attendance, menus, notices or sample people are inserted.
    The first real administrator is created through the one-time setup endpoint.
    """
    hostel = db.scalar(select(Hostel).where(Hostel.code == HOSTEL_CODE))
    if hostel is None:
        hostel = Hostel(name=HOSTEL_NAME, code=HOSTEL_CODE, address="Maisammaguda, Hyderabad, Telangana")
        db.add(hostel)
        db.flush()

    existing_rooms = db.scalar(select(func.count(Room.id)).where(Room.hostel_id == hostel.id)) or 0
    if existing_rooms == 0:
        for number in range(431):
            room = Room(hostel_id=hostel.id, room_number=number, capacity=4, status=RoomStatus.EMPTY)
            db.add(room)
            db.flush()
            db.add_all([
                Bed(room_id=room.id, bed_number=bed_number, status=BedStatus.VACANT)
                for bed_number in range(1, 5)
            ])

    existing_timings = db.scalar(select(func.count(HostelTiming.id)).where(HostelTiming.hostel_id == hostel.id)) or 0
    if existing_timings == 0:
        timings = [
            ("gate_open", "Main gate opens", "05:30 AM"),
            ("gate_close", "Main gate closes", "10:00 PM"),
            ("breakfast", "Breakfast", "08:00–09:30 AM"),
            ("lunch", "Lunch", "12:30–02:00 PM"),
            ("snacks", "Snacks", "04:30–05:30 PM"),
            ("dinner", "Dinner", "07:30–09:30 PM"),
            ("study", "Study hall", "06:00–08:00 PM"),
        ]
        db.add_all([
            HostelTiming(hostel_id=hostel.id, key=key, label=label, value=value, sort_order=index)
            for index, (key, label, value) in enumerate(timings)
        ])
    db.commit()
