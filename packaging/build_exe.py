import os
import subprocess
import sys
import shutil


def build_executable():
    """Build the executable using PyInstaller"""
    print("Building AI Document Organizer executable...")

    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Change to the packaging directory
    os.chdir(script_dir)

    # Clean up previous builds
    if os.path.exists("build"):
        print("Removing previous build directory...")
        shutil.rmtree("build")

    if os.path.exists("dist"):
        print("Removing previous dist directory...")
        shutil.rmtree("dist")

    # Build the executable
    print("Running PyInstaller...")
    result = subprocess.run([
        "pyinstaller",
        "--clean",
        "--version-file=version_info.txt",
        "ai_document_organizer.spec"
    ], capture_output=True, text=True)

    # Check if build was successful
    if result.returncode != 0:
        print("Error building executable:")
        print(result.stderr)
        return False

    print("Build completed successfully!")
    print(
        f"Executable is located in: {os.path.abspath('../dist/AI Document Organizer')}")
    return True


if __name__ == "__main__":
    build_executable()
