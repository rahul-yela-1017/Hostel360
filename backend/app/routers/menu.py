from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import Menu, MenuHistory, Notification, Role, Student, User
from ..schemas import MenuUpsert
from ..services import audit, room_scope_for

router = APIRouter(tags=["Menu"])


def menu_dict(menu: Menu) -> dict:
    return {"id": menu.id, "menu_date": menu.menu_date, "breakfast": menu.breakfast,
            "breakfast_time": menu.breakfast_time, "lunch": menu.lunch, "lunch_time": menu.lunch_time,
            "snacks": menu.snacks, "snacks_time": menu.snacks_time, "dinner": menu.dinner,
            "dinner_time": menu.dinner_time, "description": menu.description,
            "is_published": menu.is_published, "published_at": menu.published_at, "updated_at": menu.updated_at}


@router.get("/menu/today")
def today_menu(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hostel_id = room_scope_for(user) or 1
    local_today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    query = select(Menu).where(Menu.hostel_id == hostel_id, Menu.menu_date == local_today)
    if user.role == Role.STUDENT:
        query = query.where(Menu.is_published.is_(True))
    menu = db.scalar(query)
    if not menu:
        raise HTTPException(404, "Today's menu has not been published yet")
    return menu_dict(menu)


@router.get("/menu/history")
def previous_menus(limit: int = Query(14, ge=1, le=90), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hostel_id = room_scope_for(user) or 1
    rows = db.scalars(select(Menu).where(Menu.hostel_id == hostel_id, Menu.is_published.is_(True))
                      .order_by(Menu.menu_date.desc()).limit(limit)).all()
    return [menu_dict(m) for m in rows]


@router.post("/cook/menu")
@router.put("/cook/menu")
@router.put("/warden/menu")
def upsert_menu(payload: MenuUpsert, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN, Role.COOK))):
    scope = room_scope_for(actor)
    if scope is not None and scope != payload.hostel_id:
        raise HTTPException(403, "Cannot update a menu outside your hostel scope")
    menu = db.scalar(select(Menu).where(Menu.hostel_id == payload.hostel_id, Menu.menu_date == payload.menu_date))
    fields = ["breakfast", "breakfast_time", "lunch", "lunch_time", "snacks", "snacks_time", "dinner", "dinner_time", "description"]
    if menu is None:
        menu = Menu(hostel_id=payload.hostel_id, menu_date=payload.menu_date,
                    **{field: getattr(payload, field) for field in fields}, updated_by=actor.id)
        db.add(menu); db.flush()
        for meal in ("breakfast", "lunch", "snacks", "dinner"):
            db.add(MenuHistory(menu_id=menu.id, changed_by=actor.id, meal_type=meal,
                               old_value=None, new_value=getattr(menu, meal), reason=payload.reason or "Menu created"))
    else:
        for field in fields:
            old, new = getattr(menu, field), getattr(payload, field)
            if old != new:
                db.add(MenuHistory(menu_id=menu.id, changed_by=actor.id, meal_type=field,
                                   old_value=old, new_value=new, reason=payload.reason))
                setattr(menu, field, new)
        menu.updated_by = actor.id
    if payload.publish:
        menu.is_published = True
        menu.published_by = actor.id
        menu.published_at = datetime.now(timezone.utc)
        # There is deliberately no approval state: publishing is immediately committed and visible.
        student_user_ids = db.scalars(select(Student.user_id).where(Student.hostel_id == payload.hostel_id)).all()
        db.add_all([Notification(user_id=uid, type="MENU_UPDATED", title="Today's menu updated",
                                 message=f"{actor.name} published the menu for {payload.menu_date.strftime('%d %b')}.")
                    for uid in student_user_ids])
    audit(db, actor.id, "MENU_PUBLISHED" if payload.publish else "MENU_SAVED", "menu", menu.id,
          {"date": str(payload.menu_date), "direct_publish": payload.publish})
    db.commit(); db.refresh(menu)
    return {"message": "Menu published successfully." if payload.publish else "Menu saved.", "menu": menu_dict(menu)}


@router.get("/menu/{menu_id}/changes")
def menu_changes(menu_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN, Role.COOK))):
    rows = db.execute(select(MenuHistory, User.name).join(User, User.id == MenuHistory.changed_by)
                      .where(MenuHistory.menu_id == menu_id).order_by(MenuHistory.changed_at.desc())).all()
    return [{"id": h.id, "changed_by": name, "meal_type": h.meal_type, "old_value": h.old_value,
             "new_value": h.new_value, "reason": h.reason, "changed_at": h.changed_at} for h, name in rows]
