from app.core.config import settings
from app.model.user import User


def is_admin_user(user: User) -> bool:
    return user.id == 1 or user.username.lower() == settings.admin_username.lower()
