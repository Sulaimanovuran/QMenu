from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from config.settings import SECRET_KEY
import jwt

from .repository import UserRepository
from app.models.users import User, GetUser, CreateUser


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/user/login')


async def authenticate_user(username: str, password: str):
    user = await User.get(name=username)
    if not user:
        return False 
    if not user.verify_password(password):
        return False
    return user 


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    user = await User.filter(id=payload.get('id')).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",)
    
    return await GetUser.from_tortoise_orm(user)


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
        
    async def register(self, user: CreateUser): #type: ignore
        return await self.repo.create(user)
    
    async def create_admin(self):
        if await User.get_or_none(name="admin"):
            return
        await self.repo.create_admin(
            name="admin",
            password="admin"
        )
    
    async def login(self, username: str, password: str):
        user = await authenticate_user(username, password)
        if not user:
            return None

        token_payload = {"id": user.id}

        token = jwt.encode(token_payload,
                           SECRET_KEY,
                           algorithm="HS256")

        return {
            "access_token": token,
            "user_id": user.id
        }
    
