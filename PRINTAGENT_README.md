# PrintAgent - Automated Printing Utility (Prototype)

## Quick Start

### 1. Build the EXE
```batch
build_exe.bat
```
This will create `dist\PrintAgent.exe`

### 2. Setup Test Folders (Optional)
```batch
setup_test_folders.bat
```
Creates test student folders at `C:\TestStudents\`

### 3. Create Test CSV/Excel
```batch
python create_test_csv.py
```
Creates test files matching web app export format

### 4. Run PrintAgent
- Double-click `dist\PrintAgent.exe`
- Select your CSV/Excel file
- Watch it process!

## Current Configuration

**TEST MODE** (Default):
- Uses local folder: `C:\TestStudents\`
- Safe for testing without network access

**To switch to PRODUCTION MODE:**
1. Open `print_agent.py`
2. Change:
   ```python
   TEST_MODE = False
   COLLEGE_SERVER = r"\\college-server\students"
   ```
3. Rebuild EXE: `build_exe.bat`

## File Structure Expected

```
C:\TestStudents\          (or \\college-server\students\)
├── student1\
│   └── print\
│       ├── file1.pdf
│       └── file2.txt
├── student2\
│   └── print\
│       └── document.pdf
└── student3\
    └── print\
        └── report.pdf
```

## CSV/Excel Format

The app reads the **"Username"** column (which equals admission_id):

| Date | Student Name | Semester | Branch | Username |
|------|--------------|----------|--------|----------|
| 01-01-2024 | John Doe | S3 | CSE-A | student1 |

## Output

- **Copied files**: `C:\TodayPrints\{username}_filename.ext`
- **Log file**: `C:\TodayPrints\print_agent.log`
- **Printed files**: Sent to default printer

## Troubleshooting

1. **"No IDs Found"**
   - Make sure CSV/Excel has "Username" column
   - Check file isn't corrupted

2. **"Folder not found"**
   - Verify test folders exist: `C:\TestStudents\{username}\print\`
   - Check folder permissions

3. **Files not printing**
   - Ensure default printer is set
   - Check printer is online
   - See log file for details

4. **Build errors**
   - Make sure Python 3.11+ is installed
   - Run: `pip install -r requirements_print_agent.txt`

## Next Steps

Once prototype works:
1. Test with real CSV export from web app
2. Update `COLLEGE_SERVER` path in `print_agent.py`
3. Set `TEST_MODE = False`
4. Rebuild and deploy to faculty PC
