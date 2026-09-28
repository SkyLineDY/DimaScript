# DimaScript

A Windows desktop application for transcribing audio and video into timestamped text and SRT subtitles.

## Features

- Select a recording, output folder and recognition language.
- Follow transcription progress and elapsed time.
- Preview, copy and open the resulting transcript.
- Keep each recording's output in a separate folder.
- Stop an active transcription while retaining its partial output.

The interface is in Russian. Recognition supports Russian, English and automatic language detection. Processing runs locally on the CPU with the bundled Whisper small model. Transcripts may contain recognition errors, especially in names and technical terms.

## Install

Open [Releases](https://github.com/SkyLineDY/DimaScript/releases) and download `DimaScript-Setup.exe`. Run the installer and optionally create a desktop shortcut. The installer includes the recognition model and Python runtime; no separate Python installation is required.

Requires 64-bit Windows 10 or later. Allow at least 2 GB of free disk space for installation and additional space for your recordings and output.

## Use

1. Select an audio or video file.
2. Choose an output folder and recording language.
3. Click **Начать транскрипцию** (Start transcription).
4. Open the generated folder to access `Транскрипция.txt` and `Субтитры.srt`.

Preferences are stored under `%LOCALAPPDATA%\DimaScript`. Each transcription uses a new output folder to preserve earlier results.

## Build from source

Install **64-bit Python 3.12** with Tcl/Tk support and **Inno Setup 6**. From the repository root, run in PowerShell:

```powershell
.\scripts\build.ps1
```

The script creates `.venv`, installs the pinned dependencies, runs the tests, downloads the pinned model, builds the application and compiles the installer. The first build requires internet access. Outputs:

- `dist/DimaScript/` — portable application folder (keep its contents together).
- `dist/DimaScript-Setup.exe` — installer.
- `dist/DimaScript-Setup.sha256` — installer checksum.

Use `-SkipInstaller` to build only the portable application, or `-InnoSetupCompiler 'C:\path\to\ISCC.exe'` to select the compiler explicitly. `-Python` accepts a Python 3.12 executable path.

To run the source after dependencies and model have been prepared:

```powershell
.\.venv\Scripts\python.exe .\src\app.py
```

To run tests separately in a Windows desktop session:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The existing artwork is included. `scripts/create_brand.py` optionally regenerates it using Pillow and the Windows Segoe UI fonts; it is not part of the normal build.

## Recognition engine and third-party components

DimaScript uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper), based on [OpenAI Whisper](https://github.com/openai/whisper), with [SYSTRAN's converted small model](https://huggingface.co/Systran/faster-whisper-small/tree/536b0662742c02347bc0e980a01041f333bce120).

Model revision: `536b0662742c02347bc0e980a01041f333bce120`.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [licenses/](licenses/) for attribution and component license texts. Third-party components remain subject to their respective licenses.

## License

The DimaScript application source and original artwork are provided under the [MIT License](LICENSE). Bundled runtimes, model weights and media libraries have their own licenses; the MIT license does not replace them.
