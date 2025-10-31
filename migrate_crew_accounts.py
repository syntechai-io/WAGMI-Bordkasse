"""
Migration script to create User accounts for existing crew members without accounts.
Run this once to migrate existing crew members to have login accounts.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from models import CrewMember, User, UserRole

# Get database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set!")
    exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("=" * 80)
print("CREW MEMBER ACCOUNT MIGRATION")
print("=" * 80)

# Get all crew members without user accounts
crew_without_accounts = db.query(CrewMember).filter(CrewMember.user_id == None).all()

if not crew_without_accounts:
    print("\n✅ All crew members already have user accounts!")
    print("=" * 80)
    db.close()
    exit(0)

print(f"\n📋 Found {len(crew_without_accounts)} crew members without user accounts:")
for member in crew_without_accounts:
    print(f"  - {member.code} ({member.name}) - Trip ID: {member.trip_id}")

print("\n" + "=" * 80)
print("CREATING USER ACCOUNTS")
print("=" * 80)

# Default password for migrated accounts
default_password = "changeme123"
created_count = 0
skipped_count = 0

for member in crew_without_accounts:
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == member.code).first()
    
    if existing_user:
        print(f"\n⚠️  SKIP: Username '{member.code}' already exists (User ID: {existing_user.id})")
        print(f"   Linking existing user to crew member {member.name}")
        member.user_id = existing_user.id
        # Update role based on is_trip_admin flag
        existing_user.role = UserRole.admin if member.is_trip_admin else UserRole.crew
        db.commit()
        skipped_count += 1
        continue
    
    # Create new user account
    user_role = UserRole.admin if member.is_trip_admin else UserRole.crew
    user = User(username=member.code, role=user_role)
    user.set_password(default_password)
    db.add(user)
    db.flush()
    
    # Link to crew member
    member.user_id = user.id
    db.commit()
    
    print(f"\n✅ CREATED: User '{member.code}' for {member.name}")
    print(f"   Role: {user_role.value}, Password: {default_password}, User ID: {user.id}")
    created_count += 1

print("\n" + "=" * 80)
print("MIGRATION SUMMARY")
print("=" * 80)
print(f"✅ Created {created_count} new user accounts")
print(f"🔗 Linked {skipped_count} existing users")
print(f"📊 Total processed: {created_count + skipped_count}")

if created_count > 0:
    print(f"\n⚠️  IMPORTANT: New accounts have default password: '{default_password}'")
    print("   Admins should change these passwords in the crew management page!")

print("\n🎉 Migration complete!")
print("=" * 80)

db.close()
