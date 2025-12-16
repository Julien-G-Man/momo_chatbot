from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from auth import get_password_hash, verify_password, create_access_token, authenticate_user
import models, schemas

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post("/signup", response_model=schemas.Token)
def signup_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(models.User).filter(
        (models.User.email == user_data.email) | (models.User.username == user_data.username)
    ).first()
    
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    # Hash the password and create the new user
    hashed_password = get_password_hash(user_data.password)
    new_user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create and return an access token for automatic login
    access_token = create_access_token(data={"sub": new_user.username})
    return schemas.Token(access_token=access_token)

@auth_router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Look up user by username (form_data.username)
    db_user = authenticate_user(db, form_data.username)
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Add bypass for the GUEST account placeholder hash
    if db_user.username == "Guest" and db_user.hashed_password == "GUEST_PLACEHOLDER_HASH_DO_NOT_USE_FOR_LOGIN":
        # The Guest account should never be logged into.
        # We deny access here to prevent accidental login and token generation.
        # This forces users to sign up or use real credentials.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest account cannot be used for direct login. Please sign up or use real credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # CRITICAL: HASH VERIFICATION 
    if not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If verification passes, create the token
    access_token = create_access_token(
        data={"sub": db_user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}