@ECHO OFF
pushd %~dp0

REM ——————————————————————————————————————————
REM  Command file for Sphinx documentation
REM ——————————————————————————————————————————

if "%SPHINXBUILD%" == "" (
    set SPHINXBUILD=sphinx-build
)

set SOURCEDIR=source
set BUILDDIR=build

REM 1) Verify that sphinx-build exists (quietly)
%SPHINXBUILD% --version >NUL 2>NUL
if errorlevel 9009 (
    echo.
    echo The 'sphinx-build' command was not found. Make sure you have Sphinx installed,
    echo then set SPHINXBUILD to the full path of the executable, or add it to your PATH.
    echo For installation instructions see https://www.sphinx-doc.org/
    echo.
    exit /b 1
)

REM 2) If no target is given, show help
if "%1" == "" goto help

REM 3) Run the requested build target and let all output (including errors) go to the console
%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
popd