# InstallerReady

A python 3 app that allows users to download programs/apps.

https://github.com/coltonsr77/Python3-windows-installer uses InstallerReady as a helper tool for downloading apps or apps that`s needed.

Download Page: https://coltonsr77.net/Download (Updated!)

Usage
-----

Run the GUI:

```bash
python installerready.py
```

Set a GitHub token to increase API rate limits (optional):

```bash
export GITHUB_TOKEN=ghp_...    # Linux / macOS
setx GITHUB_TOKEN "ghp_..."   # Windows (PowerShell / cmd differs)
```

Build a Windows executable with PyInstaller (example):

```bash
pip install pyinstaller
pyinstaller installerready.spec
```

Notes
-----
- The app requires Python 3 and the `requests` package (`pip install -r requirements.txt`).
- `tkinter` is used for the GUI and is included with most Python installations (on Linux you may need the system package `python3-tk`).
- Error details are appended to `~/.installerready.log` and the app will offer to open the log when an error occurs.

If you want me to add a packaged release script or CI workflow for building, tell me which target platforms to support.
