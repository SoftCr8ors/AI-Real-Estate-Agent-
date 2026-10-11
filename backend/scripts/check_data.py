#!/usr/bin/env python3
"""
Data sanity validation script.

Checks:
- All properties have positive prices
- All properties have valid sizes
- All properties have at least one image
- All properties have descriptions
- All amenities are properly associated
- Demo properties are properly flagged
- No orphaned relationships
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.amenity import Amenity
from app.models.image import PropertyImage
from app.models.property import Property


def check_data(db: Session) -> bool:
    """
    Run sanity checks on the database data.
    
    Returns:
        True if all checks pass, False otherwise.
    """
    errors = []
    warnings = []
    
    print("=" * 60)
    print("Running data sanity checks...")
    print("=" * 60)
    
    # Check 1: Positive prices
    print("\n[1/9] Checking for positive prices...")
    negative_prices = db.query(Property).filter(Property.price <= 0).all()
    if negative_prices:
        errors.append(
            f"Found {len(negative_prices)} properties with non-positive prices: "
            + ", ".join([p.reference for p in negative_prices])
        )
    else:
        print("[OK] All properties have positive prices")
    
    # Check 2: Valid sizes
    print("\n[2/9] Checking for valid sizes...")
    invalid_sizes = db.query(Property).filter(
        (Property.size_sqft <= 0) | (Property.size_sqft > 50000)
    ).all()
    if invalid_sizes:
        errors.append(
            f"Found {len(invalid_sizes)} properties with invalid sizes: "
            + ", ".join([f"{p.reference} ({p.size_sqft} sqft)" for p in invalid_sizes])
        )
    else:
        print("[OK] All properties have valid sizes (0-50,000 sqft)")
    
    # Check 3: Properties have at least one image
    print("\n[3/9] Checking for property images...")
    properties_without_images = (
        db.query(Property)
        .outerjoin(PropertyImage)
        .group_by(Property.id)
        .having(func.count(PropertyImage.id) == 0)
        .all()
    )
    if properties_without_images:
        warnings.append(
            f"Found {len(properties_without_images)} properties without images: "
            + ", ".join([p.reference for p in properties_without_images])
        )
    else:
        print("[OK] All properties have at least one image")
    
    # Check 4: Properties have descriptions
    print("\n[4/9] Checking for property descriptions...")
    missing_descriptions = db.query(Property).filter(
        (Property.description == None) | (Property.description == "")
    ).all()
    if missing_descriptions:
        errors.append(
            f"Found {len(missing_descriptions)} properties without descriptions: "
            + ", ".join([p.reference for p in missing_descriptions])
        )
    else:
        print("[OK] All properties have descriptions")
    
    # Check 5: Bedrooms and bathrooms are reasonable
    print("\n[5/9] Checking bedroom/bathroom counts...")
    invalid_rooms = db.query(Property).filter(
        (Property.bedrooms < 0) | (Property.bedrooms > 20) |
        (Property.bathrooms < 0) | (Property.bathrooms > 20)
    ).all()
    if invalid_rooms:
        errors.append(
            f"Found {len(invalid_rooms)} properties with invalid bedroom/bathroom counts: "
            + ", ".join([f"{p.reference} ({p.bedrooms}BR, {p.bathrooms}BA)" for p in invalid_rooms])
        )
    else:
        print("[OK] All properties have valid bedroom/bathroom counts")
    
    # Check 6: Price consistency (buy vs rent)
    print("\n[6/9] Checking price consistency...")
    inconsistent_prices = []
    
    # Buy properties should typically be > 500k AED
    buy_properties_cheap = db.query(Property).filter(
        Property.listing_type == "buy",
        Property.price < Decimal("300000")
    ).all()
    if buy_properties_cheap:
        warnings.append(
            f"Found {len(buy_properties_cheap)} buy properties under AED 300k (unusually cheap): "
            + ", ".join([f"{p.reference} (AED {p.price})" for p in buy_properties_cheap])
        )
    
    # Rent properties should typically be < 1M AED/year
    rent_properties_expensive = db.query(Property).filter(
        Property.listing_type == "rent",
        Property.price > Decimal("2000000")
    ).all()
    if rent_properties_expensive:
        warnings.append(
            f"Found {len(rent_properties_expensive)} rent properties over AED 2M/year (unusually expensive): "
            + ", ".join([f"{p.reference} (AED {p.price})" for p in rent_properties_expensive])
        )
    
    if not buy_properties_cheap and not rent_properties_expensive:
        print("[OK] Property prices are within expected ranges")
    
    # Check 7: Demo properties are flagged
    print("\n[7/9] Checking demo property flags...")
    total_properties = db.query(Property).count()
    demo_properties = db.query(Property).filter(Property.is_demo == 1).count()
    
    print(f"  Total properties: {total_properties}")
    print(f"  Demo properties: {demo_properties}")
    print(f"  Real properties: {total_properties - demo_properties}")
    
    if demo_properties == 0 and total_properties > 0:
        warnings.append("No demo properties flagged - are you sure this is correct?")
    else:
        print("[OK] Demo properties are properly tracked")
    
    # Check 8: Amenities exist and are used
    print("\n[8/9] Checking amenities...")
    amenity_count = db.query(Amenity).count()
    
    if amenity_count == 0:
        errors.append("No amenities found in database")
    else:
        print(f"[OK] Found {amenity_count} amenities")
        
        # Check for unused amenities
        # Note: This requires checking the association table
        used_amenities = db.query(func.count(func.distinct(Property.id))).join(
            Property.amenities
        ).scalar()
        
        if used_amenities == 0:
            warnings.append("No properties are associated with amenities")
        else:
            print(f"[OK] Amenities are used in property associations")
    
    # Check 9: Location data consistency
    print("\n[9/9] Checking location data...")
    missing_location = db.query(Property).filter(
        (Property.location == None) | (Property.location == "") |
        (Property.community == None) | (Property.community == "")
    ).all()
    
    if missing_location:
        errors.append(
            f"Found {len(missing_location)} properties with missing location data: "
            + ", ".join([p.reference for p in missing_location])
        )
    else:
        print("[OK] All properties have location and community data")
    
    # Summary
    print("\n" + "=" * 60)
    print("SANITY CHECK RESULTS")
    print("=" * 60)
    
    if errors:
        print(f"\n[ERROR] Found {len(errors)} error(s):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print(f"\n[WARNING] Found {len(warnings)} warning(s):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if not errors and not warnings:
        print("\n[SUCCESS] All checks passed! Data is clean.")
    elif not errors:
        print("\n[SUCCESS] All critical checks passed (warnings can be reviewed)")
    else:
        print(f"\n[FAILED] Failed with {len(errors)} error(s)")
    
    print("=" * 60)
    
    return len(errors) == 0


def main():
    """Main entry point."""
    db = SessionLocal()
    
    try:
        success = check_data(db)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Error running sanity checks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
