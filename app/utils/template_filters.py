from datetime import datetime

def format_datetime(value, format='%Y-%m-%d %I:%M %p'):
    """Format a datetime object to a string."""
    if value is None:
        return ""
    return value.strftime(format)

def format_date(value, format='%B %d, %Y'):
    """Format a datetime object to a date string."""
    if value is None:
        return ""
    return value.strftime(format)

def register_template_filters(app):
    """Register custom filters with the Flask app."""
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['format_date'] = format_date
