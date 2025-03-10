# Using cx_Freeze to Package AI Document Organizer

cx_Freeze is an alternative to PyInstaller that can be used to package Python applications into executables.

## Installation

1. Install cx_Freeze:
   ```
   pip install cx_freeze
   ```

## Packaging Steps

1. Navigate to the packaging directory:
   ```
   cd packaging
   ```

2. Run the setup script to build the executable:
   ```
   python setup_cx_freeze.py build
   ```

3. The executable will be created in the `build` directory, typically in a subdirectory like `build/exe.win-amd64-3.10/` (the exact name depends on your Python version and system architecture).

## Creating an Installer with cx_Freeze

cx_Freeze can also create an MSI installer for Windows:

1. Navigate to the packaging directory:
   ```
   cd packaging
   ```

2. Run the setup script with the bdist_msi command:
   ```
   python setup_cx_freeze.py bdist_msi
   ```

3. The MSI installer will be created in the `dist` directory.

## Project Structure

The cx_Freeze setup script is designed to work with the following project structure:

```
AI-Document-Organizer/
├── packaging/                # Packaging-related files
│   └── setup_cx_freeze.py    # cx_Freeze setup script
├── assets/                   # Application assets
│   └── generated-icon.png    # Application icon
├── docs/                     # Documentation
├── src/                      # Source code
└── main.py                   # Main entry point
```

## Advantages of cx_Freeze

- Often handles Python packages better than PyInstaller
- Can create MSI installers directly
- May result in smaller executables for certain applications
- Good for applications with complex dependencies

## Troubleshooting

### Missing Modules

If your application is missing modules:

1. Edit the `setup_cx_freeze.py` file
2. Add the missing module to the `packages` list
3. Rebuild the executable

### Missing Files

If your application is missing data files:

1. Edit the `setup_cx_freeze.py` file
2. Add the missing files to the `include_files` list
3. Rebuild the executable

### DLL Issues

If you encounter DLL errors:

1. Set `include_msvcr` to `True` in the build options
2. Try adding the specific DLL to the `include_files` list
3. Rebuild the executable