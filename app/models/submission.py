from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.problem import PROBLEM_ID_PATTERN


class SubmissionCreate(BaseModel):
    """
    validate a python solution before it reaches the judge
    """

    problem_id: str = Field(
        min_length=1,
        max_length=32,
        pattern=PROBLEM_ID_PATTERN,
    )
    language: Literal["python"]
    source_code: str

    @model_validator(mode="after")
    def validate_source_code(self):
        """
        reject empty or excessively large source files
        """

        if not self.source_code.strip():
            raise ValueError(
                "source code must not be empty"
            )

        source_size = len(
            self.source_code.encode("utf-8")
        )

        if source_size > 64 * 1024:
            raise ValueError(
                "source code size must not exceed 64 kib"
            )

        return self
