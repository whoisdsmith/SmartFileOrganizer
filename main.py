import os
import sys
import tkinter as tk
import logging
import ctypes
from pathlib import Path

# Add src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from gui import DocumentOrganizerApp

def setup_logging():
    """Set up logging for the application"""
    try:
        # Windows-specific logging directory
        if os.name == 'nt':  # Windows
            log_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "AIDocumentOrganizer")
        else:  # macOS/Linux
            log_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "AIDocumentOrganizer")
        
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
    except Exception:
        # Fallback to current directory if there's an issue
        log_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(log_dir, "app.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("AIDocumentOrganizer")

def is_windows_admin():
    """Check if the application is running with admin privileges (Windows specific)"""
    if os.name == 'nt':  # Only check on Windows
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            pass
    return False

def main():
    """
    Main entry point for the Document Organizer application.
    Initializes and starts the GUI application.
    """
    # Setup logging
    logger = setup_logging()
    logger.info("Starting AI Document Organizer application")
    
    # Windows 10/11 DPI awareness (prevents blurry text)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        logger.info("DPI awareness set successfully")
    except:
        logger.warning("Could not set DPI awareness")
    
    # Create main window
    root = tk.Tk()
    root.title("AI Document Organizer - Powered by Google Gemini")
    
    # Set application icon (Windows specific)
    try:
        # Look for the icon in the application directory
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated-icon.png")
        if os.path.exists(icon_path):
            # For Windows, use the application icon if available
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
            logger.info(f"Set application icon from {icon_path}")
        else:
            # Use default icon
            root.iconbitmap(default='')
    except Exception as e:
        # Ignore if not on Windows
        logger.warning(f"Could not set application icon: {str(e)}")
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Set window size to 80% of screen size
    window_width = int(screen_width * 0.8)
    window_height = int(screen_height * 0.8)
    
    # Calculate position for the window to be centered
    x_position = (screen_width - window_width) // 2
    y_position = (screen_height - window_height) // 2
    
    # Set window size and position
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    
    # Set Windows-specific theme
    try:
        from tkinter import ttk
        style = ttk.Style()
        
        # Try to use Windows 10/11 native theme or fall back to vista/clam
        available_themes = style.theme_names()
        logger.info(f"Available themes: {available_themes}")
        
        if 'winnative' in available_themes:
            style.theme_use('winnative')
        elif 'vista' in available_themes:
            style.theme_use('vista')
        else:
            style.theme_use('clam')
            
        logger.info(f"Using theme: {style.theme_use()}")
    except Exception as e:
        logger.warning(f"Could not set theme: {str(e)}")
    
    # Initialize application
    app = DocumentOrganizerApp(root)
    
    # We don't need to manually configure the notebook layout
    # It's already handled in the GUI class using grid
    
    # Start the application main loop
    logger.info("Entering main application loop")
    root.mainloop()
    
    logger.info("Application closed")

if __name__ == "__main__":
    main()
