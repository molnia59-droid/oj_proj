from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    """
    roles supported by the authorization system
    """

    student = "student"
    teacher = "teacher"
    admin = "admin"


class UserUpdate(BaseModel):
    """
    fields an administrator may change for another account
    """

    role: UserRole
    is_active: bool
