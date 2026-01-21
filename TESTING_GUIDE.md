# PrintAgent Prototype - Testing Guide

## 🚀 Quick Test Steps

### Step 1: Build the EXE
```batch
build_exe.bat
```
Wait for it to complete. You should see `dist\PrintAgent.exe`

### Step 2: Setup Test Environment
```batch
setup_test_folders.bat
```
This creates:
- `C:\TestStudents\student1\print\` (with test files)
- `C:\TestStudents\student2\print\` (with test files)
- `C:\TestStudents\student3\print\` (with test files)

### Step 3: Create Test CSV
```batch
python create_test_csv.py
```
This creates `test_print_requests.csv` and `test_print_requests.xlsx` matching your web app format.

### Step 4: Test the EXE
1. Double-click `dist\PrintAgent.exe`
2. Select `test_print_requests.xlsx` (or CSV)
3. Watch it process!

## ✅ What Should Happen

1. **File Selection Dialog** opens
2. After selecting CSV/Excel, it reads the "Username" column
3. For each username (student1, student2, student3):
   - Looks in `C:\TestStudents\{username}\print\`
   - Copies files to `C:\TodayPrints\`
   - Sends files to printer
4. Shows completion dialog with stats
5. Creates log file at `C:\TodayPrints\print_agent.log`

## 📋 Expected Output

```
Students processed: 3
Files printed: 5
Skipped: 0
Errors: 0
```

## 🔍 Verify It Works

1. **Check log file**: `C:\TodayPrints\print_agent.log`
   - Should show all operations
   - Look for "Sent to printer" messages

2. **Check copied files**: `C:\TodayPrints\`
   - Should see files like: `student1_test1.pdf`, `student2_test2.pdf`, etc.

3. **Check printer**: 
   - Files should appear in print queue (if printer is connected)
   - Or check "Print to PDF" if that's your default

## 🐛 Troubleshooting

### "No IDs Found"
- Make sure CSV/Excel has "Username" column
- Check file isn't empty

### "Folder not found"
- Run `setup_test_folders.bat` again
- Verify folders exist: `C:\TestStudents\student1\print\`

### "Error reading file"
- Make sure pandas is installed: `pip install pandas openpyxl`
- Check file isn't corrupted

### EXE doesn't run
- Make sure you built it: `build_exe.bat`
- Check `dist\PrintAgent.exe` exists
- Try running from command line to see errors

## 🔄 Switching to Production Mode

When ready to test with real college server:

1. Edit `print_agent.py`:
   ```python
   TEST_MODE = False
   COLLEGE_SERVER = r"\\college-server\students"  # Your actual path
   ```

2. Rebuild:
   ```batch
   build_exe.bat
   ```

3. Test with real CSV export from web app

## 📝 Notes

- **Test mode** uses `C:\TestStudents\` (safe, local)
- **Production mode** uses `\\college-server\students\` (network)
- Log file always created at `C:\TodayPrints\print_agent.log`
- Files are copied to `C:\TodayPrints\` before printing
