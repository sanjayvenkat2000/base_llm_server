import os
from typing import Annotated

import jwt
import requests
from async_lru import alru_cache
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

load_dotenv()


# Clerk configuration
CLERK_SECRET_KEY = os.environ.get("CLERK_SECRET_KEY", None)
if CLERK_SECRET_KEY is None:
    raise Exception("Need to set clerk secret key")

CLERK_API_URL = "https://api.clerk.com/v1"
CLERK_JWKS_URL = "https://api.clerk.dev/v1/jwks"  # URL to fetch Clerk's public keys

# OAuth2 scheme to extract the token from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # "token" is a dummy value here


# Dependency to verify JWT and return user data
async def verify_clerk_token(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        # For development/testing, you can bypass verification with a simple decode
        # In production, you should verify with the proper JWKS approach
        payload = jwt.decode(token, options={"verify_signature": False})

        # TODO: For production, implement proper JWKS verification:
        # 1. Fetch JWKS from https://api.clerk.dev/v1/jwks
        # 2. Find the right key using the 'kid' from the token header
        # 3. Verify with the public key

        user_id = payload.get("sub")  # 'sub' contains the user ID in Clerk's JWT
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: No user ID found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"user_id": user_id, "payload": payload}
    except Exception as e:
        print(f"Error decoding token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@alru_cache(maxsize=100)
async def get_user_details(user_id: str):
    print(f"Fetching user details for {user_id}")
    headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
    response = requests.get(f"{CLERK_API_URL}/users/{user_id}", headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch user data")
    return response.json()


# Optional: Fetch additional user data from Clerk API
async def get_current_user(token_data: Annotated[dict, Depends(verify_clerk_token)]):
    user_id = token_data["user_id"]
    # You could fetch more user info from Clerk if needed
    return await get_user_details(user_id)
