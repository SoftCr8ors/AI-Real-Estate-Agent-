"""
Google Calendar Integration Service (Phase 5).

Uses service account authentication to manage calendar events for viewing appointments.
The sales agent's calendar must be shared with the service account email.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings


class GoogleCalendarService:
    """
    Google Calendar API wrapper using service account authentication.

    Service account setup:
    1. Create service account in Google Cloud Console
    2. Download JSON key file
    3. Share sales agent's calendar with service account email
    4. Set GOOGLE_SERVICE_ACCOUNT_FILE and GOOGLE_CALENDAR_ID in .env
    """

    def __init__(self):
        """Initialize Google Calendar service with service account."""
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.timezone = settings.GOOGLE_CALENDAR_TIMEZONE
        self.service = None

        if settings.GOOGLE_SERVICE_ACCOUNT_FILE:
            self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Calendar API service with service account credentials."""
        try:
            service_account_file = Path(settings.GOOGLE_SERVICE_ACCOUNT_FILE)

            if not service_account_file.exists():
                raise FileNotFoundError(
                    f"Service account file not found: {service_account_file}"
                )

            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_file),
                scopes=["https://www.googleapis.com/auth/calendar"]
            )

            # Build the service
            self.service = build("calendar", "v3", credentials=credentials)

        except Exception as e:
            # Log error but don't crash - allow app to run without calendar sync
            print(f"Failed to initialize Google Calendar service: {e}")
            self.service = None

    def is_available(self) -> bool:
        """
        Check if Google Calendar service is available and configured.

        Returns:
            True if service is ready to use
        """
        return (
            self.service is not None
            and self.calendar_id is not None
        )

    def _to_rfc3339(self, dt: datetime) -> str:
        """Format a datetime as RFC3339, which the freeBusy API requires.

        Google rejects timestamps without a UTC offset, so naive datetimes are
        interpreted in the configured calendar timezone.
        """
        if dt.tzinfo is None:
            try:
                dt = dt.replace(tzinfo=ZoneInfo(self.timezone))
            except Exception:
                dt = dt.replace(tzinfo=UTC)
        return dt.isoformat()

    def get_busy_times(
        self,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> list[tuple[datetime, datetime]]:
        """
        Get busy time ranges from Google Calendar.

        Args:
            start_datetime: Start of time range to check
            end_datetime: End of time range to check

        Returns:
            List of (start, end) datetime tuples for busy periods

        Raises:
            RuntimeError: If calendar service not available
            HttpError: If Google API call fails
        """
        if not self.is_available():
            raise RuntimeError("Google Calendar service not available")

        try:
            # Format times for Google API (RFC3339 requires a UTC offset)
            time_min = self._to_rfc3339(start_datetime)
            time_max = self._to_rfc3339(end_datetime)

            # Call freebusy API
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": self.calendar_id}],
                "timeZone": self.timezone
            }

            response = self.service.freebusy().query(body=body).execute()

            # Extract busy periods
            busy_times = []
            calendar_busy = response.get("calendars", {}).get(self.calendar_id, {})

            for busy_period in calendar_busy.get("busy", []):
                start = datetime.fromisoformat(busy_period["start"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(busy_period["end"].replace("Z", "+00:00"))
                busy_times.append((start, end))

            return busy_times

        except HttpError as e:
            raise RuntimeError(f"Failed to fetch busy times from Google Calendar: {e}")

    def create_event(
        self,
        summary: str,
        start_datetime: datetime,
        end_datetime: datetime,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None
    ) -> str:
        """
        Create a calendar event.

        Args:
            summary: Event title
            start_datetime: Event start time
            end_datetime: Event end time
            description: Event description (optional)
            location: Event location (optional)
            attendees: List of attendee email addresses (optional)

        Returns:
            Google Calendar event ID

        Raises:
            RuntimeError: If calendar service not available
            HttpError: If Google API call fails
        """
        if not self.is_available():
            raise RuntimeError("Google Calendar service not available")

        try:
            # Build event body
            event: dict[str, Any] = {
                "summary": summary,
                "start": {
                    "dateTime": start_datetime.isoformat(),
                    "timeZone": self.timezone,
                },
                "end": {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": self.timezone,
                },
            }

            if description:
                event["description"] = description

            if location:
                event["location"] = location

            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]

            # Create event
            created_event = (
                self.service.events()
                .insert(calendarId=self.calendar_id, body=event)
                .execute()
            )

            return created_event["id"]

        except HttpError as e:
            raise RuntimeError(f"Failed to create Google Calendar event: {e}")

    def update_event(
        self,
        event_id: str,
        summary: str | None = None,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        description: str | None = None,
        location: str | None = None
    ) -> None:
        """
        Update an existing calendar event.

        Args:
            event_id: Google Calendar event ID
            summary: New event title (optional)
            start_datetime: New start time (optional)
            end_datetime: New end time (optional)
            description: New description (optional)
            location: New location (optional)

        Raises:
            RuntimeError: If calendar service not available
            HttpError: If Google API call fails
        """
        if not self.is_available():
            raise RuntimeError("Google Calendar service not available")

        try:
            # Get existing event
            event = (
                self.service.events()
                .get(calendarId=self.calendar_id, eventId=event_id)
                .execute()
            )

            # Update fields
            if summary is not None:
                event["summary"] = summary

            if start_datetime is not None:
                event["start"] = {
                    "dateTime": start_datetime.isoformat(),
                    "timeZone": self.timezone,
                }

            if end_datetime is not None:
                event["end"] = {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": self.timezone,
                }

            if description is not None:
                event["description"] = description

            if location is not None:
                event["location"] = location

            # Update event
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()

        except HttpError as e:
            raise RuntimeError(f"Failed to update Google Calendar event: {e}")

    def delete_event(self, event_id: str) -> None:
        """
        Delete a calendar event.

        Args:
            event_id: Google Calendar event ID

        Raises:
            RuntimeError: If calendar service not available
            HttpError: If Google API call fails
        """
        if not self.is_available():
            raise RuntimeError("Google Calendar service not available")

        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

        except HttpError as e:
            # 410 Gone / 404 Not Found means event already deleted - success
            if e.resp.status in (404, 410):
                return

            raise RuntimeError(f"Failed to delete Google Calendar event: {e}")

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """
        Get event details from Google Calendar.

        Args:
            event_id: Google Calendar event ID

        Returns:
            Event dict or None if not found

        Raises:
            RuntimeError: If calendar service not available
        """
        if not self.is_available():
            raise RuntimeError("Google Calendar service not available")

        try:
            event = (
                self.service.events()
                .get(calendarId=self.calendar_id, eventId=event_id)
                .execute()
            )
            # Deleted events are sometimes returned with status "cancelled"
            # instead of a 404; treat them as gone.
            if event.get("status") == "cancelled":
                return None
            return event

        except HttpError as e:
            # 404 Not Found means event doesn't exist
            if e.resp.status == 404:
                return None
            raise


# Singleton instance
_calendar_service: GoogleCalendarService | None = None


def get_calendar_service() -> GoogleCalendarService:
    """
    Get singleton Google Calendar service instance.

    Returns:
        GoogleCalendarService instance
    """
    global _calendar_service

    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()

    return _calendar_service
