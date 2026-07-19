from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """
    validate credentials used to create a student account
    """

    username: str = Field(
        min_length=3,
        max_length=32,
    )
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """
    validate credentials used to create a session
    """

    username: str
    password: str
