from datetime import datetime
from datetime import timedelta
from typing import Annotated

from fastapi import Header
from fastapi import HTTPException
from jose import jwt
from jose import JWTError

X_TOKEN = "ThisIsATestToken"


# Secret key for JWT encoding and decoding
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(days=1000)  # Set expiration to 2 days if not specified
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_token(x_token: Annotated[str, Header()]):
    try:
        jwt.decode(x_token, SECRET_KEY, algorithms=[ALGORITHM])

        # email = payload.get('email')
        # Optionally, check if the email is in your database or if the user exists
        return True  # Token is valid
    except JWTError:
        raise HTTPException(status_code=400, detail="X-Token header invalid")


async def get_query_token(token: str):
    if token != X_TOKEN:
        raise HTTPException(status_code=400, detail="No token provided")
