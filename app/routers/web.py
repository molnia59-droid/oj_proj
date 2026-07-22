from itertools import zip_longest
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Form,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.models.problem import (
    ProblemCreate,
    ProblemUpdate,
    SampleData,
    TestCaseCreate,
)
from app.models.submission import SubmissionCreate
from app.models.user import UserRole, UserUpdate
from app.repositories.user_repository import (
    find_by_id,
    touch_user_last_seen,
)
from app.services.auth_service import (
    authenticate_user,
    register_user,
)
from app.services.problem_service import (
    create_new_problem,
    delete_existing_problem,
    get_problem_detail,
    get_problem_list,
    update_existing_problem,
)
from app.services.submission_service import (
    create_new_submission,
    get_submission_detail,
    get_submission_list,
    get_submission_logs,
    prepare_submission_rejudge,
    process_submission,
)
from app.services.user_service import (
    get_user_list,
    update_user_account,
)


# resolve templates from the project root
BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["web"])


def get_web_user(request: Request) -> dict | None:
    """
    return the current active user for an html request
    """

    user_id = request.session.get("user_id")

    if user_id is None:
        return None

    user = find_by_id(user_id)

    if user is None or not user["is_active"]:
        request.session.clear()
        return None

    # html requests update the same online presence field as api requests
    touch_user_last_seen(user["id"])
    user["is_active"] = bool(user["is_active"])

    return user


def set_flash(
    request: Request,
    message: str,
    kind: str = "info",
) -> None:
    """
    save one message that is displayed after a redirect
    """

    request.session["flash"] = {
        "message": message,
        "kind": kind,
    }


def render_page(
    request: Request,
    template_name: str,
    context: dict | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """
    render one template with shared navigation data
    """

    # reuse a user already loaded by the route to avoid a second database write
    supplied_user = (
        context.get("current_user")
        if context is not None
        else None
    )

    page_context = {
        "request": request,
        "current_user": (
            supplied_user
            if supplied_user is not None
            else get_web_user(request)
        ),
        "flash": request.session.pop("flash", None),
    }

    if context:
        page_context.update(context)

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=page_context,
        status_code=status_code,
    )


def login_redirect() -> RedirectResponse:
    """
    redirect an unauthenticated browser to login
    """

    return RedirectResponse(
        url="/web/login",
        status_code=303,
    )


def require_web_role(
    request: Request,
    *allowed_roles: str,
) -> tuple[dict | None, RedirectResponse | None]:
    """
    check authentication and role for an html route
    """

    current_user = get_web_user(request)

    if current_user is None:
        return None, login_redirect()

    if current_user["role"] not in allowed_roles:
        set_flash(request, "permission denied", "error")
        return None, RedirectResponse(
            url="/web/problems",
            status_code=303,
        )

    return current_user, None


def parse_optional_positive_int(
    value: str | None,
) -> int | None:
    """
    parse one optional positive integer from an html filter
    """

    if value is None or not value.strip():
        return None

    parsed_value = int(value)

    if parsed_value <= 0:
        raise ValueError("value must be greater than zero")

    return parsed_value


def distribute_test_scores(test_count: int) -> list[int]:
    """
    split one hundred points across all testcases
    """

    if test_count <= 0:
        raise ValueError("at least one test case is required")

    base_score, remainder = divmod(100, test_count)

    return [
        base_score + (1 if index < remainder else 0)
        for index in range(test_count)
    ]


def empty_problem_form() -> dict:
    """
    return initial values for the create problem page
    """

    return {
        "id": "",
        "title": "",
        "description": "",
        "input_description": "",
        "output_description": "",
        "constraints": "",
        "time_limit": "1.0",
        "memory_limit": "128",
        "difficulty": "easy",
        "tags": "",
        "score_mode": "auto",
        "sample": {
            "input": "",
            "output": "",
        },
        "test_cases": [
            {
                "case_id": "case_01",
                "input": "",
                "output": "",
                "score": "100",
                "is_hidden": True,
            }
        ],
    }


def problem_to_form(problem: dict) -> dict:
    """
    convert api problem data into html form values
    """

    sample = (
        problem["samples"][0]
        if problem.get("samples")
        else {"input": "", "output": ""}
    )
    test_cases = [
        {
            "case_id": test_case["case_id"],
            "input": test_case["input"],
            "output": test_case["output"],
            "score": str(test_case["score"]),
            "is_hidden": bool(test_case["is_hidden"]),
        }
        for test_case in problem.get("test_cases", [])
    ]

    if not test_cases:
        test_cases = empty_problem_form()["test_cases"]

    return {
        "id": problem["id"],
        "title": problem["title"],
        "description": problem["description"],
        "input_description": problem["input_description"],
        "output_description": problem["output_description"],
        "constraints": problem.get("constraints", ""),
        "time_limit": str(problem["time_limit"]),
        "memory_limit": str(problem["memory_limit"]),
        "difficulty": problem["difficulty"],
        "tags": ", ".join(problem["tags"]),
        "score_mode": "manual",
        "sample": {
            "input": sample["input"],
            "output": sample["output"],
        },
        "test_cases": test_cases,
    }


def raw_problem_form(
    problem_id: str,
    title: str,
    description: str,
    input_description: str,
    output_description: str,
    constraints: str,
    time_limit: str,
    memory_limit: str,
    difficulty: str,
    tags: str,
    score_mode: str,
    sample_input: str,
    sample_output: str,
    test_case_id: list[str],
    test_input: list[str],
    test_output: list[str],
    test_score: list[str],
    test_hidden: list[str],
) -> dict:
    """
    preserve submitted form values when validation fails
    """

    test_cases = [
        {
            "case_id": case_id,
            "input": input_data,
            "output": output_data,
            "score": score,
            "is_hidden": hidden == "1",
        }
        for case_id, input_data, output_data, score, hidden in zip_longest(
            test_case_id,
            test_input,
            test_output,
            test_score,
            test_hidden,
            fillvalue="",
        )
    ]

    return {
        "id": problem_id,
        "title": title,
        "description": description,
        "input_description": input_description,
        "output_description": output_description,
        "constraints": constraints,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "difficulty": difficulty,
        "tags": tags,
        "score_mode": score_mode,
        "sample": {
            "input": sample_input,
            "output": sample_output,
        },
        "test_cases": test_cases,
    }


def build_problem_model(
    form_data: dict,
    include_id: bool,
) -> ProblemCreate | ProblemUpdate:
    """
    convert html form values into validated pydantic models
    """

    raw_test_cases = form_data["test_cases"]

    if not raw_test_cases:
        raise ValueError("at least one test case is required")

    if form_data["score_mode"] == "auto":
        scores = distribute_test_scores(
            len(raw_test_cases)
        )
    elif form_data["score_mode"] == "manual":
        scores = [
            int(test_case["score"])
            for test_case in raw_test_cases
        ]
    else:
        raise ValueError("invalid score mode")

    test_cases = [
        TestCaseCreate(
            case_id=(
                test_case["case_id"].strip()
                or None
            ),
            input=test_case["input"],
            output=test_case["output"],
            score=scores[index],
            is_hidden=test_case["is_hidden"],
        )
        for index, test_case in enumerate(raw_test_cases)
    ]

    tags = [
        tag.strip()
        for tag in form_data["tags"].split(",")
        if tag.strip()
    ]

    model_data = {
        "title": form_data["title"],
        "description": form_data["description"],
        "input_description": form_data[
            "input_description"
        ],
        "output_description": form_data[
            "output_description"
        ],
        "samples": [
            SampleData(
                input=form_data["sample"]["input"],
                output=form_data["sample"]["output"],
            )
        ],
        "constraints": form_data["constraints"],
        "time_limit": float(form_data["time_limit"]),
        "memory_limit": int(form_data["memory_limit"]),
        "difficulty": form_data["difficulty"],
        "tags": tags,
        "test_cases": test_cases,
    }

    if include_id:
        model_data["id"] = form_data["id"]
        return ProblemCreate(**model_data)

    return ProblemUpdate(**model_data)


@router.get("/", include_in_schema=False)
async def root_page():
    """
    redirect the root url to the problem list
    """

    return RedirectResponse(
        url="/web/problems",
        status_code=303,
    )


@router.get("/web/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    display the login form
    """

    if get_web_user(request) is not None:
        return RedirectResponse(
            url="/web/problems",
            status_code=303,
        )

    return render_page(
        request,
        "login.html",
        {"title": "login"},
    )


@router.post("/web/login", response_class=HTMLResponse)
async def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """
    authenticate credentials and create the browser session
    """

    try:
        user = authenticate_user(username, password)
    except PermissionError as error:
        return render_page(
            request,
            "login.html",
            {
                "title": "login",
                "error": str(error),
                "username": username,
            },
            status_code=403,
        )

    if user is None:
        return render_page(
            request,
            "login.html",
            {
                "title": "login",
                "error": "invalid username or password",
                "username": username,
            },
            status_code=401,
        )

    request.session.clear()
    request.session["user_id"] = user["id"]
    touch_user_last_seen(user["id"])

    return RedirectResponse(
        url="/web/problems",
        status_code=303,
    )


@router.get("/web/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    display the registration form
    """

    if get_web_user(request) is not None:
        return RedirectResponse(
            url="/web/problems",
            status_code=303,
        )

    return render_page(
        request,
        "register.html",
        {"title": "register"},
    )


@router.post("/web/register", response_class=HTMLResponse)
async def register_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """
    create a student account and sign it in
    """

    try:
        user = register_user(username, password)
    except ValueError as error:
        return render_page(
            request,
            "register.html",
            {
                "title": "register",
                "error": str(error),
                "username": username,
            },
            status_code=422,
        )

    request.session.clear()
    request.session["user_id"] = user["id"]
    touch_user_last_seen(user["id"])

    return RedirectResponse(
        url="/web/problems",
        status_code=303,
    )


@router.post("/web/logout")
async def web_logout(
    request: Request,
):
    """
    log out the current web user
    """

    # remove the user id from the signed session cookie
    request.session.clear()

    return RedirectResponse(
        url="/web/login",
        status_code=303,
    )


@router.get("/web/problems", response_class=HTMLResponse)
async def problems_page(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """
    display the active problem list
    """

    current_user = get_web_user(request)

    if current_user is None:
        return login_redirect()

    return render_page(
        request,
        "problems.html",
        {
            "title": "problems",
            "data": get_problem_list(page, page_size),
            "current_user": current_user,
        },
    )


@router.get("/web/problems/new", response_class=HTMLResponse)
async def create_problem_page(request: Request):
    """
    display the create problem form
    """

    current_user, redirect = require_web_role(
        request,
        "teacher",
        "admin",
    )

    if redirect is not None:
        return redirect

    return render_page(
        request,
        "problem_form.html",
        {
            "title": "create problem",
            "mode": "create",
            "form_data": empty_problem_form(),
            "current_user": current_user,
        },
    )


@router.post("/web/problems/new", response_class=HTMLResponse)
async def create_problem_action(
    request: Request,
    problem_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    input_description: str = Form(...),
    output_description: str = Form(...),
    constraints: str = Form(""),
    time_limit: str = Form(...),
    memory_limit: str = Form(...),
    difficulty: str = Form(...),
    tags: str = Form(""),
    score_mode: str = Form(...),
    sample_input: str = Form(...),
    sample_output: str = Form(...),
    test_case_id: list[str] = Form(...),
    test_input: list[str] = Form(...),
    test_output: list[str] = Form(...),
    test_score: list[str] = Form(...),
    test_hidden: list[str] = Form(...),
):
    """
    validate and create a problem from html form fields
    """

    current_user, redirect = require_web_role(
        request,
        "teacher",
        "admin",
    )

    if redirect is not None:
        return redirect

    form_data = raw_problem_form(
        problem_id,
        title,
        description,
        input_description,
        output_description,
        constraints,
        time_limit,
        memory_limit,
        difficulty,
        tags,
        score_mode,
        sample_input,
        sample_output,
        test_case_id,
        test_input,
        test_output,
        test_score,
        test_hidden,
    )

    try:
        problem = build_problem_model(
            form_data,
            include_id=True,
        )
        create_new_problem(problem)
    except (ValidationError, ValueError) as error:
        return render_page(
            request,
            "problem_form.html",
            {
                "title": "create problem",
                "mode": "create",
                "form_data": form_data,
                "error": str(error),
                "current_user": current_user,
            },
            status_code=422,
        )

    set_flash(request, "problem created", "success")

    return RedirectResponse(
        url=f"/web/problems/{problem.id}",
        status_code=303,
    )


@router.get(
    "/web/problems/{problem_id}/edit",
    response_class=HTMLResponse,
)
async def edit_problem_page(
    request: Request,
    problem_id: str,
):
    """
    display the edit form with full testcase data
    """

    current_user, redirect = require_web_role(
        request,
        "teacher",
        "admin",
    )

    if redirect is not None:
        return redirect

    problem = get_problem_detail(
        problem_id,
        include_tests=True,
    )

    if problem is None:
        return render_page(
            request,
            "message.html",
            {
                "title": "problem not found",
                "heading": "problem not found",
                "message": "problem not found",
            },
            status_code=404,
        )

    return render_page(
        request,
        "problem_form.html",
        {
            "title": "edit problem",
            "mode": "edit",
            "problem_id": problem_id,
            "form_data": problem_to_form(problem),
            "current_user": current_user,
        },
    )


@router.post(
    "/web/problems/{problem_id}/edit",
    response_class=HTMLResponse,
)
async def edit_problem_action(
    request: Request,
    problem_id: str,
    title: str = Form(...),
    description: str = Form(...),
    input_description: str = Form(...),
    output_description: str = Form(...),
    constraints: str = Form(""),
    time_limit: str = Form(...),
    memory_limit: str = Form(...),
    difficulty: str = Form(...),
    tags: str = Form(""),
    score_mode: str = Form(...),
    sample_input: str = Form(...),
    sample_output: str = Form(...),
    test_case_id: list[str] = Form(...),
    test_input: list[str] = Form(...),
    test_output: list[str] = Form(...),
    test_score: list[str] = Form(...),
    test_hidden: list[str] = Form(...),
):
    """
    validate and replace editable problem data
    """

    current_user, redirect = require_web_role(
        request,
        "teacher",
        "admin",
    )

    if redirect is not None:
        return redirect

    form_data = raw_problem_form(
        problem_id,
        title,
        description,
        input_description,
        output_description,
        constraints,
        time_limit,
        memory_limit,
        difficulty,
        tags,
        score_mode,
        sample_input,
        sample_output,
        test_case_id,
        test_input,
        test_output,
        test_score,
        test_hidden,
    )

    try:
        problem = build_problem_model(
            form_data,
            include_id=False,
        )
        update_existing_problem(problem_id, problem)
    except LookupError as error:
        return render_page(
            request,
            "message.html",
            {
                "title": "problem not found",
                "heading": "problem not found",
                "message": str(error),
            },
            status_code=404,
        )
    except (ValidationError, ValueError) as error:
        return render_page(
            request,
            "problem_form.html",
            {
                "title": "edit problem",
                "mode": "edit",
                "problem_id": problem_id,
                "form_data": form_data,
                "error": str(error),
                "current_user": current_user,
            },
            status_code=422,
        )

    set_flash(request, "problem updated", "success")

    return RedirectResponse(
        url=f"/web/problems/{problem_id}",
        status_code=303,
    )


@router.post("/web/problems/{problem_id}/delete")
async def delete_problem_action(
    request: Request,
    problem_id: str,
):
    """
    soft delete one problem from the html interface
    """

    _current_user, redirect = require_web_role(
        request,
        "teacher",
        "admin",
    )

    if redirect is not None:
        return redirect

    try:
        delete_existing_problem(problem_id)
        set_flash(request, "problem deleted", "success")
    except LookupError as error:
        set_flash(request, str(error), "error")

    return RedirectResponse(
        url="/web/problems",
        status_code=303,
    )


@router.get(
    "/web/problems/{problem_id}/submit",
    response_class=HTMLResponse,
)
async def submit_page(
    request: Request,
    problem_id: str,
):
    """
    display the source code submission form
    """

    current_user = get_web_user(request)

    if current_user is None:
        return login_redirect()

    problem = get_problem_detail(
        problem_id,
        include_tests=False,
    )

    if problem is None:
        return render_page(
            request,
            "message.html",
            {
                "title": "problem not found",
                "heading": "problem not found",
                "message": "problem not found",
            },
            status_code=404,
        )

    return render_page(
        request,
        "submit.html",
        {
            "title": "submit solution",
            "problem": problem,
            "source_code": "",
            "current_user": current_user,
        },
    )


@router.post(
    "/web/problems/{problem_id}/submit",
    response_class=HTMLResponse,
)
async def submit_action(
    request: Request,
    background_tasks: BackgroundTasks,
    problem_id: str,
    source_code: str = Form(...),
):
    """
    create a pending submission and schedule its judge task
    """

    current_user = get_web_user(request)

    if current_user is None:
        return login_redirect()

    problem = get_problem_detail(
        problem_id,
        include_tests=False,
    )

    if problem is None:
        return render_page(
            request,
            "message.html",
            {
                "title": "problem not found",
                "heading": "problem not found",
                "message": "problem not found",
            },
            status_code=404,
        )

    try:
        submission_data = SubmissionCreate(
            problem_id=problem_id,
            language="python",
            source_code=source_code,
        )
        created_submission = create_new_submission(
            user_id=current_user["id"],
            submission_data=submission_data,
        )
    except (LookupError, ValidationError, ValueError) as error:
        return render_page(
            request,
            "submit.html",
            {
                "title": "submit solution",
                "problem": problem,
                "source_code": source_code,
                "error": str(error),
                "current_user": current_user,
            },
            status_code=422,
        )

    background_tasks.add_task(
        process_submission,
        created_submission["submission_id"],
    )

    return RedirectResponse(
        url=(
            "/web/submissions/"
            f"{created_submission['submission_id']}"
        ),
        status_code=303,
    )


@router.get(
    "/web/problems/{problem_id}",
    response_class=HTMLResponse,
)
async def problem_page(
    request: Request,
    problem_id: str,
):
    """
    display one problem with role appropriate testcase data
    """

    current_user = get_web_user(request)

    if current_user is None:
        return login_redirect()

    include_tests = current_user["role"] in {
        "teacher",
        "admin",
    }
    problem = get_problem_detail(
        problem_id,
        include_tests=include_tests,
    )

    if problem is None:
        return render_page(
            request,
            "message.html",
            {
                "title": "problem not found",
                "heading": "problem not found",
                "message": "problem not found",
            },
            status_code=404,
        )

    return render_page(
        request,
        "problem.html",
        {
            "title": problem["title"],
            "problem": problem,
            "current_user": current_user,
        },
    )


@router.get("/web/submissions", response_class=HTMLResponse)
async def submissions_page(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    problem_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    result: str | None = Query(default=None),
):
    """
    display filtered submissions
    """

    current_user = get_web_user(request)

    if current_user is None:
        return login_redirect()

    try:
        selected_problem_id = (
            problem_id.strip()
            if problem_id and problem_id.strip()
            else None
        )
        selected_user_id = parse_optional_positive_int(
            user_id
        )

        if status not in {
            None,
            "",
            "pending",
            "running",
            "finished",
            "failed",
        }:
            raise ValueError("invalid status filter")

        if result not in {
            None,
            "",
            "AC",
            "WA",
            "RE",
            "TLE",
            "SE",
        }:
            raise ValueError("invalid result filter")

        data = get_submission_list(
            page=page,
            page_size=page_size,
            current_user=current_user,
            problem_id=selected_problem_id,
            requested_user_id=selected_user_id,
            status=status or None,
            result=result or None,
        )
        error = None

    except (ValueError, PermissionError) as caught_error:
        data = {
            "items": [],
            "page": 1,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
        }
        error = str(caught_error)

    return render_page(
        request,
        "submissions.html",
        {
            "title": "submissions",
            "data": data,
            "filters": {
                "problem_id": problem_id or "",
                "user_id": user_id or "",
                "status": status or "",
                "result": result or "",
            },
            "error": error,
            "current_user": current_user,
        },
        status_code=422 if error else 200,
    )


@router.get(
    "/web/submissions/{submission_id}",
    response_class=HTMLResponse,
)
async def submission_page(
    request: Request,
    submission_id: int,
):
    """
    display one submission and its role appropriate logs
    """

    current_user = get_web_user(request)

    if current_user is None:
        return login_redirect()

    try:
        submission = get_submission_detail(
            submission_id,
            current_user,
        )
        log_data = get_submission_logs(
            submission_id,
            current_user,
        )
    except LookupError as error:
        return render_page(
            request,
            "message.html",
            {
                "title": "submission not found",
                "heading": "submission not found",
                "message": str(error),
            },
            status_code=404,
        )
    except PermissionError as error:
        return render_page(
            request,
            "message.html",
            {
                "title": "access denied",
                "heading": "access denied",
                "message": str(error),
            },
            status_code=403,
        )

    return render_page(
        request,
        "submission.html",
        {
            "title": f"submission {submission_id}",
            "submission": submission,
            "logs": log_data["logs"],
            "refresh_page": submission["status"] in {
                "pending",
                "running",
            },
            "current_user": current_user,
        },
    )


@router.post("/web/submissions/{submission_id}/rejudge")
async def rejudge_action(
    request: Request,
    background_tasks: BackgroundTasks,
    submission_id: int,
):
    """
    reset and schedule one submission for rejudge
    """

    current_user, redirect = require_web_role(
        request,
        "teacher",
        "admin",
    )

    if redirect is not None:
        return redirect

    try:
        prepare_submission_rejudge(
            submission_id,
            current_user=current_user,
        )
        background_tasks.add_task(
            process_submission,
            submission_id,
        )
        set_flash(request, "rejudge started", "success")
    except (LookupError, ValueError) as error:
        set_flash(request, str(error), "error")

    return RedirectResponse(
        url=f"/web/submissions/{submission_id}",
        status_code=303,
    )


@router.get("/web/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """
    display account state and online presence to an administrator
    """

    current_user, redirect = require_web_role(
        request,
        "admin",
    )

    if redirect is not None:
        return redirect

    return render_page(
        request,
        "users.html",
        {
            "title": "users",
            "data": get_user_list(page, page_size),
            "current_user": current_user,
        },
    )


@router.post("/web/users/{user_id}/update")
async def user_update_action(
    request: Request,
    user_id: int,
    role: str = Form(...),
    is_active: str = Form(...),
):
    """
    update one account from the administrator page
    """

    current_user, redirect = require_web_role(
        request,
        "admin",
    )

    if redirect is not None:
        return redirect

    try:
        update_user_account(
            user_id=user_id,
            update_data=UserUpdate(
                role=UserRole(role),
                is_active=is_active == "1",
            ),
            current_user=current_user,
        )
        set_flash(request, "user updated", "success")
    except (LookupError, ValueError) as error:
        set_flash(request, str(error), "error")

    return RedirectResponse(
        url="/web/users",
        status_code=303,
    )
