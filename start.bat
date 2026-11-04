@echo off
rem ============================================================
rem  L3VPN Mapping App - one-click launcher (portable green build)
rem  Bundled Python runtime - no installation needed.
rem  Optional env var: PORT (default 8000)
rem  NOTE: keep this file pure ASCII (no Chinese) or cmd.exe
rem        will mis-parse it under the GBK code page.
rem ============================================================
cd /d "%~dp0"
set PORT=8000
if not "%PORT_ENV%"=="" set PORT=%PORT_ENV%

echo ==============================================
echo   L3VPN Mapping App
echo   URL: http://127.0.0.1:%PORT%
echo   Close this window to stop the service.
echo ==============================================

rem Open the default browser ~3s after the server starts.
rem NOTE: the URL must stay inside the quoted string, otherwise
rem       "start" splits it into separate arguments.
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & rundll32 url.dll,FileProtocolHandler http://127.0.0.1:%PORT%"

".\runtime\python.exe" -m uvicorn app:app --host 127.0.0.1 --port %PORT%
pause
