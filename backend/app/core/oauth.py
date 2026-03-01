"""
Q-Shield OAuth Authentication Service
Real-time OAuth integration with Google, GitHub, and Microsoft.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OAuthProvider:
    """Base OAuth provider class."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorize_url: str,
        token_url: str,
        userinfo_url: str,
        scopes: list[str]
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url
        self.scopes = scopes
    
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
        }
        return f"{self.authorize_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={"Accept": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Token exchange failed: {e.response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code"
                )
            except Exception as e:
                logger.error(f"Token exchange error: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OAuth authentication failed"
                )
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Fetch user information from provider."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.userinfo_url,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to fetch user info: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch user information"
                )


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth provider."""
    
    def __init__(self):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth credentials not configured")
        
        super().__init__(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
            scopes=["openid", "email", "profile"]
        )
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Google user information."""
        user_info = await super().get_user_info(access_token)
        
        return {
            "provider_id": user_info.get("id"),
            "email": user_info.get("email"),
            "full_name": user_info.get("name"),
            "avatar_url": user_info.get("picture"),
            "email_verified": user_info.get("verified_email", False)
        }


class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth provider."""
    
    def __init__(self):
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            raise ValueError("GitHub OAuth credentials not configured")
        
        super().__init__(
            client_id=settings.GITHUB_CLIENT_ID,
            client_secret=settings.GITHUB_CLIENT_SECRET,
            redirect_uri=settings.GITHUB_REDIRECT_URI,
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scopes=["read:user", "user:email"]
        )
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get GitHub user information."""
        user_info = await super().get_user_info(access_token)
        
        # GitHub might not return primary email in user endpoint, fetch separately if needed
        email = user_info.get("email")
        if not email:
            email = await self._get_primary_email(access_token)
        
        return {
            "provider_id": str(user_info.get("id")),
            "email": email,
            "full_name": user_info.get("name") or user_info.get("login"),
            "avatar_url": user_info.get("avatar_url"),
            "email_verified": True  # GitHub emails are verified
        }
    
    async def _get_primary_email(self, access_token: str) -> Optional[str]:
        """Fetch primary email from GitHub."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.github.com/user/emails",
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                emails = response.json()
                
                # Find primary verified email
                for email_data in emails:
                    if email_data.get("primary") and email_data.get("verified"):
                        return email_data.get("email")
                
                # Fallback to first verified email
                for email_data in emails:
                    if email_data.get("verified"):
                        return email_data.get("email")
                
                return None
            except Exception as e:
                logger.warning(f"Failed to fetch GitHub emails: {str(e)}")
                return None


class MicrosoftOAuthProvider(OAuthProvider):
    """Microsoft OAuth provider."""
    
    def __init__(self):
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            raise ValueError("Microsoft OAuth credentials not configured")
        
        tenant_id = settings.MICROSOFT_TENANT_ID
        
        super().__init__(
            client_id=settings.MICROSOFT_CLIENT_ID,
            client_secret=settings.MICROSOFT_CLIENT_SECRET,
            redirect_uri=settings.MICROSOFT_REDIRECT_URI,
            authorize_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            scopes=["openid", "email", "profile", "User.Read"]
        )
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Microsoft user information."""
        user_info = await super().get_user_info(access_token)
        
        return {
            "provider_id": user_info.get("id"),
            "email": user_info.get("mail") or user_info.get("userPrincipalName"),
            "full_name": user_info.get("displayName"),
            "avatar_url": None,  # Would need separate Graph API call
            "email_verified": True  # Microsoft accounts are verified
        }


class OAuthService:
    """Central OAuth service managing all providers."""
    
    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {}
        self._initialize_providers()
        self._state_store: Dict[str, Dict[str, Any]] = {}
    
    def _initialize_providers(self):
        """Initialize available OAuth providers."""
        try:
            if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
                self.providers["google"] = GoogleOAuthProvider()
                logger.info("Google OAuth provider initialized")
        except ValueError as e:
            logger.warning(f"Google OAuth not configured: {str(e)}")
        
        try:
            if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
                self.providers["github"] = GitHubOAuthProvider()
                logger.info("GitHub OAuth provider initialized")
        except ValueError as e:
            logger.warning(f"GitHub OAuth not configured: {str(e)}")
        
        try:
            if settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET:
                self.providers["microsoft"] = MicrosoftOAuthProvider()
                logger.info("Microsoft OAuth provider initialized")
        except ValueError as e:
            logger.warning(f"Microsoft OAuth not configured: {str(e)}")
        
        if not self.providers:
            logger.warning("No OAuth providers configured")
    
    def get_provider(self, provider_name: str) -> OAuthProvider:
        """Get OAuth provider by name."""
        provider = self.providers.get(provider_name)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth provider '{provider_name}' not configured"
            )
        return provider
    
    def generate_state(self, provider: str) -> str:
        """Generate secure state token for OAuth flow."""
        state = secrets.token_urlsafe(32)
        self._state_store[state] = {
            "provider": provider,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(
                minutes=settings.OAUTH_STATE_EXPIRY_MINUTES
            )
        }
        return state
    
    def validate_state(self, state: str, expected_provider: str) -> bool:
        """Validate OAuth state token."""
        state_data = self._state_store.get(state)
        
        if not state_data:
            logger.warning(f"Invalid OAuth state: {state[:10]}...")
            return False
        
        # Check expiry
        if datetime.now(timezone.utc) > state_data["expires_at"]:
            logger.warning(f"Expired OAuth state: {state[:10]}...")
            del self._state_store[state]
            return False
        
        # Check provider matches
        if state_data["provider"] != expected_provider:
            logger.warning(f"Provider mismatch for state: {state[:10]}...")
            return False
        
        # Clean up used state
        del self._state_store[state]
        return True
    
    def get_available_providers(self) -> list[str]:
        """Get list of available OAuth providers."""
        return list(self.providers.keys())


# Global OAuth service instance
oauth_service = OAuthService()
