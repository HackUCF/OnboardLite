# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models.user import MembershipHistoryModel, UserModel

logger = logging.getLogger(__name__)


class MembershipReset:
    """
    Utility class for handling membership resets and historical data archiving.
    """

    @staticmethod
    def reset_all_memberships(
        session: Session,
        reset_reason: str = "Annual membership reset",
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Reset all user memberships and archive their current membership data to history.

        Args:
            session: SQLModel database session
            reset_reason: Reason for the reset (stored in history)
            admin_user_id: UUID of admin performing the reset (for logging)

        Returns:
            dict: Summary of the reset operation
        """
        try:
            # Get all users with their Discord data for snapshots
            statement = select(UserModel).options(selectinload(UserModel.discord))
            users = session.exec(statement).all()

            reset_count = 0
            archived_count = 0
            errors = []

            for user in users:
                try:
                    # Only archive and reset if user was a member
                    if user.is_full_member or user.did_pay_dues:
                        # Create historical record
                        history_record = MembershipHistoryModel(
                            user_id=user.id,
                            reset_date=datetime.utcnow(),
                            was_full_member=user.is_full_member,
                            had_paid_dues=user.did_pay_dues,
                            original_join_date=user.join_date,
                            could_vote=user.can_vote,
                            reset_reason=reset_reason,
                            first_name_snapshot=user.first_name or "",
                            surname_snapshot=user.surname or "",
                            email_snapshot=user.email or "",
                            discord_username_snapshot=user.discord.username if user.discord else "",
                        )
                        user.is_returning = True
                        user.renewal = True
                        user.did_get_shirt = False
                        session.add(history_record)
                        archived_count += 1

                    # Reset membership fields (for all users, not just members)
                    user.is_full_member = False
                    user.did_pay_dues = False
                    user.can_vote = False
                    user.join_date = None

                    # Note: We don't reset personal info, Discord connections, etc.

                    reset_count += 1

                except Exception as e:
                    logger.error(f"Error resetting membership for user {user.id}: {str(e)}")
                    errors.append(f"User {user.id}: {str(e)}")
                    continue

            # Commit all changes
            session.commit()

            logger.info(f"Membership reset completed. Reset: {reset_count}, Archived: {archived_count}, Errors: {len(errors)}")

            return {
                "success": True,
                "reset_count": reset_count,
                "archived_count": archived_count,
                "errors": errors,
                "reset_date": datetime.utcnow().isoformat(),
                "admin_user_id": str(admin_user_id) if admin_user_id else None,
                "reset_reason": reset_reason,
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Critical error during membership reset: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "reset_count": 0,
                "archived_count": 0,
            }

    @staticmethod
    def get_membership_history(
        session: Session,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> List[dict]:
        """
        Get membership history records.

        Args:
            session: SQLModel database session
            user_id: Optional user ID to filter by specific user
            limit: Maximum number of records to return

        Returns:
            List of membership history records
        """
        try:
            statement = select(MembershipHistoryModel).options(selectinload(MembershipHistoryModel.user))

            if user_id:
                statement = statement.where(MembershipHistoryModel.user_id == user_id)

            statement = statement.order_by(MembershipHistoryModel.reset_date).limit(limit)

            history_records = session.exec(statement).all()

            result = []
            for record in history_records:
                result.append(
                    {
                        "id": record.id,
                        "user_id": str(record.user_id),
                        "reset_date": record.reset_date.isoformat(),
                        "was_full_member": record.was_full_member,
                        "had_paid_dues": record.had_paid_dues,
                        "original_join_date": record.original_join_date,
                        "could_vote": record.could_vote,
                        "reset_reason": record.reset_reason,
                        "first_name_snapshot": record.first_name_snapshot,
                        "surname_snapshot": record.surname_snapshot,
                        "email_snapshot": record.email_snapshot,
                        "discord_username_snapshot": record.discord_username_snapshot,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error getting membership history: {str(e)}")
            return []

    @staticmethod
    def get_reset_summary(session: Session) -> dict:
        """
        Get summary statistics about membership resets.

        Args:
            session: SQLModel database session

        Returns:
            dict: Summary statistics
        """
        try:
            # Count total resets
            total_resets = session.exec(select(MembershipHistoryModel)).all()

            # Count unique users affected
            unique_users = set()
            reset_dates = set()

            for record in total_resets:
                unique_users.add(record.user_id)
                reset_dates.add(record.reset_date.date())

            # Get most recent reset
            most_recent_reset = None
            if total_resets:
                most_recent = max(total_resets, key=lambda x: x.reset_date)
                most_recent_reset = most_recent.reset_date.isoformat()

            return {
                "total_reset_records": len(total_resets),
                "unique_users_affected": len(unique_users),
                "number_of_reset_events": len(reset_dates),
                "most_recent_reset": most_recent_reset,
            }

        except Exception as e:
            logger.error(f"Error getting reset summary: {str(e)}")
            return {
                "total_reset_records": 0,
                "unique_users_affected": 0,
                "number_of_reset_events": 0,
                "most_recent_reset": None,
            }

    @staticmethod
    def restore_membership_from_history(
        session: Session,
        user_id: uuid.UUID,
        history_record_id: int,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Restore a user's membership from a historical record.
        This is useful for undoing accidental resets or restoring specific users.

        Args:
            session: SQLModel database session
            user_id: UUID of user to restore
            history_record_id: ID of the history record to restore from
            admin_user_id: UUID of admin performing the restoration

        Returns:
            dict: Result of the restoration operation
        """
        try:
            # Get the user and history record
            user = session.exec(select(UserModel).where(UserModel.id == user_id)).one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

            history_record = session.exec(select(MembershipHistoryModel).where(MembershipHistoryModel.id == history_record_id, MembershipHistoryModel.user_id == user_id)).one_or_none()

            if not history_record:
                return {"success": False, "error": "History record not found"}

            # Restore membership data
            user.is_full_member = history_record.was_full_member
            user.did_pay_dues = history_record.had_paid_dues
            user.can_vote = history_record.could_vote
            user.join_date = history_record.original_join_date

            session.add(user)
            session.commit()

            logger.info(f"Restored membership for user {user_id} from history record {history_record_id}")

            return {
                "success": True,
                "user_id": str(user_id),
                "restored_from_date": history_record.reset_date.isoformat(),
                "admin_user_id": str(admin_user_id) if admin_user_id else None,
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Error restoring membership: {str(e)}")
            return {"success": False, "error": str(e)}
