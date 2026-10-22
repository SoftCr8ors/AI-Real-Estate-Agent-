"""
Test Real Booking Flow - Books an actual viewing and creates Google Calendar event.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.customer import Customer
from app.models.lead import Lead, LeadStatus
from app.models.property import Property
from app.services.booking import book_viewing
from app.services.slots import generate_time_slots


def test_complete_booking():
    """Test complete booking flow with real Google Calendar."""
    db = SessionLocal()

    print("\n" + "=" * 60)
    print("REAL BOOKING TEST - Google Calendar Integration")
    print("=" * 60)

    try:
        # Step 1: Get a property
        print("\nStep 1: Finding available property...")
        property_obj = db.query(Property).first()
        if not property_obj:
            print("ERROR: No properties found in database")
            return False

        print(f"PASS: Using Property ID {property_obj.id}: {property_obj.title}")

        # Step 2: Create test customer
        print("\nStep 2: Creating test customer...")
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+971501234567",
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        print(f"PASS: Customer created (ID: {customer.id})")

        # Step 3: Create lead
        print("\nStep 3: Creating lead...")
        lead = Lead(
            customer_id=customer.id,
            status=LeadStatus.QUALIFIED,
            source="chat",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        print(f"PASS: Lead created (ID: {lead.id})")

        # Step 4: Get available slots
        print("\nStep 4: Fetching available slots...")
        tomorrow = datetime.now() + timedelta(days=1)
        end_date = tomorrow + timedelta(days=2)

        slots = generate_time_slots(
            db=db,
            property_id=property_obj.id,
            start_date=tomorrow,
            end_date=end_date,
        )

        available_slots = [s for s in slots if s["available"]]

        if not available_slots:
            print("ERROR: No available slots found")
            return False

        print(f"PASS: Found {len(available_slots)} available slots")
        print(f"  First slot: {available_slots[0]['start']}")

        # Step 5: Book the first available slot
        print("\nStep 5: Booking viewing appointment...")
        slot_datetime = datetime.fromisoformat(available_slots[0]["start"])

        appointment = book_viewing(
            db=db,
            lead_id=lead.id,
            property_id=property_obj.id,
            scheduled_at=slot_datetime,
            notes="Test booking via API"
        )

        print(f"PASS: Appointment booked (ID: {appointment.id})")
        print(f"  Scheduled at: {appointment.scheduled_at}")
        print(f"  Duration: {appointment.duration_minutes} minutes")
        print(f"  Status: {appointment.status}")

        # Step 6: Check Google Calendar sync
        print("\nStep 6: Checking Google Calendar sync...")
        print(f"  Sync Status: {appointment.sync_status}")
        print(f"  Google Event ID: {appointment.google_event_id}")

        if appointment.sync_status == "synced" and appointment.google_event_id:
            print("PASS: Successfully synced to Google Calendar!")
            print("\n" + "=" * 60)
            print("SUCCESS! CHECK YOUR GOOGLE CALENDAR NOW!")
            print("=" * 60)
            print("\nLook for event:")
            print(f"  Title: Property Viewing: {property_obj.title}")
            print(f"  Time: {appointment.scheduled_at.strftime('%B %d, %Y at %I:%M %p')}")
            print("  Duration: 45 minutes")
            print(f"  Customer: {customer.name}")
            print(f"  Phone: {customer.phone}")
            print(f"  Email: {customer.email}")
            print("=" * 60)

            # Ask if user wants to delete the test event
            print("\nThis was a test booking.")
            delete = input("Delete this test event from calendar? (y/n): ").lower().strip()

            if delete == 'y':
                from app.services.booking import cancel_appointment
                cancel_appointment(db, appointment.id, "Test booking - cleaned up")
                print("PASS: Test event deleted from Google Calendar")
            else:
                print("Test event kept in calendar. You can delete it manually.")

            return True
        elif appointment.sync_status == "failed":
            print("WARNING: Google Calendar sync failed")
            print(f"  Error: {appointment.sync_error}")
            print("  Appointment is saved in database but not in Google Calendar")
            return False
        else:
            print(f"INFO: Sync status is '{appointment.sync_status}'")
            return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_complete_booking()
    sys.exit(0 if success else 1)
