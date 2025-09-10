"""
IP Restrictions Middleware - Enforces organization IP whitelist settings
"""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.database import get_session
from ..services.organization_settings_service import OrganizationSettingsService

logger = logging.getLogger(__name__)


class IPRestrictionsMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce IP restrictions based on organization settings"""
    
    def __init__(self, app, excluded_paths: list[str] = None):
        super().__init__(app)
        # Paths that don't require IP checking (like health check, public endpoints)
        self.excluded_paths = excluded_paths or [
            "/api/health",
            "/api/docs",
            "/api/redoc",
            "/api/auth/register",
            "/api/auth/verify-email",
            "/api/auth/forgot-password",
            "/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip IP checking for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Skip IP checking for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Get client IP (handle proxy headers)
            client_ip = self.get_client_ip(request)
            
            # Check if request requires authentication
            auth_header = request.headers.get("authorization")
            if not auth_header:
                # No auth required, skip IP check
                return await call_next(request)
            
            # Extract user from token and check IP restrictions
            if await self.check_ip_restrictions(request, client_ip):
                return await call_next(request)
            else:
                logger.warning(f"IP {client_ip} blocked for request to {request.url.path}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Access denied: IP address not allowed by organization policy",
                        "client_ip": client_ip
                    }
                )
        
        except Exception as e:
            logger.error(f"IP Restrictions Middleware error: {e}")
            # On error, allow request to proceed (fail open)
            return await call_next(request)
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxy headers"""
        # Check for common proxy headers in order of preference
        ip_headers = [
            "x-forwarded-for",
            "x-real-ip", 
            "cf-connecting-ip",  # Cloudflare
            "x-client-ip",
            "x-cluster-client-ip"
        ]
        
        for header in ip_headers:
            if header in request.headers:
                ip = request.headers[header].split(",")[0].strip()
                if ip and ip != "unknown":
                    return ip
        
        # Fallback to request client
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    async def check_ip_restrictions(self, request: Request, client_ip: str) -> bool:
        """Check if client IP is allowed based on user's organization settings"""
        try:
            # Get database session
            with next(get_session()) as db:
                # Extract and decode JWT token to get user ID
                auth_header = request.headers.get("authorization", "")
                if not auth_header.startswith("Bearer "):
                    return True  # No valid token, let other middleware handle
                
                token = auth_header.split(" ")[1]
                
                # Decode token to get user ID (simplified)
                from jose import JWTError, jwt

                from ..core.config import get_settings
                
                settings = get_settings()
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    user_id = payload.get("sub")
                    if not user_id:
                        return True  # Invalid token, let auth middleware handle
                    
                    # Check IP restrictions using our service
                    return OrganizationSettingsService.is_ip_allowed(db, user_id, client_ip)
                    
                except JWTError:
                    return True  # Invalid token, let auth middleware handle
                
        except Exception as e:
            logger.error(f"Error checking IP restrictions: {e}")
            return True  # Fail open on error
