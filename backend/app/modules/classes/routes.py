"""`/api/classes`: the Lecturer's Classes (Story 4.1, FR-5, FR-6, AD-12)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.classes import service
from app.modules.classes.schemas import (
    ClassIn,
    ClassListOut,
    ClassOut,
    InstitutionChoicesOut,
    InvalidClass,
)
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get(
    "",
    response_model=ClassListOut,
    responses=documented(401, 403),
    operation_id="listClasses",
)
async def list_classes(
    user: Annotated[authz.Principal, Depends(authz.require("classes.read"))],
) -> Response:
    """The Classes the User is staff of, by name: «Klassene dine» on the Lærerhjem."""
    return JSONResponse((await service.list_classes(user)).model_dump(mode="json"))


@router.post(
    "",
    status_code=201,
    response_model=ClassOut,
    responses=documented(401, 403, 422),
    operation_id="createClass",
)
async def create_class(
    body: ClassIn,
    user: Annotated[authz.Principal, Depends(authz.require("classes.create"))],
) -> Response:
    """Create a Class with the User as its owner (FR-6). A refused field answers 422
    `invalid_request` with every refused field in `fields`, and nothing is stored."""
    try:
        created = await service.create_class(user, body, now=auth.utcnow())
    except InvalidClass as error:
        return error_response(422, "invalid_request", "The Class is not valid.", error.fields)
    return JSONResponse(created.model_dump(mode="json"), status_code=201)


# Declared before `/{class_id}`, so the path is never read as a Class id.
@router.get(
    "/institutions",
    response_model=InstitutionChoicesOut,
    responses=documented(401, 403),
    operation_id="listClassInstitutions",
)
async def list_institutions(
    _: Annotated[authz.Principal, Depends(authz.require("classes.create"))],
) -> Response:
    """The Institutions a new Class may belong to, by name."""
    return JSONResponse((await service.institution_choices()).model_dump(mode="json"))


@router.get(
    "/{class_id}",
    response_model=ClassOut,
    responses=documented(401, 403),
    operation_id="getClass",
)
async def get_class(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("classes.read"))],
) -> Response:
    """One Class. A Class the User is not staff of, one that does not exist and an id that is not
    one all answer the same 403 `forbidden` (FR-5)."""
    try:
        parsed = uuid.UUID(class_id)
    except ValueError:
        raise authz.Forbidden from None
    found = await service.get_class(user, parsed)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))
