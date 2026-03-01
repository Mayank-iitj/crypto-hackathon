"""
Q-Shield OAuth Authentication Endpoints
Real-time OAuth integration with Google, GitHub, and Microsoft.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Optional

from app.core.oauth import oauth_service
from app.core.security import create_token_pair
from app.db.database import get_session
from app.models.models import User, UserRole
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

oauth_router = APIRouter(prefix="/auth", tags=["OAuth Authentication"])


@oauth_router.get("/providers")
async def get_oauth_providers():
    """Get list of available OAuth providers."""
    providers = oauth_service.get_available_providers()
    return {
        "providers": providers,
        "available": len(providers) > 0,
        "details": {
            "google": {
                "name": "Google",
                "icon": "google",
                "enabled": "google" in providers
            },
            "github": {
                "name": "GitHub",
                "icon": "github",
                "enabled": "github" in providers
            },
            "microsoft": {
                "name": "Microsoft",
                "icon": "microsoft",
                "enabled": "microsoft" in providers
            }
        }
    }


@oauth_router.get("/google/login")
async def google_login():
    """Initiate Google OAuth login flow."""
    try:
        provider = oauth_service.get_provider("google")
        state = oauth_service.generate_state("google")
        auth_url = provider.get_authorization_url(state)
        
        logger.info("Initiating Google OAuth login")
        return {"authorization_url": auth_url, "state": state}
    except Exception as e:
        logger.error(f"Google login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google login"
        )


@oauth_router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session)
):
    """Handle Google OAuth callback."""
    try:
        # Validate state
        if not oauth_service.validate_state(state, "google"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state token"
            )
        
        provider = oauth_service.get_provider("google")
        
        # Exchange code for token
        token_data = await provider.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )
        
        # Get user info
        user_info = await provider.get_user_info(access_token)
        
        # Find or create user
        user = await _find_or_create_oauth_user(
            session=session,
            provider="google",
            provider_id=user_info["provider_id"],
            email=user_info["email"],
            full_name=user_info["full_name"],
            avatar_url=user_info["avatar_url"],
            access_token=access_token,
            refresh_token=token_data.get("refresh_token")
        )
        
        # Generate JWT tokens
        tokens = create_token_pair(
            user_id=str(user.uuid),
            roles=[user.role.value],
            permissions=user.permissions or []
        )
        
        logger.info(f"Google OAuth successful for user: {user.email}")
        
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
            "user": {
                "id": str(user.uuid),
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "role": user.role.value
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google callback error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed"
        )


@oauth_router.get("/github/login")
async def github_login():
    """Initiate GitHub OAuth login flow."""
    try:
        provider = oauth_service.get_provider("github")
        state = oauth_service.generate_state("github")
        auth_url = provider.get_authorization_url(state)
        
        logger.info("Initiating GitHub OAuth login")
        return {"authorization_url": auth_url, "state": state}
    except Exception as e:
        logger.error(f"GitHub login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate GitHub login"
        )


@oauth_router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session)
):
    """Handle GitHub OAuth callback."""
    try:
        # Validate state
        if not oauth_service.validate_state(state, "github"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state token"
            )
        
        provider = oauth_service.get_provider("github")
        
        # Exchange code for token
        token_data = await provider.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )
        
        # Get user info
        user_info = await provider.get_user_info(access_token)
        
        # Find or create user
        user = await _find_or_create_oauth_user(
            session=session,
            provider="github",
            provider_id=user_info["provider_id"],
            email=user_info["email"],
            full_name=user_info["full_name"],
            avatar_url=user_info["avatar_url"],
            access_token=access_token,
            refresh_token=token_data.get("refresh_token")
        )
        
        # Generate JWT tokens
        tokens = create_token_pair(
            user_id=str(user.uuid),
            roles=[user.role.value],
            permissions=user.permissions or []
        )
        
        logger.info(f"GitHub OAuth successful for user: {user.email}")
        
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
            "user": {
                "id": str(user.uuid),
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "role": user.role.value
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub callback error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed"
        )


@oauth_router.get("/microsoft/login")
async def microsoft_login():
    """Initiate Microsoft OAuth login flow."""
    try:
        provider = oauth_service.get_provider("microsoft")
        state = oauth_service.generate_state("microsoft")
        auth_url = provider.get_authorization_url(state)
        
        logger.info("Initiating Microsoft OAuth login")
        return {"authorization_url": auth_url, "state": state}
    except Exception as e:
        logger.error(f"Microsoft login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Microsoft login"
        )


@oauth_router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session)
):
    """Handle Microsoft OAuth callback."""
    try:
        # Validate state
        if not oauth_service.validate_state(state, "microsoft"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state token"
            )
        
        provider = oauth_service.get_provider("microsoft")
        
        # Exchange code for token
        token_data = await provider.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )
        
        # Get user info
        user_info = await provider.get_user_info(access_token)
        
        # Find or create user
        user = await _find_or_create_oauth_user(
            session=session,
            provider="microsoft",
            provider_id=user_info["provider_id"],
            email=user_info["email"],
            full_name=user_info["full_name"],
            avatar_url=user_info["avatar_url"],
            access_token=access_token,
            refresh_token=token_data.get("refresh_token")
        )
        
        # Generate JWT tokens
        tokens = create_token_pair(
            user_id=str(user.uuid),
            roles=[user.role.value],
            permissions=user.permissions or []
        )
        
        logger.info(f"Microsoft OAuth successful for user: {user.email}")
        
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
            "user": {
                "id": str(user.uuid),
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "role": user.role.value
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Microsoft callback error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed"
        )


async def _find_or_create_oauth_user(
    session: AsyncSession,
    provider: str,
    provider_id: str,
    email: str,
    full_name: Optional[str],
    avatar_url: Optional[str],
    access_token: str,
    refresh_token: Optional[str]
) -> User:
    """Find existing OAuth user or create new one."""
    
    # Try to find user by OAuth provider ID
    query = select(User).where(
        User.oauth_provider == provider,
        User.oauth_provider_id == provider_id
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Update existing user's OAuth tokens
        user.oauth_access_token = access_token
        user.oauth_refresh_token = refresh_token
        user.last_login = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Updated existing OAuth user: {email}")
        return user
    
    # Try to find user by email (for linking existing accounts)
    query = select(User).where(User.email == email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Link OAuth to existing account
        user.oauth_provider = provider
        user.oauth_provider_id = provider_id
        user.oauth_access_token = access_token
        user.oauth_refresh_token = refresh_token
        user.last_login = datetime.now(timezone.utc)
        if avatar_url:
            user.avatar_url = avatar_url
        await session.commit()
        await session.refresh(user)
        logger.info(f"Linked OAuth to existing user: {email}")
        return user
    
    # Create new user
    if not settings.OAUTH_ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OAuth registration is disabled"
        )
    
    new_user = User(
        email=email,
        full_name=full_name,
        oauth_provider=provider,
        oauth_provider_id=provider_id,
        oauth_access_token=access_token,
        oauth_refresh_token=refresh_token,
        avatar_url=avatar_url,
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=True,  # OAuth users are pre-verified
        password_hash=None  # No password for OAuth users
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    logger.info(f"Created new OAuth user: {email} via {provider}")
    return new_user


__all__ = ["oauth_router"]
