from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from .service import *
from .repository import UserRepository


userRouter = APIRouter()
repo = UserRepository()
service = UserService(repo)


@userRouter.post("/reg")
async def register(user: CreateUser): #type: ignore
    return await service.register(user)


@userRouter.post('/login', summary='Login')
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await service.login(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    response = JSONResponse({
        "access_token": user["access_token"],
        "token_type": "bearer"
    })

    response.set_cookie(
        key="access_token",
        value=f"Bearer {user['access_token']}",
        httponly=True
    )

    return response


@userRouter.get('/me', response_model=GetUser)
async def get_user(user: GetUser = Depends(get_current_user)): # type: ignore
    return user
    