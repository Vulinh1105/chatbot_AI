from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from app.repository.user_repository import UserRepository
from app.model.user import User
from app.schemas.user import UserCreate, TokenResponse, LoginJSONRequest
from app.core.security import hash_password, verify_password, create_access_token, verify_access_token


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_current_user_by_token(self, token: str) -> User:
        """Validate a JWT access token and return its active user."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        user_id_str = verify_access_token(token)
        if user_id_str is None:
            raise credentials_exception

        try:
            user_id = int(user_id_str)
        except (TypeError, ValueError):
            raise credentials_exception

        user = await self.user_repo.get_by_id(user_id=user_id)
        if user is None:
            raise credentials_exception

        return user

    async def register(self, user_in: UserCreate) -> User:
        """Register a new user with username, email, and password."""
        # Check if username is already taken
        existing_username = await self.user_repo.get_by_username(user_in.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists.",
            )

        # Check if email is already taken
        existing_email = await self.user_repo.get_by_email(str(user_in.email))
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists.",
            )

        hashed_password = hash_password(user_in.password)
        return await self.user_repo.create(user_in=user_in, hashed_password=hashed_password)

    async def login(self, form_data: OAuth2PasswordRequestForm) -> TokenResponse:
        # Try finding by username first, then by email
        user = await self.user_repo.get_by_username(form_data.username)
        if not user:
            user = await self.user_repo.get_by_email(form_data.username)

        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect username/email or password",
            )

        access_token = create_access_token(data={"sub": str(user.id)})
        return TokenResponse(access_token=access_token, token_type="bearer")

    async def login_json(self, credentials: LoginJSONRequest) -> TokenResponse:
        user = await self.user_repo.get_by_username(credentials.username)
        if not user:
            user = await self.user_repo.get_by_email(credentials.username)

        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect username/email or password",
            )

        access_token = create_access_token(data={"sub": str(user.id)})
        return TokenResponse(access_token=access_token, token_type="bearer")
