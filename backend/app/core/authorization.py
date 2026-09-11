from app.core.config import settings
from app.model.user import User


def is_admin_user(user: User) -> bool:
    """Return whether the user has the application's administrator privileges."""
    return user.id == 1 or user.username.lower() == settings.admin_username.lower()
