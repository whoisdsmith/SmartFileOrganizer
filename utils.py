import os
import re
import math

def get_readable_size(size_bytes):
    """
    Convert size in bytes to human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human readable size string
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def sanitize_filename(filename):
    """
    Make a string safe to use as a filename
    
    Args:
        filename: String to sanitize
        
    Returns:
        Sanitized string
    """
    # Replace problematic characters with underscore
    s = re.sub(r'[\\/*?:"<>|]', '_', filename)
    
    # Remove leading/trailing whitespace
    s = s.strip()
    
    # Replace multiple underscores with single one
    s = re.sub(r'_+', '_', s)
    
    # Limit length
    max_length = 255
    if len(s) > max_length:
        s = s[:max_length]
    
    # Ensure not empty
    if not s:
        s = "unnamed"
    
    return s

def truncate_text(text, max_length=100, add_ellipsis=True):
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        add_ellipsis: Whether to add ellipsis
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length].rstrip()
    if add_ellipsis:
        truncated += "..."
    
    return truncated

def strip_html_tags(html_text):
    """
    Remove HTML tags from text
    
    Args:
        html_text: HTML text
        
    Returns:
        Text without HTML tags
    """
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html_text)

def is_file_locked(file_path):
    """
    Check if a file is locked (in use)
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file is locked, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    try:
        with open(file_path, 'r+') as f:
            return False
    except IOError:
        return True
