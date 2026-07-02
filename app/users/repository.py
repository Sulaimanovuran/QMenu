from app.models.users import User, GetUser, CreateUser


class UserRepository:
    async def create(self, user: CreateUser):  # type: ignore
        user_obj = User(
            login=user.login,
            full_name=user.full_name,
            phone=user.phone,
            is_active=user.is_active,
        )
        user_obj.set_password(user.password_hash)
        await user_obj.save()
        return await GetUser.from_tortoise_orm(user_obj)

    async def create_admin(self, login: str, full_name: str, password: str) -> User:
        user = User(login=login, full_name=full_name, is_superadmin=True)
        user.set_password(password)
        await user.save()
        return user

# обратная совместимость со старым именем
TortoiseRepository = UserRepository
