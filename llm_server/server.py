import asyncio
import json
import os
import random
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, RedirectResponse, StreamingResponse

# Import the auth providers
from llm_server.auth_provider import AuthProviderEnum, get_auth_provider

# Global variable for HTML content
chat_test_html = ""

# Load environment variables from .env file
load_dotenv()

if os.getenv("SOCIAL_AUTH_GOOGLE_CLIENT_SECRET") is None:
    raise ValueError("SOCIAL_AUTH_GOOGLE_CLIENT_SECRET is not set")
if os.getenv("SOCIAL_AUTH_GOOGLE_CLIENT_ID") is None:
    raise ValueError("SOCIAL_AUTH_GOOGLE_CLIENT_ID is not set")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup code that runs before application startup
    global chat_test_html
    template_path = os.path.join(
        os.path.dirname(__file__), "templates", "chat_test.html"
    )
    with open(template_path, "r") as f:
        chat_test_html = f.read()

    yield
    # Cleanup code would go here (runs on shutdown)


app = FastAPI(lifespan=lifespan)


# Middleware to protect routes
@app.middleware("http")
async def protected_routes(request: Request, call_next):
    if request.url.path.startswith("/protected"):
        user = userProvider(request)
        if not user:
            request.session["redirect_after_login"] = str(request.url)
            return RedirectResponse(url="/login_page")
    response = await call_next(request)
    return response


app.add_middleware(SessionMiddleware, secret_key="!secret")


# Dependency function to get user info from session
def userProvider(request: Request) -> Optional[dict]:
    return request.session.get("user")


@app.get("/login/{login_provider}")
async def login(request: Request):
    login_provider = request.path_params["login_provider"]

    match login_provider:
        case "google":
            provider = get_auth_provider(AuthProviderEnum.GOOGLE)
        case "github":
            provider = get_auth_provider(AuthProviderEnum.GITHUB)
        case "twitter":
            provider = get_auth_provider(AuthProviderEnum.TWITTER)
        case _:
            raise HTTPException(status_code=404, detail="Provider not found")

    return await provider.login(request)  # type: ignore


@app.get("/auth/{provider}", name="auth_callback")
async def auth(request: Request):
    provider_name = request.path_params["provider"]

    match provider_name:
        case "google":
            provider = get_auth_provider(AuthProviderEnum.GOOGLE)
        case "github":
            provider = get_auth_provider(AuthProviderEnum.GITHUB)
        case "twitter":
            provider = get_auth_provider(AuthProviderEnum.TWITTER)
        case _:
            raise HTTPException(status_code=404, detail="Provider not found")

    return await provider.auth(request)  # type: ignore


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


# Model for chat messages
class ChatMessage(BaseModel):
    role: str
    content: str


######################
# Delete in real usecases - Testing route
######################
@app.get("/")
async def homepage(request: Request):
    user = request.session.get("user")
    if user:
        data = json.dumps(user)
        html = f'<pre>{data}</pre><a href="/logout">logout</a>'
        return HTMLResponse(html)
    return HTMLResponse('<a href="/login_page">login</a>')


######################
# Delete in real usecases - Testing route
######################
@app.get("/login_page")
async def login_page(request: Request):
    html = """
    <div>
        <a href="/login/google">Login with Google</a><br>
        <a href="/login/github">Login with GitHub</a><br>
        <a href="/login/twitter">Login with Twitter</a>
    </div>
    """
    return HTMLResponse(html)


######################
# Delete in real usecases - Testing route
######################
# Protected route using dependency
@app.get("/protected/chat_test")
async def chat_test(request: Request, user: Optional[dict] = Depends(userProvider)):
    return HTMLResponse(chat_test_html)


######################
# Delete in real usecases - Testing route
######################
@app.post("/protected/api/chat")
async def chat_completion(
    chat_request: list[ChatMessage],
    user: Optional[dict] = Depends(userProvider),
):
    async def event_generator():
        try:
            # Get the last message from the chat request
            last_message = chat_request[-1].content

            # Determine how many times to repeat the message (25-30 times)
            repeat_count = random.randint(25, 30)

            # Create the repeated content with spaces in between
            repeated_content = (
                " ".join([last_message] * repeat_count)
                + " "
                + str(repeat_count)
                + " times: "
                + "I just repeated this message "
            )

            # Split into words to stream at 10 words per minute
            words = repeated_content.split()

            # Stream each word with appropriate delay (6 seconds per word for ~10 words/minute)
            for word in words:
                yield f"data: {json.dumps({'content': word + ' '})}\n\n"
                await asyncio.sleep(0.075)  # 6 seconds delay for ~10 words per minute

            # Send done message when complete
            yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
