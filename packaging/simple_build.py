import os
import subprocess
import sys

print("Simple PyInstaller Build Script")
print("Python version:", sys.version)

# Get the project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

print(f"Current directory: {os.getcwd()}")
print(f"Script directory: {script_dir}")
print(f"Project root: {project_root}")

# Change to the project root directory
os.chdir(project_root)
print(f"Changed to directory: {os.getcwd()}")

# Run PyInstaller with a simple command
print("Running PyInstaller...")
try:
    result = subprocess.run([
        "pyinstaller",
        "--onedir",
        "--windowed",
        "--name", "AI Document Organizer",
        "--icon", "assets/generated-icon.png",
        "main.py"
    ], check=True)
    print("PyInstaller completed with return code:", result.returncode)

    # Check if the executable was created
    exe_dir = os.path.join(project_root, "dist", "AI Document Organizer")
    if os.path.exists(exe_dir):
        print("Build completed successfully!")
        print(f"Executable is located in: {exe_dir}")
    else:
        print("Build process completed but executable not found.")
        print(f"Expected executable directory: {exe_dir}")
except Exception as e:
    print(f"Error running PyInstaller: {e}")

print("Script completed.")
