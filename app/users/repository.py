from app.models.users import User, GetUser, CreateUser


class UserRepository:
    async def create(self, user: CreateUser):  # type: ignore
        user_obj = User(name=user.name)
        user_obj.set_password(user.password_hash)
        await user_obj.save()
        return await GetUser.from_tortoise_orm(user_obj)

    async def create_admin(self, name: str, password: str) -> User:
        user = User(name=name)
        user.set_password(password)
        await user.save()
        return user

# обратная совместимость со старым именем
TortoiseRepository = UserRepository
