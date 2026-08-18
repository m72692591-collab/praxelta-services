@echo off
setlocal
set "ROOT=%~dp0"
where pwsh.exe >nul 2>nul
if %errorlevel%==0 (
  pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\update_github_description.ps1"
) else (
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\update_github_description.ps1"
)
set "CODE=%errorlevel%"
echo.
if "%CODE%"=="0" (
  echo GitHub description ПРАКСЕЛЬТЫ заменён и повторно подтверждён через API.
) else (
  echo Обновление не подтверждено. Ошибка выше является фактическим административным блокером.
)
exit /b %CODE%
