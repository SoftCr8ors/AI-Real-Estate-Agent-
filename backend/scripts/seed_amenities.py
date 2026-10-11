import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.amenity import Amenity

amenities_data = [
    {"name": "Swimming Pool", "icon": "🏊"},
    {"name": "Gym", "icon": "🏋️"},
    {"name": "Parking", "icon": "🚗"},
    {"name": "Security", "icon": "🔒"},
    {"name": "Balcony", "icon": "🏡"},
    {"name": "Garden", "icon": "🌳"},
    {"name": "Kids Play Area", "icon": "🎠"},
    {"name": "BBQ Area", "icon": "🍖"},
    {"name": "Maid Room", "icon": "🧹"},
    {"name": "Storage", "icon": "📦"},
    {"name": "Pet Friendly", "icon": "🐕"},
    {"name": "Concierge", "icon": "🛎️"},
    {"name": "Sauna", "icon": "🧖"},
    {"name": "Steam Room", "icon": "💨"},
    {"name": "Jacuzzi", "icon": "🛁"},
    {"name": "Tennis Court", "icon": "🎾"},
    {"name": "Basketball Court", "icon": "🏀"},
    {"name": "Jogging Track", "icon": "🏃"},
    {"name": "Smart Home", "icon": "🏠"},
    {"name": "Central AC", "icon": "❄️"},
]


def seed_amenities():
    """Seed amenities into database"""
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(Amenity).count()
        if existing > 0:
            print(f"✅ Amenities already seeded ({existing} found). Skipping.")
            return

        # Insert amenities
        for amenity in amenities_data:
            db_amenity = Amenity(**amenity)
            db.add(db_amenity)

        db.commit()
        print(f"✅ Successfully seeded {len(amenities_data)} amenities!")

    except Exception as e:
        print(f"❌ Error seeding amenities: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding amenities...")
    seed_amenities()
