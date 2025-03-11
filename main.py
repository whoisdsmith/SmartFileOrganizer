from src.gui import DocumentOrganizerApp
import os
import sys
import tkinter as tk
import logging
import ctypes
from pathlib import Path
import argparse

# Add src directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Version 2 imports
from ai_document_organizer_v2.core import PluginManager, SettingsManager
from ai_document_organizer_v2.compatibility import CompatibilityManager


def setup_logging(log_to_file_only=False):
    """Set up logging for the application"""
    try:
        # Windows-specific logging directory
        if os.name == 'nt':  # Windows
            log_dir = os.path.join(os.path.expanduser(
                "~"), "AppData", "Local", "AIDocumentOrganizer")
        else:  # macOS/Linux
            log_dir = os.path.join(os.path.expanduser(
                "~"), ".local", "share", "AIDocumentOrganizer")

        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
    except Exception:
        # Fallback to current directory if there's an issue
        log_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(log_dir, "app.log")

    # Configure handlers based on the log_to_file_only setting
    handlers = [logging.FileHandler(log_file)]

    # Add console handler only if not log_to_file_only
    if not log_to_file_only:
        # Use StreamHandler but cast it to avoid LSP type issues
        console_handler = logging.StreamHandler()
        handlers.append(console_handler)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    logger = logging.getLogger("AIDocumentOrganizer")
    logger.info(f"Logging initialized (log_to_file_only={log_to_file_only})")
    return logger


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
    # Check for command-line arguments
    parser = argparse.ArgumentParser(description='AI Document Organizer')
    parser.add_argument('--log-to-file-only', action='store_true',
                        help='Log to file only, not to console')
    parser.add_argument('--use-v2', action='store_true',
                        help='Use Version 2 plugin architecture (experimental)')
    parser.add_argument('--test-plugins', action='store_true',
                        help='Test V2 plugin system and exit')
    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(log_to_file_only=args.log_to_file_only)
    logger.info("Starting AI Document Organizer application")
    
    # Initialize variables to avoid "possibly unbound" issues
    plugin_manager = None
    settings_manager = None
    compat_manager = None
    
    # Initialize V2 plugin system if enabled
    if args.use_v2 or args.test_plugins:
        logger.info("Initializing V2 plugin architecture")
        try:
            # Initialize plugin system
            settings_manager = SettingsManager()
            plugin_manager = PluginManager(settings_manager=settings_manager)
            
            # Discover and initialize plugins
            discovery_results = plugin_manager.discover_plugins()
            logger.info(f"Discovered {discovery_results['found']} plugins, loaded {discovery_results['loaded']}")
            
            if discovery_results['failed'] > 0:
                logger.warning(f"Failed to load {discovery_results['failed']} plugins")
                
            # Initialize plugins
            init_results = plugin_manager.initialize_plugins()
            logger.info(f"Initialized {init_results['successful']} plugins")
            
            # Set up compatibility layer
            compat_manager = CompatibilityManager(plugin_manager, settings_manager)
            logger.info("V2 compatibility layer ready")
            
            # If just testing plugins, run the test and exit
            if args.test_plugins:
                # Import our test script
                import test_v2_plugins
                test_v2_plugins.main()
                return
        except Exception as e:
            logger.error(f"Error initializing V2 plugin system: {e}")
            logger.info("Falling back to V1 architecture")
            args.use_v2 = False

    # Windows 10/11 DPI awareness (prevents blurry text)
    if os.name == 'nt':  # Windows only
        try:
            if hasattr(ctypes, 'windll') and hasattr(ctypes.windll, 'shcore'):
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
                logger.info("DPI awareness set successfully")
            else:
                logger.warning("Windows DPI awareness API not available")
        except Exception as e:
            logger.warning(f"Could not set DPI awareness: {e}")
    else:
        logger.debug("DPI awareness setting skipped (non-Windows platform)")

    # Create main window
    root = tk.Tk()
    root.title("AI Document Organizer - Powered by Google Gemini")

    # Set application icon (Windows specific)
    try:
        # Look for the icon in the application directory
        icon_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "assets", "generated-icon.png")
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

    # Initialize application with V2 components if enabled
    if args.use_v2:
        try:
            # Pass V2 components to the app
            app = DocumentOrganizerApp(root, v2_components={
                'plugin_manager': plugin_manager,
                'settings_manager': settings_manager,
                'compat_manager': compat_manager,
                'use_v2': True
            })
            logger.info("Initialized application with V2 plugin architecture")
        except Exception as e:
            logger.error(f"Error initializing app with V2 components: {e}")
            logger.info("Falling back to V1 architecture")
            app = DocumentOrganizerApp(root)
    else:
        # Standard V1 initialization
        app = DocumentOrganizerApp(root)

    # Start the application main loop
    logger.info("Entering main application loop")
    root.mainloop()
    
    # Clean up V2 plugin system if used
    if args.use_v2 and plugin_manager is not None:
        try:
            # Shutdown plugins
            shutdown_results = plugin_manager.shutdown_plugins()
            logger.info(f"Shutdown {shutdown_results['successful']} plugins")
            if shutdown_results['failed'] > 0:
                logger.warning(f"Failed to shutdown {shutdown_results['failed']} plugins")
        except Exception as e:
            logger.error(f"Error shutting down plugin system: {e}")

    logger.info("Application closed")


if __name__ == "__main__":
    main()
