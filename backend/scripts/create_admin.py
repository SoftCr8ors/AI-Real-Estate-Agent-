#!/usr/bin/env python3
"""
Create admin user from environment variables.

Usage:
    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secret123 ADMIN_FULL_NAME="Admin User" python create_admin.py

Environment variables:
    ADMIN_EMAIL: Email address for admin user (required)
    ADMIN_PASSWORD: Plain text password (will be hashed) (required)
    ADMIN_FULL_NAME: Full name of admin user (required)
    ADMIN_ROLE: Role (admin or agent, default: admin)
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.admin_user import AdminUser, UserRole

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_admin_user(
    email: str,
    password: str,
    full_name: str,
    role: str = "admin"
) -> bool:
    """
    Create an admin user in the database.

    Args:
        email: Email address
        password: Plain text password (will be hashed)
        full_name: Full name
        role: Role (admin or agent)

    Returns:
        True if user was created, False otherwise
    """
    db = SessionLocal()

    try:
        # Validate role
        try:
            user_role = UserRole(role.lower())
        except ValueError:
            print(f"❌ Invalid role: {role}. Must be 'admin' or 'agent'.")
            return False

        # Check if user already exists
        existing_user = db.query(AdminUser).filter(AdminUser.email == email).first()

        if existing_user:
            print(f"⚠️  User with email {email} already exists.")
            print(f"   ID: {existing_user.id}")
            print(f"   Name: {existing_user.full_name}")
            print(f"   Role: {existing_user.role.value}")
            print(f"   Active: {'Yes' if existing_user.is_active else 'No'}")
            return False

        # Hash password
        hashed_password = hash_password(password)

        # Create admin user
        admin_user = AdminUser(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=user_role,
            is_active=1,
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("=" * 60)
        print("✅ Admin user created successfully!")
        print("=" * 60)
        print(f"ID:        {admin_user.id}")
        print(f"Email:     {admin_user.email}")
        print(f"Name:      {admin_user.full_name}")
        print(f"Role:      {admin_user.role.value}")
        print(f"Active:    {'Yes' if admin_user.is_active else 'No'}")
        print(f"Created:   {admin_user.created_at}")
        print("=" * 60)

        return True

    except IntegrityError as e:
        db.rollback()
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Main entry point."""
    print("=" * 60)
    print("Admin User Creation Script")
    print("=" * 60)

    # Get environment variables
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    full_name = os.getenv("ADMIN_FULL_NAME")
    role = os.getenv("ADMIN_ROLE", "admin")

    # Validate required variables
    missing = []
    if not email:
        missing.append("ADMIN_EMAIL")
    if not password:
        missing.append("ADMIN_PASSWORD")
    if not full_name:
        missing.append("ADMIN_FULL_NAME")

    if missing:
        print("\n❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nUsage:")
        print("  ADMIN_EMAIL=admin@example.com \\")
        print("  ADMIN_PASSWORD=secret123 \\")
        print("  ADMIN_FULL_NAME=\"Admin User\" \\")
        print("  ADMIN_ROLE=admin \\")
        print("  python scripts/create_admin.py")
        print("\nOr set them in your .env file:")
        print("  ADMIN_EMAIL=admin@example.com")
        print("  ADMIN_PASSWORD=secret123")
        print("  ADMIN_FULL_NAME=Admin User")
        print("  ADMIN_ROLE=admin")
        sys.exit(1)

    # Validate email format (basic check)
    if "@" not in email or "." not in email.split("@")[1]:
        print(f"❌ Invalid email format: {email}")
        sys.exit(1)

    # Validate password strength (basic check)
    if len(password) < 8:
        print("❌ Password must be at least 8 characters long")
        sys.exit(1)

    print("\nCreating admin user:")
    print(f"  Email:     {email}")
    print(f"  Name:      {full_name}")
    print(f"  Role:      {role}")
    print(f"  Password:  {'*' * len(password)}")
    print()

    # Create user
    success = create_admin_user(email, password, full_name, role)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
