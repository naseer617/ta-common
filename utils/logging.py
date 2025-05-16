import logging
import functools
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_exceptions(func):
    """
    Decorator to log exceptions for route handlers.
    Logs all exceptions with their full details before re-raising them.
    Only handles database-related errors, lets HTTP exceptions pass through.

    Usage:
        @log_exceptions
        async def your_route_handler(session: AsyncSession = Depends(get_session)):
            # Your route logic here
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Find session in kwargs or args
        session = next((arg for arg in args if isinstance(arg, AsyncSession)), None)
        if not session:
            session = next((v for v in kwargs.values() if isinstance(v, AsyncSession)), None)

        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Let HTTP exceptions pass through without logging
            raise
        except IntegrityError as e:
            if session:
                await session.rollback()
            logger.error(f"IntegrityError in {func.__name__}: {str(e)}")
            error_msg = str(e).lower()
            if func.__name__ == "create_member":
                if "members_login_key" in error_msg:
                    raise HTTPException(status_code=400, detail="Login already exists")
                if "members_email_key" in error_msg:
                    raise HTTPException(status_code=400, detail="Email already exists")
                raise HTTPException(status_code=400, detail="Database error")
            else:
                raise HTTPException(status_code=400, detail="Database error")
        except SQLAlchemyError as e:
            if session:
                await session.rollback()
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            # Preserve original error messages based on function name
            if func.__name__ in ["get_members", "get_feedbacks"]:
                raise HTTPException(status_code=500, detail="Failed to fetch members" if func.__name__ == "get_members" else "Failed to fetch comments")
            elif func.__name__ in ["soft_delete_members", "soft_delete_feedbacks"]:
                raise HTTPException(status_code=500, detail="Failed to delete members" if func.__name__ == "soft_delete_members" else "Failed to delete comments")
            elif func.__name__ in ["soft_delete_member", "soft_delete_feedback"]:
                raise HTTPException(status_code=500, detail="Failed to delete member" if func.__name__ == "soft_delete_member" else "Failed to delete comment")
            elif func.__name__ in ["create_member", "create_feedback"]:
                raise HTTPException(status_code=500, detail="Failed to create member" if func.__name__ == "create_member" else "Failed to create comment")
            else:
                raise HTTPException(status_code=500, detail="Database error")
        except Exception as e:
            if session:
                await session.rollback()
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            # Preserve original error messages based on function name
            if func.__name__ in ["get_members", "get_feedbacks"]:
                raise HTTPException(status_code=500, detail="Failed to fetch members" if func.__name__ == "get_members" else "Failed to fetch comments")
            elif func.__name__ in ["soft_delete_members", "soft_delete_feedbacks"]:
                raise HTTPException(status_code=500, detail="Failed to delete members" if func.__name__ == "soft_delete_members" else "Failed to delete comments")
            elif func.__name__ in ["soft_delete_member", "soft_delete_feedback"]:
                raise HTTPException(status_code=500, detail="Failed to delete member" if func.__name__ == "soft_delete_member" else "Failed to delete comment")
            else:
                raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper
