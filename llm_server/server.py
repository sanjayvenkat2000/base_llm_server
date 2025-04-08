from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_server.auth_provider import get_current_user, verify_clerk_token

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
    ],  # Allow localhost origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)


# Public route (no authentication required)
@app.get("/public")
async def public_endpoint():
    return {"message": "This is a public endpoint"}


# Protected route (requires valid JWT)
@app.get("/protected")
async def protected_endpoint(token_data: Annotated[dict, Depends(verify_clerk_token)]):
    return {"message": f"Welcome, user {token_data['user_id']}!"}


# Protected route with user data
@app.get("/user")
async def user_endpoint(current_user: Annotated[dict, Depends(get_current_user)]):
    return {"message": f"User ID: {current_user['id']}"}


# Another protected route example
@app.post("/protected-action")
async def protected_action(current_user: Annotated[dict, Depends(get_current_user)]):
    return {"message": f"Action performed by user {current_user['user_id']}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
