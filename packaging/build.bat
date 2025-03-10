@echo off
echo Building AI Document Organizer executable...

cd ..
echo Current directory: %CD%

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo Running PyInstaller...

pyinstaller --clean --onedir --windowed --name "AI Document Organizer" --icon assets/generated-icon.png --version-file packaging/version_info.txt --add-data "assets/generated-icon.png;." --add-data "docs;docs" main.py

if exist "dist\AI Document Organizer" (
    echo Build completed successfully!
    echo Executable is located in: %CD%\dist\AI Document Organizer
) else (
    echo Build process completed but executable not found.
    echo Expected executable directory: %CD%\dist\AI Document Organizer
    echo Check the PyInstaller output for details.
)

pause