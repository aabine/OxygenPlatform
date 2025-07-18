from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.modules.users.service import UserService
from app.modules.users.schemas import User, Token, UserLogin
from app.modules.auth.deps import authenticate_user, create_access_token
from app.core.config import settings
from app.core.security import get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
) -> Token:
    user_service = UserService(db)
    user = await authenticate_user(user_data.email, user_data.password, user_service)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await user_service.update(user.id, {"last_login": user.last_login})
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token)

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:
    """OAuth2 compatible token login, get an access token for future requests"""
    user_service = UserService(db)
    user = await authenticate_user(form_data.username, form_data.password, user_service)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await user_service.update(user.id, {"last_login": user.last_login})
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token)

@router.post("/test-token", response_model=User)
async def test_token(current_user: User = Depends(get_current_active_user)) -> User:
    """Test access token"""
    return current_user
