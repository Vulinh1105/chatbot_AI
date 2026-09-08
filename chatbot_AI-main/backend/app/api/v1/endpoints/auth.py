from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_service
from app.schemas.user import UserCreate, UserResponse, TokenResponse, LoginJSONRequest
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    return await auth_service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to obtain access token (Form-data for OAuth2 / Swagger UI)",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await auth_service.login(form_data)


@router.post(
    "/login/json",
    response_model=TokenResponse,
    summary="Login via JSON request body",
)
async def login_json(
    credentials: LoginJSONRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await auth_service.login_json(credentials)
