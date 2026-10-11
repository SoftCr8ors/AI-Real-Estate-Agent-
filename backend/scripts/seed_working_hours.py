import sys
from pathlib import Path
from datetime import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.schedule import WorkingHours


def seed_working_hours():
    """Seed default working hours (Sunday to Thursday, 10:00-18:00)"""
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(WorkingHours).count()
        if existing > 0:
            print(f"✅ Working hours already seeded ({existing} found). Skipping.")
            return

        # Sunday to Thursday (Dubai business days)
        # 0=Monday, 6=Sunday
        working_days = [6, 0, 1, 2, 3]  # Sunday, Monday, Tuesday, Wednesday, Thursday

        for day in working_days:
            working_hour = WorkingHours(
                day_of_week=day,
                start_time=time(10, 0),  # 10:00 AM
                end_time=time(18, 0),  # 6:00 PM
            )
            db.add(working_hour)

        db.commit()
        print(f"✅ Successfully seeded working hours for 5 days!")

    except Exception as e:
        print(f"❌ Error seeding working hours: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding working hours...")
    seed_working_hours()