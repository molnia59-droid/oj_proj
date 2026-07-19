from enum import Enum

from pydantic import BaseModel, Field, model_validator


PROBLEM_ID_PATTERN = r"^[A-Za-z0-9_-]{1,32}$"
CASE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class Difficulty(str, Enum):
    """
    allowed difficulty values stored in the database
    """

    easy = "easy"
    medium = "medium"
    hard = "hard"


class SampleData(BaseModel):
    """
    one public input and output example
    """

    input: str
    output: str


class TestCaseCreate(BaseModel):
    """
    one judge test with its own score and visibility setting
    """

    case_id: str | None = Field(
        default=None,
        pattern=CASE_ID_PATTERN,
    )
    input: str
    output: str
    score: int = Field(ge=0, le=100)
    is_hidden: bool = True


class ProblemBase(BaseModel):
    """
    fields shared by problem creation and problem update
    """

    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    input_description: str = Field(min_length=1)
    output_description: str = Field(min_length=1)
    samples: list[SampleData] = Field(min_length=1)
    constraints: str = ""
    time_limit: float = Field(gt=0, le=60)
    memory_limit: int = Field(gt=0, le=4096)
    difficulty: Difficulty
    tags: list[str] = Field(default_factory=list)
    test_cases: list[TestCaseCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_test_cases(self):
        """
        create missing case ids and validate score rules
        """

        case_ids = []

        # generate stable case ids when the teacher leaves them empty
        for index, test_case in enumerate(
            self.test_cases,
            start=1,
        ):
            if not test_case.case_id:
                test_case.case_id = f"case_{index:02d}"

            case_ids.append(test_case.case_id)

        # duplicate case ids would make test logs ambiguous
        if len(case_ids) != len(set(case_ids)):
            raise ValueError(
                "case ids must be unique within one problem"
            )

        # the assignment requires the full problem score to equal one hundred
        total_score = sum(
            test_case.score
            for test_case in self.test_cases
        )

        if total_score != 100:
            raise ValueError(
                "test case scores must total 100"
            )

        return self


class ProblemCreate(ProblemBase):
    """
    request model used when a new problem is created
    """

    id: str = Field(
        min_length=1,
        max_length=32,
        pattern=PROBLEM_ID_PATTERN,
    )


class ProblemUpdate(ProblemBase):
    """
    request model used when an existing problem is updated
    """
