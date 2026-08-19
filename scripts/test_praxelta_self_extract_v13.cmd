@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PRAXELTA_SELF=%~f0"
set "PRAXELTA_PS1=%TEMP%\PRAXELTA_WRAP_TEST_%RANDOM%_%RANDOM%.ps1"
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$src=$env:PRAXELTA_SELF;$dst=$env:PRAXELTA_PS1;$m='###PRAXELTA_POWERSHELL_PAYLOAD_V1_3###';$t=[IO.File]::ReadAllText($src,[Text.Encoding]::UTF8);$i=$t.LastIndexOf($m,[StringComparison]::Ordinal);if($i -lt 0){exit 90};$b=$t.Substring($i+$m.Length).TrimStart([char]13,[char]10);[IO.File]::WriteAllText($dst,$b,(New-Object Text.UTF8Encoding($true)))"
set "EXTRACT_RC=%ERRORLEVEL%"
if not "%EXTRACT_RC%"=="0" exit /b %EXTRACT_RC%
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%PRAXELTA_PS1%"
set "RC=%ERRORLEVEL%"
del /q "%PRAXELTA_PS1%" >nul 2>&1
exit /b %RC%
###PRAXELTA_POWERSHELL_PAYLOAD_V1_3###
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$proof = Join-Path $env:TEMP 'praxelta-wrapper-v13-ok.txt'
[IO.File]::WriteAllText($proof, 'PRAXELTA_WRAPPER_V13_OK', (New-Object Text.UTF8Encoding($false)))
Write-Host 'PRAXELTA_WRAPPER_V13_OK'
exit 0
