import os
import subprocess
import sys
import shutil


def build_executable():
    """
    Build the executable using PyInstaller with the spec file.

    This function:
    1. Determines the project root and packaging directories
    2. Cleans up previous build artifacts
    3. Runs PyInstaller with the spec file
    4. Verifies the build was successful
    """
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

    # Build the executable using just the spec file
    # Note: The version info is already included in the spec file
    print("Running PyInstaller...")
    result = subprocess.run([
        "pyinstaller",
        "--clean",
        "ai_document_organizer.spec"
    ], capture_output=True, text=True)

    # Check if build was successful
    if result.returncode != 0:
        print("Error building executable:")
        print(result.stderr)
        return False

    # Verify the executable was created
    exe_path = os.path.abspath('../dist/AI Document Organizer')
    if os.path.exists(exe_path):
        print("Build completed successfully!")
        print(f"Executable is located in: {exe_path}")
        return True
    else:
        print("Build process completed but executable not found.")
        print("Check the PyInstaller output for details.")
        return False


if __name__ == "__main__":
    build_executable()
