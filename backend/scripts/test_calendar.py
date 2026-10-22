"""
Manual Google Calendar Integration Test Script.

This script tests the Google Calendar service account setup.
DO NOT run in CI/CD - only for manual testing.

Setup:
1. Create Google Cloud project
2. Enable Google Calendar API
3. Create service account and download JSON key
4. Set GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/key.json in .env
5. Set GOOGLE_CALENDAR_ID=your-calendar-email@gmail.com in .env
6. Share your Google Calendar with the service account email
7. Run: python scripts/test_calendar.py

Expected output:
- PASS: Service configured
- PASS: Can read busy times
- PASS: Can create event
- PASS: Can delete event
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.services.calendar_google import get_calendar_service


def test_configuration():
    """Test that Google Calendar is configured."""
    print("\n" + "=" * 60)
    print("TEST 1: Configuration")
    print("=" * 60)

    print(f"Service account file: {settings.GOOGLE_SERVICE_ACCOUNT_FILE}")
    print(f"Calendar ID: {settings.GOOGLE_CALENDAR_ID}")

    if not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
        print("FAIL: GOOGLE_SERVICE_ACCOUNT_FILE not set in .env")
        return False

    if not settings.GOOGLE_CALENDAR_ID:
        print("FAIL: GOOGLE_CALENDAR_ID not set in .env")
        return False

    service_account_path = Path(settings.GOOGLE_SERVICE_ACCOUNT_FILE)
    if not service_account_path.exists():
        print(f"FAIL: Service account file not found: {service_account_path}")
        return False

    print("PASS: Configuration complete")
    return True


def test_service_initialization():
    """Test that calendar service initializes."""
    print("\n" + "=" * 60)
    print("TEST 2: Service Initialization")
    print("=" * 60)

    calendar_service = get_calendar_service()

    if not calendar_service.is_available():
        print("FAIL: Calendar service not available")
        return False

    print("PASS: Calendar service initialized")
    return True


def test_read_busy_times():
    """Test reading busy times from calendar."""
    print("\n" + "=" * 60)
    print("TEST 3: Read Busy Times")
    print("=" * 60)

    calendar_service = get_calendar_service()

    try:
        # Get busy times for next 7 days
        start = datetime.now()
        end = start + timedelta(days=7)

        print(f"Checking busy times from {start.date()} to {end.date()}...")

        busy_times = calendar_service.get_busy_times(start, end)

        print(f"PASS: Found {len(busy_times)} busy periods")

        if busy_times:
            print("\nBusy periods:")
            for i, (busy_start, busy_end) in enumerate(busy_times[:5], 1):
                print(f"  {i}. {busy_start} to {busy_end}")

            if len(busy_times) > 5:
                print(f"  ... and {len(busy_times) - 5} more")
        else:
            print("  (No busy times found - calendar is clear)")

        return True

    except Exception as e:
        print(f"FAIL: Failed to read busy times: {e}")
        return False


def test_create_and_delete_event():
    """Test creating and deleting a calendar event."""
    print("\n" + "=" * 60)
    print("TEST 4: Create and Delete Event")
    print("=" * 60)

    calendar_service = get_calendar_service()

    try:
        # Create test event tomorrow at 10:00 AM
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=45)

        print(f"Creating test event: {start_time} to {end_time}...")

        event_id = calendar_service.create_event(
            summary="[TEST] Real Estate Viewing - DELETE ME",
            start_datetime=start_time,
            end_datetime=end_time,
            description="This is a test event. Safe to delete.",
            location="Test Property Location"
        )

        print(f"PASS: Event created with ID: {event_id}")

        # Verify event exists
        print("Verifying event exists...")
        event = calendar_service.get_event(event_id)

        if event:
            print(f"PASS: Event verified: {event.get('summary')}")
        else:
            print("FAIL: Event not found after creation")
            return False

        # Delete event
        print("Deleting test event...")
        calendar_service.delete_event(event_id)
        print("PASS: Event deleted")

        # Verify event is gone
        print("Verifying event is deleted...")
        event = calendar_service.get_event(event_id)

        if event is None:
            print("PASS: Event successfully removed")
        else:
            print("FAIL: Event still exists after deletion")
            return False

        return True

    except Exception as e:
        print(f"FAIL: Failed to create/delete event: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GOOGLE CALENDAR INTEGRATION TEST")
    print("=" * 60)
    print("\nThis script tests Google Calendar service account setup.")
    print("Make sure you have:")
    print("1. Created service account and downloaded JSON key")
    print("2. Set GOOGLE_SERVICE_ACCOUNT_FILE in .env")
    print("3. Set GOOGLE_CALENDAR_ID in .env")
    print("4. Shared your calendar with service account email")

    results = []

    # Run tests
    results.append(("Configuration", test_configuration()))

    if results[-1][1]:  # Only continue if configuration passes
        results.append(("Service Initialization", test_service_initialization()))

    if all(r[1] for r in results):  # Only continue if all passed
        results.append(("Read Busy Times", test_read_busy_times()))
        results.append(("Create and Delete Event", test_create_and_delete_event()))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "PASS: PASS" if passed else "FAIL: FAIL"
        print(f"{status} - {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nPassed: {total_passed}/{total_tests}")

    if all(r[1] for r in results):
        print("\nPASS: All tests passed! Google Calendar integration is working.")
        return 0
    else:
        print("\nFAIL: Some tests failed. Check the error messages above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
