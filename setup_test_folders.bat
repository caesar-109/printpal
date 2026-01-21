@echo off
echo ========================================
echo Setting up test folder structure
echo ========================================
echo.

set TEST_BASE=C:\TestStudents

echo Creating test folder structure at: %TEST_BASE%
echo.

REM Create base folder
if not exist "%TEST_BASE%" mkdir "%TEST_BASE%"

REM Create test student folders with print subfolders
echo Creating test student folders...

REM Student 1
if not exist "%TEST_BASE%\student1" mkdir "%TEST_BASE%\student1"
if not exist "%TEST_BASE%\student1\print" mkdir "%TEST_BASE%\student1\print"
echo. > "%TEST_BASE%\student1\print\test1.pdf"
echo. > "%TEST_BASE%\student1\print\document1.txt"

REM Student 2
if not exist "%TEST_BASE%\student2" mkdir "%TEST_BASE%\student2"
if not exist "%TEST_BASE%\student2\print" mkdir "%TEST_BASE%\student2\print"
echo. > "%TEST_BASE%\student2\print\test2.pdf"
echo. > "%TEST_BASE%\student2\print\assignment.docx"

REM Student 3
if not exist "%TEST_BASE%\student3" mkdir "%TEST_BASE%\student3"
if not exist "%TEST_BASE%\student3\print" mkdir "%TEST_BASE%\student3\print"
echo. > "%TEST_BASE%\student3\print\report.pdf"

REM Student 4
if not exist "%TEST_BASE%\student4" mkdir "%TEST_BASE%\student4"
if not exist "%TEST_BASE%\student4\print" mkdir "%TEST_BASE%\student4\print"
echo. > "%TEST_BASE%\student4\print\assignment.pdf"

echo.
echo Test folder structure created!
echo.
echo Test students created:
echo   - student1 (2 files)
echo   - student2 (2 files)
echo   - student3 (1 file)
echo   - student4 (1 file)
echo.
echo You can now:
echo   1. Create a CSV/Excel file with usernames: student1, student2, student3
echo   2. Run PrintAgent.exe
echo   3. Select your CSV/Excel file
echo.
pause
