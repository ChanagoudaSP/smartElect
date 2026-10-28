from datetime import datetime

def convert_to_24hr(time_str):
    """Convert 12-hour time format to 24-hour format."""
    try:
        # Parse the time string (e.g., "2:30 PM")
        time, period = time_str.split(' ')
        hour, minute = map(int, time.split(':'))
        
        # Convert to 24-hour format
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
            
        return f"{hour:02d}:{minute:02d}"
    except Exception as e:
        raise ValueError(f"Invalid time format: {time_str}. Error: {str(e)}")

def convert_to_12hr(datetime_obj):
    """Convert datetime object to 12-hour time format."""
    try:
        return datetime_obj.strftime("%I:%M %p").lstrip("0")
    except Exception as e:
        return "12:00 AM"  # Default value in case of error

def get_date_string(datetime_obj):
    """Get date string in YYYY-MM-DD format."""
    try:
        return datetime_obj.strftime("%Y-%m-%d")
    except Exception as e:
        return datetime.now().strftime("%Y-%m-%d")  # Default to today in case of error
