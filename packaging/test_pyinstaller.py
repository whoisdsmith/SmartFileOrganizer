import subprocess
import sys

print("Python version:", sys.version)
print("Testing PyInstaller...")

try:
    result = subprocess.run(["pyinstaller", "--version"],
                            capture_output=True, text=True)
    print("PyInstaller version:", result.stdout.strip())
    print("Return code:", result.returncode)
    if result.stderr:
        print("Error output:", result.stderr)
except Exception as e:
    print("Error running PyInstaller:", e)

print("Test complete.")
