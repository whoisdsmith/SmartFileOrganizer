import sys
import os
from cx_Freeze import setup, Executable

# Get the project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Dependencies
build_exe_options = {
    "packages": [
        "os",
        "sys",
        "tkinter",
        "logging",
        "threading",
        "queue",
        "time",
        "json",
        "google.generativeai",
        "openai",
        "pandas",
        "numpy",
        "chardet",
        "bs4",
        "docx",
        "openpyxl"
    ],
    "excludes": ["test", "unittest"],
    "include_files": [
        (os.path.join(project_root, "assets",
         "generated-icon.png"), "generated-icon.png"),
        (os.path.join(project_root, "docs"), "docs"),
    ],
    "include_msvcr": True,
}

# Base for GUI applications
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Create the executable
setup(
    name="AI Document Organizer",
    version="1.0.0",
    description="AI-powered document organization tool",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            os.path.join(project_root, "main.py"),
            base=base,
            target_name="AI Document Organizer.exe",
            icon=os.path.join(project_root, "assets", "generated-icon.png"),
            copyright="Copyright (c) 2024",
        )
    ],
)
