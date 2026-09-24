@echo off
setlocal enableextensions
title SplatKit 4D backend installer

rem ---------------------------------------------------------------------------
rem SplatKit backend installer bundle (distributed via GitHub Releases, NOT part
rem of the custom node package). This .bat and install_splat_backend.py travel
rem together. Drop BOTH into the ComfyUI-SplatKit folder (or the ComfyUI root)
rem and run this file. It builds the optional, self-contained CUDA backend under
rem ComfyUI-SplatKit\bin\ -- including downloading the SHA-256-pinned gsplat wheel
rem and uv. Nothing is installed into ComfyUI's own Python.
rem ---------------------------------------------------------------------------

set "HERE=%~dp0"

rem --- The installer script travels next to this .bat -------------------------
set "INSTALLER=%HERE%install_splat_backend.py"
if not exist "%INSTALLER%" (
  echo.
  echo Could not find install_splat_backend.py next to this file.
  echo Keep installer.bat and install_splat_backend.py together in the same folder.
  echo.
  pause
  exit /b 1
)

rem --- Locate the ComfyUI-SplatKit folder (the pack root) ----------------------
set "PACK="
if exist "%HERE%core\splatting\runtime.py" set "PACK=%HERE%"
if not defined PACK if exist "%HERE%custom_nodes\ComfyUI-SplatKit\core\splatting\runtime.py" set "PACK=%HERE%custom_nodes\ComfyUI-SplatKit\"
if not defined PACK (
  echo.
  echo Could not find the ComfyUI-SplatKit folder next to this file.
  echo Put installer.bat + install_splat_backend.py inside the ComfyUI-SplatKit folder
  echo ^(or the ComfyUI root^) and run again.
  echo.
  pause
  exit /b 1
)

rem Strip a trailing backslash: "%PACK%\" would escape the closing quote on the command
rem line and hand Python a path with a stray double-quote.
if "%PACK:~-1%"=="\" set "PACK=%PACK:~0,-1%"

rem --- Pick a Python interpreter ----------------------------------------------
rem Prefer ComfyUI portable's embedded Python if nearby, else the py launcher, else
rem python on PATH. PYEXE is always quoted when invoked, so a path with spaces and a
rem bare command both work.
set "PYEXE="
set "PYARGS="
if exist "%HERE%python_embeded\python.exe" set "PYEXE=%HERE%python_embeded\python.exe"
if not defined PYEXE if exist "%HERE%..\python_embeded\python.exe" set "PYEXE=%HERE%..\python_embeded\python.exe"
if not defined PYEXE if exist "%HERE%..\..\python_embeded\python.exe" set "PYEXE=%HERE%..\..\python_embeded\python.exe"
if not defined PYEXE if exist "%HERE%..\..\..\python_embeded\python.exe" set "PYEXE=%HERE%..\..\..\python_embeded\python.exe"
if not defined PYEXE (
  py -3 --version >nul 2>&1 && ( set "PYEXE=py" & set "PYARGS=-3" )
)
if not defined PYEXE (
  python --version >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
  echo.
  echo No Python interpreter found. Install Python 3.11+ or run this from a ComfyUI portable install.
  echo.
  pause
  exit /b 1
)

echo Installer : %INSTALLER%
echo Pack      : %PACK%
echo Python    : %PYEXE% %PYARGS%
echo.
echo This downloads about 7.5 GB (backend runtime + SHA-pinned gsplat wheel) and builds
echo the backend under the pack's bin\ folder. Models are installed separately (see docs/4DANYONE.md).
echo.

set "SPLATKIT_PACK_ROOT=%PACK%"
"%PYEXE%" %PYARGS% "%INSTALLER%" --pack-root "%PACK%" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo Done. Start ComfyUI and the Splat Backend Setup node should report "Ready".
) else (
  echo Installer exited with code %RC%. Scroll up for the error.
)
echo.
pause
exit /b %RC%
