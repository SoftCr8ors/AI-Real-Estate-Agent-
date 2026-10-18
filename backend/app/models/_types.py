"""Shared SQLAlchemy column-type helpers for models."""
import enum


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Return member values for use as a SQLAlchemy Enum ``values_callable``.

    SQLAlchemy persists enum member *names* (e.g. ``"AVAILABLE"``) by
    default, but the Postgres enum types created by Alembic store member
    *values* (e.g. ``"available"``). Passing this callable makes the ORM
    match the database schema.
    """
    return [member.value for member in enum_cls]
