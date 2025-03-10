import os
import subprocess
import sys
import shutil


def build_executable():
    """
    Build the executable using PyInstaller.

    This function:
    1. Determines the project root and packaging directories
    2. Cleans up previous build artifacts
    3. Runs PyInstaller with the appropriate options
    4. Verifies the build was successful
    """
    print("Building AI Document Organizer executable...")

    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Change to the project root directory
    os.chdir(project_root)

    print(f"Current directory: {os.getcwd()}")

    # Clean up previous builds
    if os.path.exists("dist"):
        print("Removing previous dist directory...")
        shutil.rmtree("dist")

    if os.path.exists("build"):
        print("Removing previous build directory...")
        shutil.rmtree("build")

    # Build the executable
    print("Running PyInstaller...")

    # Run PyInstaller with the appropriate options
    try:
        # Option 1: Use the spec file
        # result = subprocess.run([
        #     "pyinstaller",
        #     "--clean",
        #     os.path.join("packaging", "ai_document_organizer.spec")
        # ], check=True)

        # Option 2: Use command-line options (more reliable)
        result = subprocess.run([
            "pyinstaller",
            "--clean",
            "--onedir",
            "--windowed",
            "--name", "AI Document Organizer",
            "--icon", os.path.join("assets", "generated-icon.png"),
            "--version-file", os.path.join("packaging", "version_info.txt"),
            "--add-data", f"{os.path.join('assets', 'generated-icon.png')};.",
            "--add-data", f"{os.path.join('docs')};docs",
            "--hidden-import", "google.generativeai",
            "--hidden-import", "openai",
            "--hidden-import", "pandas",
            "--hidden-import", "openpyxl",
            "--hidden-import", "numpy",
            "--hidden-import", "chardet",
            "--hidden-import", "bs4",
            "--hidden-import", "docx",
            "main.py"
        ], check=True)

        print("PyInstaller completed with return code:", result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed with return code: {e.returncode}")
        return False

    # Verify the executable was created
    exe_dir = os.path.join(project_root, "dist", "AI Document Organizer")
    if os.path.exists(exe_dir):
        print("Build completed successfully!")
        print(f"Executable is located in: {exe_dir}")
        return True
    else:
        print("Build process completed but executable not found.")
        print(f"Expected executable directory: {exe_dir}")
        print("Check the PyInstaller output for details.")
        return False


if __name__ == "__main__":
    build_executable()
