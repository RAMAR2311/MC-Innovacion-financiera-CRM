from datetime import datetime, timedelta, timezone

def get_colombia_now():
    """
    Returns the current time in Colombia (UTC-5).
    Useful for timestamps in logs and chat messages.
    Returns a naive datetime object (no timezone info) matching local time.
    """
    # Get current UTC time (aware)
    utc_now = datetime.now(timezone.utc)
    
    # Colombia is UTC-5
    colombia_offset = timedelta(hours=-5)
    
    # Calculate Colombia time
    colombia_time = utc_now + colombia_offset
    
    # Return naive datetime (stripping tzinfo) to be compatible with database columns
    # that expect naive datetimes (like the previous datetime.utcnow)
    return colombia_time.replace(tzinfo=None)
