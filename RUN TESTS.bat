@echo off
REM Double-click this to run every test on the Daily Measurement Excel Filer.
REM Nothing real is touched - the tests work in a throwaway folder.
REM The full report is written to:  Test Results\latest_test_run.md

cd /d "%~dp0"
python "tests\run_tests.py"
echo.
pause
