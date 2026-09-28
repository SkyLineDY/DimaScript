param(
    [string]$Python = 'py',
    [string]$InnoSetupCompiler = '',
    [switch]$SkipInstaller
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepoRoot = Split-Path -Parent $PSScriptRoot
function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Command" }
}
Push-Location -LiteralPath $RepoRoot
try {
    $VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        $BaseArguments = @()
        if ([IO.Path]::GetFileNameWithoutExtension($Python) -eq 'py') { $BaseArguments += '-3.12' }
        Invoke-Checked $Python ($BaseArguments + @('-c', 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 required"; assert sys.maxsize > 2**32, "64-bit Python required"; import tkinter'))
        Invoke-Checked $Python ($BaseArguments + @('-m', 'venv', '.venv'))
    }
    Invoke-Checked $VenvPython @('-c', 'import sys; assert sys.version_info[:2] == (3, 12); assert sys.maxsize > 2**32; import tkinter; t=tkinter.Tcl(); print("Tcl", t.eval("info patchlevel"))')
    Invoke-Checked $VenvPython @('-m', 'pip', 'install', '-r', 'requirements-build.txt')
    Invoke-Checked $VenvPython @('-m', 'pip', 'check')
    $PreviousPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = Join-Path $RepoRoot 'src'
        Invoke-Checked $VenvPython @('-m', 'unittest', 'discover', '-s', 'tests', '-v')
    } finally { $env:PYTHONPATH = $PreviousPythonPath }
    Invoke-Checked $VenvPython @('scripts\download_model.py')
    if (-not (Test-Path -LiteralPath 'THIRD_PARTY_NOTICES.md')) { throw 'THIRD_PARTY_NOTICES.md is required for distribution.' }
    if (-not (Test-Path -LiteralPath 'licenses')) { throw 'The licenses directory is required for distribution.' }
    Invoke-Checked $VenvPython @('-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath', 'dist', '--workpath', 'build', 'packaging\DimaScript.spec')
    $Output = Join-Path $RepoRoot 'dist\DimaScript'
    Copy-Item -LiteralPath 'assets\app.ico','assets\brand.png','README.md','THIRD_PARTY_NOTICES.md' -Destination $Output -Force
    Copy-Item -LiteralPath 'licenses' -Destination $Output -Recurse -Force
    Copy-Item -LiteralPath 'models' -Destination $Output -Recurse -Force
    if (Test-Path -LiteralPath 'LICENSE') { Copy-Item -LiteralPath 'LICENSE' -Destination $Output -Force }
    if (-not $SkipInstaller) {
        if (-not $InnoSetupCompiler) {
            $CompilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
            if ($CompilerCommand) { $InnoSetupCompiler = $CompilerCommand.Source }
            else {
                foreach ($Candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
                    if (Test-Path -LiteralPath $Candidate) { $InnoSetupCompiler = $Candidate; break }
                }
            }
        }
        if (-not $InnoSetupCompiler -or -not (Test-Path -LiteralPath $InnoSetupCompiler)) { throw 'Install Inno Setup 6 or specify -InnoSetupCompiler.' }
        Invoke-Checked $InnoSetupCompiler @('packaging\DimaScript.iss')
        $Installer = Join-Path $RepoRoot 'dist\DimaScript-Setup.exe'
        $Hash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
        [IO.File]::WriteAllText((Join-Path $RepoRoot 'dist\DimaScript-Setup.sha256'), "$Hash  DimaScript-Setup.exe`n", [Text.UTF8Encoding]::new($false))
    }
} finally { Pop-Location }

