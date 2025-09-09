from datetime import datetime, timezone
from typing import Optional


def ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is timezone-aware (UTC if naive).
    
    Args:
        dt: Datetime that might be timezone-naive or timezone-aware
        
    Returns:
        Timezone-aware datetime or None if input is None
    """
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
