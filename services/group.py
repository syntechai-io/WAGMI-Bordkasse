"""
Crew Group Service
Handles settlement group management (combining crew members for settlement)
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from models import CrewGroup, CrewGroupMember, CrewMember, Trip
from typing import Optional, List, Dict
from datetime import datetime


class GroupService:
    """Service for managing crew settlement groups"""
    
    @staticmethod
    def create_group(
        db: Session,
        trip_id: int,
        name: str,
        representative_member_id: int,
        member_ids: List[int]
    ) -> CrewGroup:
        """
        Create a new settlement group
        
        Args:
            db: Database session
            trip_id: Trip ID
            name: Group name (e.g., "Smith Family", "Anna & Tom")
            representative_member_id: ID of crew member who settles for the group
            member_ids: List of member IDs to include in group (including representative)
        
        Returns:
            CrewGroup: Created group
        
        Raises:
            ValueError: If validation fails
        """
        # Validation: Check trip exists
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            raise ValueError(f"Trip {trip_id} not found")
        
        # Validation: Check representative exists and belongs to trip
        representative = db.query(CrewMember).filter(
            and_(
                CrewMember.id == representative_member_id,
                CrewMember.trip_id == trip_id
            )
        ).first()
        if not representative:
            raise ValueError(f"Representative member {representative_member_id} not found in trip {trip_id}")
        
        # Validation: Representative must be in member list
        if representative_member_id not in member_ids:
            raise ValueError("Representative must be included in group members")
        
        # Validation: Check all members exist and belong to this trip
        members = db.query(CrewMember).filter(
            and_(
                CrewMember.id.in_(member_ids),
                CrewMember.trip_id == trip_id
            )
        ).all()
        
        if len(members) != len(member_ids):
            raise ValueError("Some members not found or belong to different trip")
        
        # Validation: Check members aren't already in another group
        existing_memberships = db.query(CrewGroupMember).filter(
            CrewGroupMember.member_id.in_(member_ids)
        ).all()
        
        if existing_memberships:
            conflicting_names = [m.member.name for m in existing_memberships]
            raise ValueError(f"Members already in groups: {', '.join(conflicting_names)}")
        
        # Validation: Check group name is unique for this trip
        existing_group = db.query(CrewGroup).filter(
            and_(
                CrewGroup.trip_id == trip_id,
                CrewGroup.name == name
            )
        ).first()
        
        if existing_group:
            raise ValueError(f"Group name '{name}' already exists for this trip")
        
        # Create group
        group = CrewGroup(
            trip_id=trip_id,
            name=name,
            representative_member_id=representative_member_id,
            created_at=datetime.utcnow()
        )
        db.add(group)
        db.flush()  # Get group.id
        
        # Add members to group
        for member_id in member_ids:
            group_member = CrewGroupMember(
                group_id=group.id,
                member_id=member_id,
                created_at=datetime.utcnow()
            )
            db.add(group_member)
        
        db.commit()
        db.refresh(group)
        return group
    
    @staticmethod
    def get_group_by_id(db: Session, group_id: int) -> Optional[CrewGroup]:
        """Get group by ID with all relationships loaded"""
        return db.query(CrewGroup).filter(CrewGroup.id == group_id).first()
    
    @staticmethod
    def get_groups_for_trip(db: Session, trip_id: int) -> List[CrewGroup]:
        """Get all groups for a trip"""
        return db.query(CrewGroup).filter(CrewGroup.trip_id == trip_id).all()
    
    @staticmethod
    def get_member_group(db: Session, member_id: int) -> Optional[CrewGroup]:
        """Get the group that a member belongs to (if any)"""
        membership = db.query(CrewGroupMember).filter(
            CrewGroupMember.member_id == member_id
        ).first()
        
        if membership:
            return membership.group
        return None
    
    @staticmethod
    def update_group_members(
        db: Session,
        group_id: int,
        member_ids: List[int]
    ) -> CrewGroup:
        """
        Update group membership
        
        Args:
            db: Database session
            group_id: Group ID
            member_ids: New list of member IDs
        
        Returns:
            CrewGroup: Updated group
        
        Raises:
            ValueError: If validation fails
        """
        group = db.query(CrewGroup).filter(CrewGroup.id == group_id).first()
        if not group:
            raise ValueError(f"Group {group_id} not found")
        
        # Validation: Representative must be in new member list
        if group.representative_member_id not in member_ids:
            raise ValueError("Representative must remain in group. Change representative first.")
        
        # Validation: Check all members exist and belong to this trip
        members = db.query(CrewMember).filter(
            and_(
                CrewMember.id.in_(member_ids),
                CrewMember.trip_id == group.trip_id
            )
        ).all()
        
        if len(members) != len(member_ids):
            raise ValueError("Some members not found or belong to different trip")
        
        # Get current member IDs
        current_member_ids = {m.member_id for m in group.members}
        new_member_ids = set(member_ids)
        
        # Members to remove
        to_remove = current_member_ids - new_member_ids
        if to_remove:
            db.query(CrewGroupMember).filter(
                and_(
                    CrewGroupMember.group_id == group_id,
                    CrewGroupMember.member_id.in_(to_remove)
                )
            ).delete(synchronize_session=False)
        
        # Members to add
        to_add = new_member_ids - current_member_ids
        for member_id in to_add:
            # Check if member is already in another group
            existing = db.query(CrewGroupMember).filter(
                CrewGroupMember.member_id == member_id
            ).first()
            if existing:
                raise ValueError(f"Member {member_id} already in another group")
            
            group_member = CrewGroupMember(
                group_id=group_id,
                member_id=member_id,
                created_at=datetime.utcnow()
            )
            db.add(group_member)
        
        db.commit()
        db.refresh(group)
        return group
    
    @staticmethod
    def change_representative(
        db: Session,
        group_id: int,
        new_representative_id: int
    ) -> CrewGroup:
        """
        Change the group representative
        
        Args:
            db: Database session
            group_id: Group ID
            new_representative_id: New representative member ID
        
        Returns:
            CrewGroup: Updated group
        
        Raises:
            ValueError: If validation fails
        """
        group = db.query(CrewGroup).filter(CrewGroup.id == group_id).first()
        if not group:
            raise ValueError(f"Group {group_id} not found")
        
        # Validation: New representative must be a member of the group
        is_member = db.query(CrewGroupMember).filter(
            and_(
                CrewGroupMember.group_id == group_id,
                CrewGroupMember.member_id == new_representative_id
            )
        ).first()
        
        if not is_member:
            raise ValueError("New representative must be a member of the group")
        
        group.representative_member_id = new_representative_id
        db.commit()
        db.refresh(group)
        return group
    
    @staticmethod
    def delete_group(db: Session, group_id: int) -> None:
        """
        Delete a settlement group (members become independent again)
        
        Args:
            db: Database session
            group_id: Group ID
        
        Raises:
            ValueError: If group not found
        """
        group = db.query(CrewGroup).filter(CrewGroup.id == group_id).first()
        if not group:
            raise ValueError(f"Group {group_id} not found")
        
        # Members will cascade delete due to relationship
        db.delete(group)
        db.commit()
    
    @staticmethod
    def get_group_member_ids(db: Session, group_id: int) -> List[int]:
        """Get list of member IDs in a group"""
        members = db.query(CrewGroupMember.member_id).filter(
            CrewGroupMember.group_id == group_id
        ).all()
        return [m[0] for m in members]
    
    @staticmethod
    def is_member_in_group(db: Session, member_id: int) -> bool:
        """Check if a crew member is in any settlement group"""
        membership = db.query(CrewGroupMember).filter(
            CrewGroupMember.member_id == member_id
        ).first()
        return membership is not None
    
    @staticmethod
    def can_delete_member(db: Session, member_id: int) -> tuple[bool, Optional[str]]:
        """
        Check if a crew member can be deleted
        
        Returns:
            (can_delete, reason) - reason is None if can delete
        """
        # Check if member is in a group
        membership = db.query(CrewGroupMember).filter(
            CrewGroupMember.member_id == member_id
        ).first()
        
        if membership:
            return False, f"Member is in settlement group '{membership.group.name}'. Remove from group first."
        
        # Check if member is a representative
        representing = db.query(CrewGroup).filter(
            CrewGroup.representative_member_id == member_id
        ).first()
        
        if representing:
            return False, f"Member is representative for group '{representing.name}'. Change representative first."
        
        return True, None
