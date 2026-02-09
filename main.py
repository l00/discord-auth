from fastapi import FastAPI, HTTPException, Response, Request, Depends
from fastapi.responses import RedirectResponse
import dotenv
import requests
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from database_models import User
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from secrets import token_hex
from fastapi.middleware.cors import CORSMiddleware
from hashlib import sha256

dotenv.load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"], # Set allow_origins to domains that should be able to view access and refresh tokens
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data):
    now = datetime.now(timezone.utc)
    to_encode={
        "sub": data,
        "iat": now,
        "exp": now + timedelta(minutes=15)
    }

    return jwt.encode(to_encode, os.getenv("JWT_SECRET_KEY"), algorithm="HS256")

@app.post("/auth/refresh")
async def refresh_token(request: Request):
    db: Session = SessionLocal()
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user = db.query(User).filter(User.refresh_token == sha256(refresh_token.encode('utf-8'), usedforsecurity=True).hexdigest()).first()

        if user:
            access_token = create_access_token(str(user.discord_id))
        else:
            raise HTTPException(status_code=404, detail="User not found")
    finally:
        db.close()

    redirect = RedirectResponse(
        url="http://127.0.0.1:5500/", # Set url to the page user should be redirected to after authenticating
        status_code=302
    )

    redirect.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=900
    )

    return redirect

@app.get("/auth")
async def discord_register(code: str = None, response: Response = None):
    if not code:
        raise HTTPException(status_code=400, detail="Code is required")
    
    data = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://127.0.0.1:8000/auth" # Set the value to redirect URI you added in Discord Dev Portal
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "application/x-www-form-urlencoded"
    }
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail="Error fetching token/invalid code provided")

    token_response = r.json()

    headers = {
        "Authorization": f"Bearer {token_response['access_token']}"
    }
    r = requests.get("https://discord.com/api/users/@me", headers=headers)

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail="Error fetching user info")
    
    user_info = r.json()

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.discord_id == user_info["id"]).first()

        refresh_token = token_hex(32)
        if not user:
            user = User(
                discord_id=user_info["id"],
                username=user_info["username"],
                email=user_info["email"],
                refresh_token = sha256(refresh_token.encode('utf-8'), usedforsecurity=True).hexdigest(),
                avatar=user_info["avatar"]
            )
            db.add(user)
        else:
            user.discord_id = user_info["id"]
            user.username = user_info["username"]
            user.email = user_info["email"]
            user.refresh_token = sha256(refresh_token.encode('utf-8'), usedforsecurity=True).hexdigest()
            user.avatar = user_info["avatar"]

        db.commit()
        db.refresh(user)

    finally:
        db.close()

    access_token = create_access_token(user.discord_id)

    redirect = RedirectResponse(
        url="http://127.0.0.1:5500/", # Set url to the page user should be redirected to after authenticating
        status_code=302
    )

    redirect.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True, # Set to False for local HTTP
        samesite="lax",
        max_age=900
    )

    redirect.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True, # Set to False for local HTTP
        samesite="lax",
        max_age=604800
    )

    return redirect

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms="HS256")
        discord_id = payload.get("sub")
        if not discord_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.discord_id == discord_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Invalid user")
    
    return user

@app.get("/users/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "discord_id": user.discord_id,
        "username": user.username,
        "email": user.email,
        "avatar": user.avatar
    }