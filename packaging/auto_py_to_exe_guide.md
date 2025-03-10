# Using Auto-Py-To-Exe to Package AI Document Organizer

Auto-Py-To-Exe provides a graphical interface for PyInstaller, making it easier to package Python applications into executables.

## Installation

1. Install Auto-Py-To-Exe:
   ```
   pip install auto-py-to-exe
   ```

## Packaging Steps

1. Navigate to the project root directory:
   ```
   cd /path/to/AI-Document-Organizer
   ```

2. Launch Auto-Py-To-Exe:
   ```
   auto-py-to-exe
   ```

3. Configure the packaging settings:

   - **Script Location**: Browse and select `main.py` in the project root
   - **Onefile**: Select "One Directory" (recommended for this application)
   - **Console**: Select "Window Based (hide the console)"
   - **Icon**: Browse and select `assets/generated-icon.png`
   - **Additional Files**: Add the following:
     - Add `assets/generated-icon.png` as `generated-icon.png`
     - Add `docs` folder as `docs`

4. Advanced Settings:
   - Click "Advanced" to expand additional options
   - Add the following hidden imports:
     - `google.generativeai`
     - `openai`
     - `pandas`
     - `openpyxl`
     - `numpy`
     - `chardet`
     - `bs4`
     - `python-docx`

5. Click "CONVERT .PY TO .EXE" to start the packaging process.

6. Once complete, click "OPEN OUTPUT FOLDER" to access your executable.

## Creating an Installer

After generating the executable with Auto-Py-To-Exe, you can still use the NSIS script provided in this repository to create an installer:

1. Make sure the executable is built and located in the `output/AI Document Organizer` directory.

2. Copy the NSIS script from the packaging directory:
   ```
   cp packaging/installer.nsi output/installer.nsi
   ```

3. Edit the NSIS script to point to the correct output directory:
   ```nsi
   ; Change this line:
   File /r "../dist/AI Document Organizer/*.*"

   ; To:
   File /r "AI Document Organizer/*.*"
   ```

4. Navigate to the output directory:
   ```
   cd output
   ```

5. Compile the NSIS script as described in the main packaging guide.

## Troubleshooting

- If you encounter missing modules, add them to the "Hidden Imports" section.
- For file not found errors, make sure all required files are added in the "Additional Files" section.
- If the application crashes on startup, try the "One Directory" option instead of "One File".