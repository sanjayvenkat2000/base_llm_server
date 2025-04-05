# auth_providers.py
import os
from enum import Enum
from typing import Optional

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import Request

# from starlette.config import Config
from starlette.responses import HTMLResponse, RedirectResponse

# config = Config(".env")
oauth = OAuth()


class AuthProviderEnum(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    TWITTER = "twitter"


class AuthProvider:
    def __init__(
        self,
        name,
        client_id,
        client_secret,
        authorize_url,
        access_token_url,
        api_base_url,
        client_kwargs,
        jwks_uri=None,
        request_token_url=None,
    ):
        self.name = name
        oauth.register(
            name=name,
            client_id=client_id,
            client_secret=client_secret,
            access_token_url=access_token_url,
            authorize_url=authorize_url,
            api_base_url=api_base_url,
            client_kwargs=client_kwargs,
            jwks_uri=jwks_uri,
            request_token_url=request_token_url,
        )
        self.oauth_client = getattr(oauth, name)

    async def login(self, request: Request):
        provider_name = self.name.value if hasattr(self.name, "value") else self.name
        redirect_uri = str(request.url_for("auth_callback", provider=provider_name))
        return await self.oauth_client.authorize_redirect(request, redirect_uri)

    async def auth(self, request: Request):
        try:
            token = await self.oauth_client.authorize_access_token(request)
        except OAuthError as error:
            return HTMLResponse(f"<h1>{error.error}</h1>")
        user = token.get("userinfo") or token.get("user")
        if user:
            request.session["user"] = dict(user)
            redirect_url = request.session.pop("redirect_after_login", "/")
            return RedirectResponse(url=redirect_url)
        return RedirectResponse(url="/")


google_provider = AuthProvider(
    name=AuthProviderEnum.GOOGLE,
    client_id=os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_SECRET"),
    access_token_url="https://oauth2.googleapis.com/token",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    api_base_url="https://www.googleapis.com/",
    client_kwargs={"scope": "openid email profile"},
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
)

github_provider = AuthProvider(
    name=AuthProviderEnum.GITHUB,
    client_id=os.environ.get("SOCIAL_AUTH_GITHUB_CLIENT_ID"),
    client_secret=os.environ.get("SOCIAL_AUTH_GITHUB_CLIENT_SECRET"),
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)

twitter_provider = AuthProvider(
    name=AuthProviderEnum.TWITTER,
    client_id=os.environ.get("SOCIAL_AUTH_TWITTER_CLIENT_ID"),
    client_secret=os.environ.get("SOCIAL_AUTH_TWITTER_CLIENT_SECRET"),
    request_token_url="https://api.twitter.com/oauth/request_token",
    access_token_url="https://api.twitter.com/oauth/access_token",
    authorize_url="https://api.twitter.com/oauth/authorize",
    api_base_url="https://api.twitter.com/1.1/",
    client_kwargs={"scope": "users.read tweets.read"},
)


def get_auth_provider(provider_name: str) -> Optional[AuthProvider]:
    if provider_name == AuthProviderEnum.GOOGLE:
        return google_provider
    elif provider_name == AuthProviderEnum.GITHUB:
        return github_provider
    elif provider_name == AuthProviderEnum.TWITTER:
        return twitter_provider
    else:
        return None


def auth_provider_callback(request: Request, provider: str):
    return f"/auth/{provider}"
