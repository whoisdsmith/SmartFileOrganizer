# Packaging AI Document Organizer for Windows

This document explains how to package the AI Document Organizer application into a Windows executable and create an installer.

## Prerequisites

1. Install PyInstaller:
   ```
   pip install pyinstaller
   ```

2. Install NSIS (Nullsoft Scriptable Install System) for creating the installer:
   - Download from: https://nsis.sourceforge.io/Download
   - Install with default options

## Building the Executable

### Method 1: Using the build script (Recommended)

1. Navigate to the packaging directory:
   ```
   cd packaging
   ```

2. Run the build script:
   ```
   python build_exe.py
   ```

3. The executable will be created in the `../dist/AI Document Organizer` directory.

### Method 2: Manual PyInstaller command

1. Navigate to the packaging directory:
   ```
   cd packaging
   ```

2. Run PyInstaller with the spec file:
   ```
   pyinstaller --clean ai_document_organizer.spec
   ```

3. The executable will be created in the `../dist/AI Document Organizer` directory.

## Creating the Installer

1. Make sure you've built the executable first using one of the methods above.

2. Navigate to the packaging directory:
   ```
   cd packaging
   ```

3. Compile the NSIS installer script:
   - Right-click on `installer.nsi`
   - Select "Compile NSIS Script" (if you have NSIS installed)

   OR

   - Open NSIS
   - Click "Compile NSI scripts"
   - Select the `installer.nsi` file

4. The installer (`AI Document Organizer Setup.exe`) will be created in the packaging directory.

## Distribution

The final installer can be distributed to users who can then install the application on their Windows systems.

## Project Structure

The packaging files are organized as follows:

```
AI-Document-Organizer/
├── packaging/                # Packaging-related files
│   ├── ai_document_organizer.spec  # PyInstaller specification
│   ├── version_info.txt      # Version information
│   ├── installer.nsi         # NSIS installer script
│   ├── build_exe.py          # Build script
│   └── setup_cx_freeze.py    # cx_Freeze setup script
├── assets/                   # Application assets
│   └── generated-icon.png    # Application icon
├── docs/                     # Documentation
│   └── LICENSE.txt           # License file for installer
├── src/                      # Source code
└── main.py                   # Main entry point
```

## Troubleshooting

### Missing DLLs or Modules

If the executable fails to run due to missing DLLs or modules:

1. Edit the `ai_document_organizer.spec` file
2. Add the missing modules to the `hiddenimports` list
3. Rebuild the executable

### Icon Issues

If the icon doesn't appear correctly:

1. Make sure the icon file (`assets/generated-icon.png`) exists
2. Try converting the icon to `.ico` format and update the spec file accordingly

### NSIS Errors

If you encounter errors during NSIS compilation:

1. Make sure all paths in the `installer.nsi` file are correct
2. Check that the `dist/AI Document Organizer` directory exists and contains the built application
3. Verify that you have the required NSIS plugins installed

### Version Information

The application version information is stored in `version_info.txt` and is automatically included in the executable when building with the spec file. If you need to update the version:

1. Edit the `version_info.txt` file
2. Update the version numbers in both `filevers` and `prodvers` tuples
3. Update the `FileVersion` and `ProductVersion` string values
4. Rebuild the executable