import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.amenity import Amenity
from app.models.image import PropertyImage
from app.models.property import Property

# Demo properties data - 25 realistic Dubai properties
properties_data = [
    # DUBAI MARINA - 2BR APARTMENTS (8+ available, ≤ AED 1.5M)
    {
        "reference": "DM-2BR-001",
        "title": "Spacious 2BR in Marina Diamond 3",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1450000"),
        "location": "Dubai Marina",
        "community": "Marina Diamond",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1200,
        "furnished": 0,
        "description": "Bright 2-bedroom apartment with marina views, modern kitchen, large balcony. Close to metro, restaurants, and beach.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony"],
        "images": ["https://images.unsplash.com/photo-1522708323590-d24dbb6b0267"],
    },
    {
        "reference": "DM-2BR-002",
        "title": "Marina View 2BR in Sulafa Tower",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1380000"),
        "location": "Dubai Marina",
        "community": "Sulafa Tower",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1150,
        "furnished": 1,
        "description": "Fully furnished 2BR with stunning marina and sea views. High floor, premium finishes, maid's room.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Maid Room"],
        "images": ["https://images.unsplash.com/photo-1512917774080-9991f1c4c750"],
    },
    {
        "reference": "DM-2BR-003",
        "title": "Modern 2BR in Princess Tower",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1500000"),
        "location": "Dubai Marina",
        "community": "Princess Tower",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1300,
        "furnished": 0,
        "description": "Spacious 2-bedroom on high floor. Panoramic views, premium building, excellent facilities.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Concierge"],
        "images": ["https://images.unsplash.com/photo-1502672260266-1c1ef2d93688"],
    },
    {
        "reference": "DM-2BR-004",
        "title": "Sea View 2BR in Marina Promenade",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1420000"),
        "location": "Dubai Marina",
        "community": "Marina Promenade",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1180,
        "furnished": 0,
        "description": "Beautiful 2BR apartment with direct sea views from balcony. Walking distance to beach and JBR.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "BBQ Area"],
        "images": ["https://images.unsplash.com/photo-1560448204-e02f11c3d0e2"],
    },
    {
        "reference": "DM-2BR-005",
        "title": "Bright 2BR in Marina Heights",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1350000"),
        "location": "Dubai Marina",
        "community": "Marina Heights",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1100,
        "furnished": 0,
        "description": "Well-maintained 2-bedroom with open plan living. Great investment opportunity, high rental yield.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security"],
        "images": ["https://images.unsplash.com/photo-1567496898669-ee935f5f647a"],
    },
    {
        "reference": "DM-2BR-006",
        "title": "Upgraded 2BR in Marina Gate",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1480000"),
        "location": "Dubai Marina",
        "community": "Marina Gate",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1250,
        "furnished": 1,
        "description": "Fully upgraded 2BR with designer furniture. Premium finishes, smart home features, storage room.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Storage", "Smart Home"],
        "images": ["https://images.unsplash.com/photo-1600585154340-be6161a56a0c"],
    },
    {
        "reference": "DM-2BR-007",
        "title": "Corner 2BR in The Torch",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1395000"),
        "location": "Dubai Marina",
        "community": "The Torch",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1220,
        "furnished": 0,
        "description": "Corner unit with extra windows and natural light. Large master bedroom, modern kitchen, balcony.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Sauna"],
        "images": ["https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3"],
    },
    {
        "reference": "DM-2BR-008",
        "title": "Elegant 2BR in Elite Residence",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1440000"),
        "location": "Dubai Marina",
        "community": "Elite Residence",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1280,
        "furnished": 0,
        "description": "Spacious 2BR with elegant design. Walk-in closets, quality finishes, close to marina walk.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Concierge"],
        "images": ["https://images.unsplash.com/photo-1600607687939-ce8a6c25118c"],
    },
    {
        "reference": "DM-2BR-009",
        "title": "Luxury 2BR in Marina 101",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1495000"),
        "location": "Dubai Marina",
        "community": "Marina 101",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1320,
        "furnished": 1,
        "description": "Premium 2BR in iconic tower. Floor-to-ceiling windows, luxury amenities, stunning views.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Concierge", "Jacuzzi"],
        "images": ["https://images.unsplash.com/photo-1600607687644-c7171b42498b"],
    },

    # BUSINESS BAY - MIX OF TYPES
    {
        "reference": "BB-STU-001",
        "title": "Modern Studio in Executive Towers",
        "property_type": "studio",
        "listing_type": "rent",
        "price": Decimal("45000"),
        "rent_period": "yearly",
        "location": "Business Bay",
        "community": "Executive Towers",
        "bedrooms": 0,
        "bathrooms": 1,
        "size_sqft": 520,
        "furnished": 1,
        "description": "Fully furnished studio with canal views. Perfect for professionals, close to metro and downtown.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security"],
        "images": ["https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf"],
    },
    {
        "reference": "BB-1BR-001",
        "title": "Spacious 1BR in Bay Square",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("950000"),
        "location": "Business Bay",
        "community": "Bay Square",
        "bedrooms": 1,
        "bathrooms": 2,
        "size_sqft": 850,
        "furnished": 0,
        "description": "Large 1-bedroom with study area. Canal views, modern design, investment opportunity.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony"],
        "images": ["https://images.unsplash.com/photo-1600585154526-990dced4db0d"],
    },
    {
        "reference": "BB-2BR-001",
        "title": "Premium 2BR in Burj Views",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1850000"),
        "location": "Business Bay",
        "community": "Burj Views",
        "bedrooms": 2,
        "bathrooms": 3,
        "size_sqft": 1400,
        "furnished": 1,
        "description": "Luxurious 2BR with direct Burj Khalifa views. Premium finishes, maid's room, designer furniture.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Maid Room", "Concierge"],
        "images": ["https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea"],
    },

    # DOWNTOWN DUBAI - LUXURY
    {
        "reference": "DT-1BR-001",
        "title": "Elegant 1BR in Boulevard Central",
        "property_type": "apartment",
        "listing_type": "rent",
        "price": Decimal("95000"),
        "rent_period": "yearly",
        "location": "Downtown Dubai",
        "community": "Boulevard Central",
        "bedrooms": 1,
        "bathrooms": 2,
        "size_sqft": 900,
        "furnished": 1,
        "description": "Luxury 1BR with Burj Khalifa views. Walking distance to Dubai Mall, world-class amenities.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Concierge"],
        "images": ["https://images.unsplash.com/photo-1600607687920-4e2a09cf159d"],
    },
    {
        "reference": "DT-2BR-001",
        "title": "Luxury 2BR in Address Downtown",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("2950000"),
        "location": "Downtown Dubai",
        "community": "The Address Downtown",
        "bedrooms": 2,
        "bathrooms": 3,
        "size_sqft": 1500,
        "furnished": 1,
        "description": "Ultra-luxury 2BR in iconic Address hotel residences. 5-star amenities, Burj Khalifa views.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Concierge", "Sauna", "Jacuzzi"],
        "images": ["https://images.unsplash.com/photo-1600607687939-ce8a6c25118c"],
    },

    # JUMEIRAH VILLAGE CIRCLE - AFFORDABLE
    {
        "reference": "JVC-STU-001",
        "title": "Cozy Studio in Belgravia Heights",
        "property_type": "studio",
        "listing_type": "rent",
        "price": Decimal("32000"),
        "rent_period": "yearly",
        "location": "Jumeirah Village Circle",
        "community": "Belgravia Heights",
        "bedrooms": 0,
        "bathrooms": 1,
        "size_sqft": 480,
        "furnished": 0,
        "description": "Affordable studio in family-friendly community. Great for first-time renters, pet-friendly building.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Pet Friendly"],
        "images": ["https://images.unsplash.com/photo-1600585154340-be6161a56a0c"],
    },
    {
        "reference": "JVC-1BR-001",
        "title": "Bright 1BR in Diamond Views",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("680000"),
        "location": "Jumeirah Village Circle",
        "community": "Diamond Views",
        "bedrooms": 1,
        "bathrooms": 1,
        "size_sqft": 720,
        "furnished": 0,
        "description": "Well-maintained 1BR with garden view. Excellent ROI, family community, pet-friendly.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Garden", "Kids Play Area", "Pet Friendly"],
        "images": ["https://images.unsplash.com/photo-1600585154526-990dced4db0d"],
    },
    {
        "reference": "JVC-2BR-001",
        "title": "Family 2BR in Fortunato",
        "property_type": "apartment",
        "listing_type": "rent",
        "price": Decimal("75000"),
        "rent_period": "yearly",
        "location": "Jumeirah Village Circle",
        "community": "Fortunato",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1100,
        "furnished": 0,
        "description": "Spacious 2BR perfect for families. Large balcony, storage, close to schools and supermarkets.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Balcony", "Kids Play Area", "Storage"],
        "images": ["https://images.unsplash.com/photo-1502672260266-1c1ef2d93688"],
    },

    # ARABIAN RANCHES - VILLAS
    {
        "reference": "AR-3BR-001",
        "title": "Stunning 3BR Villa in Palmera",
        "property_type": "villa",
        "listing_type": "buy",
        "price": Decimal("3450000"),
        "location": "Arabian Ranches",
        "community": "Palmera",
        "bedrooms": 3,
        "bathrooms": 4,
        "size_sqft": 2800,
        "furnished": 0,
        "description": "Beautiful 3BR villa with private garden and pool. Golf course views, upgraded kitchen, maid's room.",
        "amenities": ["Swimming Pool", "Garden", "Parking", "Maid Room", "BBQ Area", "Storage"],
        "images": ["https://images.unsplash.com/photo-1600596542815-ffad4c1539a9"],
    },
    {
        "reference": "AR-4BR-001",
        "title": "Luxury 4BR Villa in Savannah",
        "property_type": "villa",
        "listing_type": "rent",
        "price": Decimal("285000"),
        "rent_period": "yearly",
        "location": "Arabian Ranches",
        "community": "Savannah",
        "bedrooms": 4,
        "bathrooms": 5,
        "size_sqft": 3500,
        "furnished": 0,
        "description": "Spacious 4BR villa with landscaped garden. Study room, upgraded flooring, close to pool and park.",
        "amenities": ["Swimming Pool", "Garden", "Parking", "Maid Room", "BBQ Area", "Storage", "Kids Play Area"],
        "images": ["https://images.unsplash.com/photo-1600585154363-67eb9e2e2099"],
    },

    # JBR - BEACHFRONT
    {
        "reference": "JBR-1BR-001",
        "title": "Beachfront 1BR in Sadaf",
        "property_type": "apartment",
        "listing_type": "rent",
        "price": Decimal("95000"),
        "rent_period": "yearly",
        "location": "Jumeirah Beach Residence",
        "community": "Sadaf",
        "bedrooms": 1,
        "bathrooms": 2,
        "size_sqft": 950,
        "furnished": 1,
        "description": "Fully furnished 1BR with sea views. Direct beach access, walking distance to restaurants and shops.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Beach Access"],
        "images": ["https://images.unsplash.com/photo-1600607687920-4e2a09cf159d"],
    },
    {
        "reference": "JBR-2BR-001",
        "title": "Sea View 2BR in Rimal",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("2200000"),
        "location": "Jumeirah Beach Residence",
        "community": "Rimal",
        "bedrooms": 2,
        "bathrooms": 3,
        "size_sqft": 1450,
        "furnished": 1,
        "description": "Premium 2BR with stunning sea views. High floor, luxury finishes, beach lifestyle.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Beach Access", "Concierge"],
        "images": ["https://images.unsplash.com/photo-1512917774080-9991f1c4c750"],
    },

    # DUBAI HILLS - MODERN
    {
        "reference": "DH-2BR-001",
        "title": "Modern 2BR in Park Heights",
        "property_type": "apartment",
        "listing_type": "buy",
        "price": Decimal("1650000"),
        "location": "Dubai Hills Estate",
        "community": "Park Heights",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1250,
        "furnished": 0,
        "description": "Contemporary 2BR with park views. Brand new building, smart home, walking distance to mall.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Smart Home", "Kids Play Area"],
        "images": ["https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3"],
    },
    {
        "reference": "DH-TH-001",
        "title": "Elegant 3BR Townhouse in Maple",
        "property_type": "townhouse",
        "listing_type": "rent",
        "price": Decimal("180000"),
        "rent_period": "yearly",
        "location": "Dubai Hills Estate",
        "community": "Maple",
        "bedrooms": 3,
        "bathrooms": 4,
        "size_sqft": 2200,
        "furnished": 0,
        "description": "Beautiful 3BR townhouse with garden and terrace. Family community, close to school and park.",
        "amenities": ["Garden", "Parking", "Storage", "BBQ Area", "Kids Play Area"],
        "images": ["https://images.unsplash.com/photo-1600585154340-be6161a56a0c"],
    },

    # PALM JUMEIRAH - ULTRA LUXURY
    {
        "reference": "PJ-PH-001",
        "title": "Stunning 4BR Penthouse in Tiara",
        "property_type": "penthouse",
        "listing_type": "buy",
        "price": Decimal("8500000"),
        "location": "Palm Jumeirah",
        "community": "Tiara Residences",
        "bedrooms": 4,
        "bathrooms": 5,
        "size_sqft": 4500,
        "furnished": 1,
        "description": "Ultra-luxury penthouse with 360° views. Private pool, rooftop terrace, beach access, fully upgraded.",
        "amenities": ["Swimming Pool", "Gym", "Parking", "Security", "Balcony", "Beach Access", "Concierge", "Sauna", "Jacuzzi"],
        "images": ["https://images.unsplash.com/photo-1600607687939-ce8a6c25118c"],
    },
]


def seed_demo_properties():
    """Seed demo properties with images and amenities"""
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(Property).filter(Property.is_demo == 1).count()
        if existing > 0:
            print(f"✅ Demo properties already seeded ({existing} found). Skipping.")
            return

        # Get all amenities from database
        amenities_map = {amenity.name: amenity for amenity in db.query(Amenity).all()}

        if not amenities_map:
            print("❌ No amenities found! Please run seed_amenities.py first.")
            return

        # Insert properties
        for prop_data in properties_data:
            # Extract amenities and images
            amenity_names = prop_data.pop("amenities", [])
            image_urls = prop_data.pop("images", [])

            # Create property
            property_obj = Property(**prop_data, is_demo=1)

            # Add amenities
            for amenity_name in amenity_names:
                if amenity_name in amenities_map:
                    property_obj.amenities.append(amenities_map[amenity_name])

            db.add(property_obj)
            db.flush()  # Get the property ID

            # Add images
            for idx, image_url in enumerate(image_urls):
                image = PropertyImage(
                    property_id=property_obj.id,
                    image_url=image_url,
                    is_primary=1 if idx == 0 else 0,
                    display_order=idx,
                )
                db.add(image)

        db.commit()
        print(f"✅ Successfully seeded {len(properties_data)} demo properties!")

        # Count Marina 2BR under 1.5M
        marina_2br_count = db.query(Property).filter(
            Property.location == "Dubai Marina",
            Property.bedrooms == 2,
            Property.listing_type == "buy",
            Property.price <= 1500000,
            Property.availability == "available",
            Property.is_demo == 1
        ).count()
        print(f"✅ Found {marina_2br_count} available 2BR apartments in Marina ≤ AED 1.5M")

    except Exception as e:
        print(f"❌ Error seeding properties: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding demo properties...")
    seed_demo_properties()

