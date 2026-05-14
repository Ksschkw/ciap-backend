"""
CIAP Seed Script
================
Populates the local database with the creators and SMEs from:
    seeds/creators.json
    seeds/smes.json

What it creates:
    - One User record per person (with bcrypt-hashed password)
    - One CreatorProfile per creator (with all profile fields)
    - One PlatformConnection per platform_connection entry
    - One SMEProfile per SME

Passwords in the JSON files are PLAINTEXT.
This script hashes them with bcrypt — the DB never stores plaintext.

Usage (run from ciap-backend/):
    uv run python seeds/seed.py
    uv run python seeds/seed.py --reset     # wipe & re-seed
"""
from __future__ import annotations
from sqlalchemy.orm import Session
import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Make sure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# ── DATA layer imports (single source of truth) ─────────────────────────────
from DATA.core.database import SessionLocal
from DATA.models.users import (
    User,
    CreatorProfile,
    SMEProfile,
    PlatformConnection,
)

# ── Helpers ──────────────────────────────────────────────────────────────────
SEEDS_DIR = os.path.dirname(__file__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_json(filename: str) -> list[dict]:
    with open(os.path.join(SEEDS_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


# ── Reset ────────────────────────────────────────────────────────────────────

def reset_db(db: Session) -> None:
    print("\nResetting seeded data …")
    # Order matters because of FK constraints
    for model in (
        PlatformConnection,
        CreatorProfile,
        SMEProfile,
        User,
    ):
        deleted = db.query(model).delete()
        print(f"  Deleted {deleted} rows from {model.__tablename__}")
    db.commit()
    print("Done.\n")


# ── Creators ─────────────────────────────────────────────────────────────────

def seed_creators(db: Session) -> None:
    creators = load_json("creators.json")
    print(f"Seeding {len(creators)} creators …\n")

    for data in creators:
        email: str = data["email"]

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"  [SKIP] {email} — already exists")
            continue

        # ── 1. User ──────────────────────────────────────────────────────────
        user = User(
            email=email,
            hashed_password=hash_password(data["password"]),
            role=data["role"],
            full_name=data["full_name"],
            avatar_url=data.get("avatar_url"),
            language_preference=data.get("language_preference", "en"),
            status=data.get("status", "ACTIVE"),
            subscription_plan=data.get("subscription_plan", "FREE"),
            is_email_verified=data.get("is_email_verified", True),
            last_login_at=None,
        )
        db.add(user)
        db.flush()  # gives user.id without committing

        # ── 2. CreatorProfile ─────────────────────────────────────────────────
        p = data.get("profile", {})
        profile = CreatorProfile(
            user_id=user.id,
            category=p.get("category", "Other"),
            secondary_categories=p.get("secondary_categories"),
            bio=p.get("bio"),
            location_country=p.get("location_country"),
            location_city=p.get("location_city"),
            social_handles=p.get("social_handles"),
            influence_score=p.get("influence_score"),
            total_followers=p.get("total_followers"),
            avg_engagement_rate=p.get("avg_engagement_rate"),
            is_public=p.get("is_public", True),
            is_verified=p.get("is_verified", False),
        )
        db.add(profile)
        db.flush()

        # ── 3. PlatformConnections ────────────────────────────────────────────
        for conn_data in data.get("platform_connections", []):
            conn = PlatformConnection(
                user_id=user.id,
                platform_name=conn_data["platform_name"],
                platform_user_id=conn_data["platform_user_id"],
                platform_username=conn_data.get("platform_username"),
                scopes_granted=conn_data.get("scopes_granted"),
                is_active=conn_data.get("is_active", True),
                # Seed tokens are placeholders — real tokens come from OAuth
                access_token=f"seed_token_{conn_data['platform_user_id']}",
                last_synced_at=utcnow(),
            )
            db.add(conn)

        db.commit()
        print(f"  [OK] {data['full_name']}  ({email})")

    print()


# ── SMEs ─────────────────────────────────────────────────────────────────────

def seed_smes(db: Session) -> None:
    smes = load_json("smes.json")
    print(f"Seeding {len(smes)} SMEs …\n")

    for data in smes:
        email: str = data["email"]

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"  [SKIP] {email} — already exists")
            continue

        # ── 1. User ──────────────────────────────────────────────────────────
        user = User(
            email=email,
            hashed_password=hash_password(data["password"]),
            role=data["role"],
            full_name=data["full_name"],
            avatar_url=data.get("avatar_url"),
            language_preference=data.get("language_preference", "en"),
            status=data.get("status", "ACTIVE"),
            subscription_plan=data.get("subscription_plan", "FREE"),
            is_email_verified=data.get("is_email_verified", True),
            last_login_at=None,
        )
        db.add(user)
        db.flush()

        # ── 2. SMEProfile ─────────────────────────────────────────────────────
        p = data.get("profile", {})
        sme_profile = SMEProfile(
            user_id=user.id,
            company_name=p.get("company_name", data["full_name"]),
            industry=p.get("industry", "General"),
            website_url=p.get("website_url"),
            logo_url=p.get("logo_url"),
            description=p.get("description"),
            monthly_budget_ngn=p.get("monthly_budget_ngn"),
        )
        db.add(sme_profile)
        db.commit()
        print(f"  [OK] {data['full_name']} @ {sme_profile.company_name}  ({email})")

    print()


# ── Print login table ─────────────────────────────────────────────────────────

def print_logins() -> None:
    creators = load_json("creators.json")
    smes = load_json("smes.json")

    print("=" * 65)
    print("  SEEDED LOGIN CREDENTIALS")
    print("=" * 65)
    print(f"\n{'CREATORS':}")
    print(f"  {'Name':<30} {'Email':<35} Password")
    print(f"  {'-'*28} {'-'*33} {'-'*20}")
    for c in creators:
        print(f"  {c['full_name']:<30} {c['email']:<35} {c['password']}")

    print(f"\n{'SMEs':}")
    print(f"  {'Name':<30} {'Email':<35} Password")
    print(f"  {'-'*28} {'-'*33} {'-'*20}")
    for s in smes:
        print(f"  {s['full_name']:<30} {s['email']:<35} {s['password']}")
    print("=" * 65)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="CIAP seed script")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all seeded rows before re-seeding",
    )
    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        if args.reset:
            reset_db(db)
        seed_creators(db)
        seed_smes(db)
        print("\nDatabase seeding complete!\n")
        print_logins()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
