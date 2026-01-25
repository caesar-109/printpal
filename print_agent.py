import os
import sys
import csv
import shutil
import subprocess
import logging
import time
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox, Tk
import tkinter as tk

# ============================================================================
# CONFIGURATION - Change these for production
# ============================================================================
# TEST MODE: Use local test folder
TEST_MODE = True
TEST_STUDENTS_FOLDER = r"C:\TestStudents"  # Local test path

# PRODUCTION MODE: College server path (set TEST_MODE = False when ready)
COLLEGE_SERVER = r"\\college-server\students"  # Will be used when TEST_MODE = False

# Other settings
LOCAL_WORK_FOLDER = r"C:\TodayPrints"
PRINT_COST_FOLDER = r"C:\TodayPrints\Print Cost"  # Folder for billing Excel files
SUMATRA_PDF_PATH = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"  # Optional
LOG_FILE = r"C:\TodayPrints\print_agent.log"

# Supported file extensions for printing
PRINTABLE_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.xps', '.jpg', '.jpeg', '.png', '.bmp'}

class PrintAgent:
    def __init__(self):
        self.setup_logging()
        self.setup_work_folder()
        self.files_to_print = []
        self.stats = {
            'processed': 0,
            'printed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Set base path based on mode
        if TEST_MODE:
            self.base_path = Path(TEST_STUDENTS_FOLDER)
            self.logger.info("*** RUNNING IN TEST MODE ***")
            self.logger.info(f"Test folder: {TEST_STUDENTS_FOLDER}")
        else:
            self.base_path = Path(COLLEGE_SERVER)
            self.logger.info("*** RUNNING IN PRODUCTION MODE ***")
            self.logger.info(f"College server: {COLLEGE_SERVER}")
        
    def setup_logging(self):
        """Setup logging to file"""
        log_dir = Path(LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_work_folder(self):
        """Create local working folder if it doesn't exist"""
        Path(LOCAL_WORK_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(PRINT_COST_FOLDER).mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Work folder ready: {LOCAL_WORK_FOLDER}")
        self.logger.info(f"Print Cost folder ready: {PRINT_COST_FOLDER}")
    
    def clean_copied_print_files(self):
        """Clean only copied print files from previous sessions
        Keeps: Print Cost folder, log files, session logs
        Deletes: Only copied print files (pattern: {admission_id}_filename.ext)
        Runs at startup before each new session to prevent duplicate printing
        """
        work_folder = Path(LOCAL_WORK_FOLDER)
        deleted_count = 0
        failed_count = 0
        skipped_count = 0
        
        if not work_folder.exists():
            self.logger.info("Work folder does not exist, nothing to clean")
            return
        
        # Files/folders to preserve (exact names)
        preserve_items = {
            'Print Cost',  # Billing folder
            'session_logs',  # Future resume feature
            'print_agent.log',  # Log file
        }
        
        # Get all items in work folder
        try:
            items = list(work_folder.iterdir())
        except Exception as e:
            self.logger.error(f"Cannot access work folder: {str(e)}")
            return
        
        if not items:
            self.logger.info("Work folder is empty, nothing to clean")
            return
        
        self.logger.info(f"Scanning {len(items)} item(s) in work folder for cleanup...")
        
        # Delete only copied print files (not folders, not preserved files)
        for item in items:
            # Skip folders (like "Print Cost", "session_logs")
            if item.is_dir():
                skipped_count += 1
                self.logger.debug(f"Skipping folder: {item.name}")
                continue
            
            # Skip preserved files (like log file)
            if item.name in preserve_items:
                skipped_count += 1
                self.logger.debug(f"Preserving file: {item.name}")
                continue
            
            # Try to delete copied print files
            # These follow pattern: {admission_id}_{original_filename}
            try:
                # Check if file exists and is accessible
                if not item.exists():
                    continue
                
                # Try to delete
                item.unlink()
                deleted_count += 1
                self.logger.info(f"✓ Cleaned: {item.name}")
                
            except PermissionError as e:
                failed_count += 1
                self.logger.warning(f"✗ Permission denied: {item.name} (file may be locked by another process)")
            except FileNotFoundError:
                # File was already deleted, skip
                pass
            except Exception as e:
                failed_count += 1
                self.logger.warning(f"✗ Could not delete {item.name}: {str(e)}")
        
        # Summary
        if deleted_count > 0:
            self.logger.info(f"Cleanup complete: {deleted_count} file(s) deleted, {skipped_count} preserved, {failed_count} failed")
        elif failed_count > 0:
            self.logger.warning(f"Cleanup had issues: {failed_count} file(s) could not be deleted (may be in use)")
        else:
            self.logger.info(f"Cleanup complete: No old print files found ({skipped_count} preserved items)")
        
    def select_csv_file(self):
        """Open file dialog to select CSV/Excel file"""
        root = Tk()
        root.withdraw()  # Hide main window
        
        file_path = filedialog.askopenfilename(
            title="Select CSV or Excel file with admission IDs (Username column)",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        root.destroy()
        return file_path
        
    def read_admission_ids(self, csv_path):
        """Read admission IDs (usernames) and print paths from CSV/Excel file
        Returns: List of dicts with 'admission_id' and 'print_path' keys
        """
        student_data = []
        
        try:
            # Handle Excel files
            if csv_path.lower().endswith('.xlsx'):
                try:
                    import pandas as pd
                    
                    # Read ALL sheets from Excel file
                    excel_file = pd.ExcelFile(csv_path)
                    sheet_names = excel_file.sheet_names
                    self.logger.info(f"Found {len(sheet_names)} sheet(s): {', '.join(sheet_names)}")
                    
                    all_student_data = []
                    
                    # Process each sheet
                    for sheet_name in sheet_names:
                        # Skip first 2 rows (merged header + empty row), use row 2 as headers
                        # This matches the web app export format: startrow=2
                        df = pd.read_excel(csv_path, sheet_name=sheet_name, header=2)
                        self.logger.info(f"Processing sheet '{sheet_name}' - columns: {list(df.columns)}")
                        
                        # Check for required columns
                        if 'Username' not in df.columns:
                            self.logger.warning(f"  No 'Username' column found in sheet '{sheet_name}', skipping")
                            continue
                        
                        # Check for Print Path column (new format)
                        has_print_path = 'Print Path (TEST)' in df.columns or 'Print Path' in df.columns
                        print_path_col = 'Print Path (TEST)' if 'Print Path (TEST)' in df.columns else 'Print Path'
                        
                        if not has_print_path:
                            self.logger.warning(f"  No 'Print Path' column found in sheet '{sheet_name}'")
                            self.logger.info(f"  Falling back to old format (constructing path from admission ID)")
                        
                        # Process each row
                        for idx, row in df.iterrows():
                            username = str(row['Username']).strip() if pd.notna(row['Username']) else None
                            if not username or username.lower() in ['username', 'nan', 'none']:
                                continue
                            
                            # Get print path from Excel or construct it
                            if has_print_path and pd.notna(row[print_path_col]):
                                print_path = str(row[print_path_col]).strip()
                            else:
                                # Fallback: construct path (old behavior)
                                print_path = str(self.base_path / username / "print")
                            
                            # Get student details for billing
                            student_name = str(row.get('Student Name', '')).strip() if pd.notna(row.get('Student Name', '')) else username
                            branch = str(row.get('Branch', '')).strip() if pd.notna(row.get('Branch', '')) else 'UNKNOWN'
                            year = str(row.get('Year', '')).strip() if pd.notna(row.get('Year', '')) else ''
                            semester = str(row.get('Semester', '')).strip() if pd.notna(row.get('Semester', '')) else ''
                            
                            all_student_data.append({
                                'admission_id': username,
                                'print_path': print_path,
                                'name': student_name,
                                'branch': branch,
                                'year': year,
                                'semester': semester
                            })
                        
                        self.logger.info(f"  Added {len([d for d in all_student_data if d['admission_id']])} entries from sheet '{sheet_name}'")
                    
                    # Remove duplicates while preserving order (based on admission_id)
                    seen_ids = set()
                    student_data = []
                    for student in all_student_data:
                        if student['admission_id'] not in seen_ids:
                            student_data.append(student)
                            seen_ids.add(student['admission_id'])
                    
                    self.logger.info(f"Total unique students across all sheets: {len(student_data)}")
                    
                    if not student_data:
                        raise ValueError("No student data found in any sheet")
                        
                except ImportError:
                    self.logger.error("pandas not installed. Cannot read Excel files.")
                    messagebox.showerror("Error", "pandas library required for Excel files.\nPlease install: pip install pandas openpyxl")
                    return []
                    
            else:
                # Handle CSV files
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    
                    self.logger.info(f"CSV columns found: {fieldnames}")
                    
                    if not fieldnames:
                        raise ValueError("CSV file has no headers")
                    
                    # Check for required columns
                    if 'Username' not in fieldnames:
                        raise ValueError("CSV file must contain 'Username' column")
                    
                    # Check for Print Path column
                    has_print_path = 'Print Path (TEST)' in fieldnames or 'Print Path' in fieldnames
                    print_path_col = 'Print Path (TEST)' if 'Print Path (TEST)' in fieldnames else 'Print Path'
                    
                    # Process each row
                    for row in reader:
                        username = row.get('Username', '').strip()
                        if not username or username.lower() in ['username', 'nan', 'none']:
                            continue
                        
                        # Get print path from CSV or construct it
                        if has_print_path and row.get(print_path_col):
                            print_path = row[print_path_col].strip()
                        else:
                            # Fallback: construct path (old behavior)
                            print_path = str(self.base_path / username / "print")
                        
                        # Get student details for billing
                        student_name = row.get('Student Name', '').strip() or username
                        branch = row.get('Branch', '').strip() or 'UNKNOWN'
                        year = row.get('Year', '').strip() or ''
                        semester = row.get('Semester', '').strip() or ''
                        
                        student_data.append({
                            'admission_id': username,
                            'print_path': print_path,
                            'name': student_name,
                            'branch': branch,
                            'year': year,
                            'semester': semester
                        })
                    
                    self.logger.info(f"Found {len(student_data)} entries in CSV")
                        
        except Exception as e:
            self.logger.error(f"Error reading file: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Failed to read file:\n{str(e)}")
            return []
            
        self.logger.info(f"Total valid student entries: {len(student_data)}")
        return student_data
        
    def copy_student_files(self, print_path, admission_id):
        """Copy all files from student's print folder to local work folder
        Args:
            print_path: Full path to the student's print folder (from Excel)
            admission_id: Student's admission ID (for naming copied files)
        """
        # Use the print path directly from Excel
        student_folder = Path(print_path)
        copied_files = []
        
        file_count = 0
        try:
            if not student_folder.exists():
                self.logger.warning(f"Folder not found: {student_folder}")
                return copied_files, file_count
                
            if not student_folder.is_dir():
                self.logger.warning(f"Path is not a directory: {student_folder}")
                return copied_files, file_count
                
            # Check read access
            try:
                test_access = os.access(str(student_folder), os.R_OK)
                if not test_access:
                    self.logger.warning(f"No read access: {student_folder}")
                    return copied_files, file_count
            except Exception as e:
                self.logger.warning(f"Access check failed: {str(e)}")
                
            # Get all files
            files = list(student_folder.glob("*"))
            files = [f for f in files if f.is_file()]
            file_count = len(files)
            
            if not files:
                self.logger.info(f"Empty folder: {student_folder}")
                return copied_files, file_count
                
            self.logger.info(f"Found {len(files)} file(s) in {student_folder}")
            
            # Copy each file
            for file_path in files:
                try:
                    # Create unique filename to avoid conflicts
                    dest_name = f"{admission_id}_{file_path.name}"
                    dest_path = Path(LOCAL_WORK_FOLDER) / dest_name
                    
                    # Skip if already exists (avoid re-copying)
                    if dest_path.exists():
                        self.logger.info(f"File already exists, skipping: {dest_name}")
                        copied_files.append(dest_path)
                        continue
                    
                    shutil.copy2(file_path, dest_path)
                    copied_files.append(dest_path)
                    self.logger.info(f"Copied: {file_path.name} -> {dest_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error copying {file_path.name}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error accessing folder for {admission_id}: {str(e)}", exc_info=True)
            
        return copied_files, file_count  # Return file count too
    
    def update_billing_records(self, session_data):
        """Update billing Excel files organized by branch+batch with year+semester sheets
        Structure: Print Cost/{BRANCH} BATCH {BATCH} {YEAR}.xlsx
        Sheets: {YEAR} {SEMESTER} (e.g., "2023 S3")
        Columns: Username, Name, No. of Files Printed
        """
        try:
            import pandas as pd
            
            # Group students by branch+batch+year for Excel file organization
            billing_groups = {}
            
            for student in session_data:
                admission_id = student['admission_id']
                name = student.get('name', admission_id)
                branch = student.get('branch', 'UNKNOWN')
                year = student.get('year', '')
                semester = student.get('semester', '')
                files_counted = student.get('files_counted', 0)
                
                # Extract batch from branch (e.g., "CSE-A" -> branch="CSE", batch="A")
                if '-' in branch:
                    branch_code, batch_code = branch.split('-', 1)
                    batch = batch_code.upper()
                else:
                    branch_code = branch
                    batch = 'A'  # Default batch for non-CSE branches
                
                # Create Excel filename: "AD BATCH A 2023.xlsx"
                excel_filename = f"{branch_code} BATCH {batch} {year}.xlsx"
                excel_path = Path(PRINT_COST_FOLDER) / excel_filename
                
                # Create sheet name: Just the year (e.g., "2023")
                sheet_name = str(year) if year else "Unknown"
                
                # Group key: (excel_filename, sheet_name)
                group_key = (excel_filename, sheet_name)
                
                if group_key not in billing_groups:
                    billing_groups[group_key] = []
                
                billing_groups[group_key].append({
                    'Username': admission_id,
                    'Name': name,
                    'Files_This_Session': files_counted
                })
            
            # Update each Excel file
            for (excel_filename, sheet_name), students in billing_groups.items():
                excel_path = Path(PRINT_COST_FOLDER) / excel_filename
                
                # Read existing Excel if it exists - IMPORTANT: Keep ALL existing students
                existing_students = {}  # {username: {'Name': name, 'Total': total}}
                if excel_path.exists():
                    try:
                        # Try to read the specific sheet
                        excel_file = pd.ExcelFile(excel_path)
                        if sheet_name in excel_file.sheet_names:
                            df_existing = pd.read_excel(excel_path, sheet_name=sheet_name)
                            for _, row in df_existing.iterrows():
                                username = str(row['Username'])
                                name = str(row.get('Name', username))
                                total = int(row.get('No. of Files Printed', 0))
                                existing_students[username] = {
                                    'Name': name,
                                    'Total': total
                                }
                            self.logger.info(f"Read {len(existing_students)} existing students from sheet {sheet_name}")
                    except Exception as e:
                        self.logger.warning(f"Error reading existing Excel {excel_filename} sheet {sheet_name}: {str(e)}")
                
                # Update totals for current session students
                for student in students:
                    username = student['Username']
                    name = student['Name']
                    files_this_session = student['Files_This_Session']
                    
                    # Get previous total or 0, update name if provided
                    if username in existing_students:
                        previous_total = existing_students[username]['Total']
                        # Keep existing name unless new one is provided
                        if name and name != username:
                            existing_students[username]['Name'] = name
                    else:
                        previous_total = 0
                        existing_students[username] = {'Name': name, 'Total': 0}
                    
                    # Add files from this session
                    new_total = previous_total + files_this_session
                    existing_students[username]['Total'] = new_total
                    
                    self.logger.info(f"Billing: {username} - Previous: {previous_total}, This session: {files_this_session}, New total: {new_total}")
                
                # Convert to DataFrame for writing
                updated_students = []
                for username, data in existing_students.items():
                    updated_students.append({
                        'Username': username,
                        'Name': data['Name'],
                        'No. of Files Printed': data['Total']
                    })
                
                # Sort by username
                updated_students.sort(key=lambda x: x['Username'])
                
                # Write to Excel - need to handle append mode properly
                if excel_path.exists():
                    # Read all existing sheets first
                    all_sheets = {}
                    try:
                        excel_file = pd.ExcelFile(excel_path)
                        for existing_sheet in excel_file.sheet_names:
                            if existing_sheet != sheet_name:  # Keep other sheets
                                all_sheets[existing_sheet] = pd.read_excel(excel_path, sheet_name=existing_sheet)
                    except Exception as e:
                        self.logger.warning(f"Error reading other sheets: {str(e)}")
                    
                    # Write all sheets (updated + existing)
                    with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                        # Write updated sheet
                        df_updated = pd.DataFrame(updated_students)
                        df_updated.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Write other sheets back
                        for sheet_name_other, df_other in all_sheets.items():
                            df_other.to_excel(writer, sheet_name=sheet_name_other, index=False)
                else:
                    # New file - just write the sheet
                    df_updated = pd.DataFrame(updated_students)
                    df_updated.to_excel(excel_path, sheet_name=sheet_name, index=False, engine='openpyxl')
                
                self.logger.info(f"Updated billing file: {excel_filename} - Sheet: {sheet_name}")
                
        except Exception as e:
            self.logger.error(f"Error updating billing records: {str(e)}", exc_info=True)
        
    def print_via_direct_spooler(self, file_path):
        """Print text files directly to Windows print spooler - NO file opening"""
        try:
            import win32print
            
            printer_name = win32print.GetDefaultPrinter()
            printer_handle = win32print.OpenPrinter(printer_name)
            
            try:
                # Read file content as binary
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # Start print job
                job_info = (f"PrintAgent: {file_path.name}", None, "RAW")
                job_id = win32print.StartDocPrinter(printer_handle, 1, job_info)
                win32print.StartPagePrinter(printer_handle)
                
                # Send data directly to printer spooler
                win32print.WritePrinter(printer_handle, file_data)
                win32print.EndPagePrinter(printer_handle)
                win32print.EndDocPrinter(printer_handle)
                
                return True
            finally:
                win32print.ClosePrinter(printer_handle)
                
        except ImportError:
            # pywin32 not available
            return False
        except Exception as e:
            self.logger.debug(f"Direct spooler failed: {str(e)}")
            return False
    
    def print_via_powershell_text(self, file_path):
        """Print text files via PowerShell Get-Content | Out-Printer (truly silent)"""
        try:
            file_str = str(file_path.resolve())
            ps_command = f'Get-Content -Path "{file_str}" -Raw | Out-Printer -ErrorAction SilentlyContinue'
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                check=False,
                timeout=30,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.debug(f"PowerShell text print failed: {str(e)}")
            return False
    
    def print_via_sumatra_pdf(self, file_path):
        """Print PDFs via SumatraPDF (truly silent)"""
        if not Path(SUMATRA_PDF_PATH).exists():
            return False
        try:
            file_str = str(file_path.resolve())
            result = subprocess.run(
                [SUMATRA_PDF_PATH, '-print-to-default', '-silent', file_str],
                check=False,
                timeout=30,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.debug(f"SumatraPDF print failed: {str(e)}")
            return False
    
    def print_file(self, file_path, file_index=None, total_files=None):
        """Print a file silently without opening it - uses best method for file type
        
        Args:
            file_path: Path to file to print
            file_index: Current file number (for progress display)
            total_files: Total files to print (for progress display)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            if file_index is not None:
                print(f" ✗ File not found")
            return False
            
        ext = file_path.suffix.lower()
        file_str = str(file_path.resolve())
        
        # Show progress in console
        if file_index is not None and total_files is not None:
            print(f"[{file_index}/{total_files}] Printing: {file_path.name}...", end='', flush=True)
        else:
            print(f"Printing: {file_path.name}...", end='', flush=True)
        
        # Check if file type is printable
        if ext not in PRINTABLE_EXTENSIONS:
            self.logger.warning(f"Unknown file type: {ext}, attempting silent print anyway")
        
        try:
            # Method 1: Direct print spooler for text files (BEST - no file opening)
            if ext in {'.txt', '.log', '.csv', '.text'}:
                if self.print_via_direct_spooler(file_path):
                    print(f" ✓ (Direct Spooler)")
                    self.logger.info(f"✓ Printed via direct spooler: {file_path.name}")
                    return True
                
                # Fallback: PowerShell Get-Content | Out-Printer
                if self.print_via_powershell_text(file_path):
                    print(f" ✓ (PowerShell)")
                    self.logger.info(f"✓ Printed via PowerShell: {file_path.name}")
                    return True
            
            # Method 2: SumatraPDF for PDFs (truly silent)
            if ext == '.pdf':
                if self.print_via_sumatra_pdf(file_path):
                    print(f" ✓ (SumatraPDF)")
                    self.logger.info(f"✓ Printed via SumatraPDF: {file_path.name}")
                    return True
            
            # Method 3: Try win32api ShellExecute with printto (for other file types)
            try:
                import win32print
                import win32api
                import win32con
                
                printer_name = win32print.GetDefaultPrinter()
                result = win32api.ShellExecute(
                    0,
                    "printto",
                    file_str,
                    f'"{printer_name}"',
                    ".",
                    win32con.SW_HIDE
                )
                
                if result > 32:
                    time.sleep(0.2)  # Give it a moment to queue
                    print(f" ✓ (Win32API)")
                    self.logger.info(f"✓ Printed via win32api: {file_path.name}")
                    return True
            except (ImportError, Exception) as e:
                pass
            
            # Method 4: PowerShell Out-Printer for other text-like files
            if ext in {'.doc', '.docx', '.rtf'}:
                # Try PowerShell print verb (may briefly open, but hidden)
                ps_command = f'$proc = Start-Process -FilePath "{file_str}" -Verb Print -WindowStyle Hidden -PassThru -ErrorAction SilentlyContinue; if ($proc) {{ Start-Sleep -Milliseconds 300; $proc.CloseMainWindow() }}'
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    check=False,
                    timeout=30,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0:
                    print(f" ✓ (PowerShell Print)")
                    self.logger.info(f"✓ Printed via PowerShell Print: {file_path.name}")
                    return True
            
            # All methods failed
            print(f" ✗ FAILED")
            self.logger.warning(f"All print methods failed: {file_path.name}")
            return False
            
        except subprocess.TimeoutExpired:
            print(f" ✗ TIMEOUT")
            self.logger.error(f"Print timeout: {file_path.name}")
            return False
        except Exception as e:
            print(f" ✗ ERROR")
            self.logger.error(f"Error printing {file_path.name}: {str(e)}")
            return False
            
    def process_all(self, csv_path):
        """Main processing function"""
        # Show console header
        print("\n" + "=" * 70)
        print("PrintAgent - Automated Printing System")
        print("=" * 70)
        print(f"CSV/Excel file: {Path(csv_path).name}")
        print(f"Mode: {'TEST' if TEST_MODE else 'PRODUCTION'}")
        print("=" * 70 + "\n")
        
        self.logger.info("=" * 70)
        self.logger.info("PrintAgent started")
        self.logger.info(f"CSV/Excel file: {csv_path}")
        self.logger.info(f"Base path: {self.base_path}")
        self.logger.info(f"Mode: {'TEST' if TEST_MODE else 'PRODUCTION'}")
        self.logger.info("=" * 70)
        
        # Clean old copied print files before starting new session
        # This prevents duplicate printing from previous sessions
        print("Cleaning old print files from previous session...")
        self.logger.info("Cleaning old print files from previous session...")
        self.clean_copied_print_files()
        print()  # Blank line after cleanup
        
        try:
            # Read student data (admission IDs and print paths)
            student_data = self.read_admission_ids(csv_path)
            
            if not student_data:
                messagebox.showwarning(
                    "No Data Found",
                    "No student data found in the file.\n\n"
                    "Make sure the file contains 'Username' and 'Print Path' columns."
                )
                return
                
            # Confirm before processing
            if not TEST_MODE:
                response = messagebox.askyesno(
                    "Confirm Printing",
                    f"Found {len(student_data)} student(s) to process.\n\n"
                    f"This will print files from the paths specified in the Excel file.\n\n"
                    "Continue?"
                )
                if not response:
                    self.logger.info("User cancelled processing")
                    return
                
            # Process each student
            for idx, student in enumerate(student_data, 1):
                self.stats['processed'] += 1
                admission_id = student['admission_id']
                print_path = student['print_path']
                
                self.logger.info(f"[{idx}/{len(student_data)}] Processing student: {admission_id}")
                self.logger.info(f"  Print path: {print_path}")
                
                # Copy files from the print path specified in Excel
                copied_files, file_count = self.copy_student_files(print_path, admission_id)
                
                # Store file count for billing
                student['files_counted'] = file_count
                
                if not copied_files:
                    self.stats['skipped'] += 1
                    self.logger.warning(f"No files found for {admission_id}")
                    student['files_counted'] = 0  # No files to count
                    continue
                    
                # Print each file (with small delay to prevent printer queue overload)
                total_files_to_print = len(copied_files)
                student_printed = 0
                student_errors = 0
                
                if total_files_to_print > 0:
                    print(f"\n{'=' * 70}")
                    print(f"Printing {total_files_to_print} file(s) for {admission_id}...")
                    print(f"{'=' * 70}\n")
                
                for idx, file_path in enumerate(copied_files, 1):
                    if self.print_file(file_path, file_index=idx, total_files=total_files_to_print):
                        self.stats['printed'] += 1
                        student_printed += 1
                        self.files_to_print.append(file_path)
                        # Small delay between prints to prevent printer queue overload
                        # Especially important when processing many files (100+ students)
                        time.sleep(0.3)  # 300ms delay between prints
                    else:
                        self.stats['errors'] += 1
                        student_errors += 1
                
                if total_files_to_print > 0:
                    print(f"\n✓ Completed {admission_id}: {student_printed} printed, {student_errors} errors\n")
                        
            # Update billing records
            print("\nUpdating billing records...")
            self.logger.info("Updating billing records...")
            self.update_billing_records(student_data)
            print("✓ Billing records updated\n")
            
            # Summary
            print("=" * 70)
            print("PROCESSING COMPLETE")
            print("=" * 70)
            print(f"Students processed: {self.stats['processed']}")
            print(f"Files printed: {self.stats['printed']}")
            print(f"Students skipped: {self.stats['skipped']}")
            print(f"Errors: {self.stats['errors']}")
            print(f"Billing files: {PRINT_COST_FOLDER}")
            print("=" * 70)
            
            self.logger.info("=" * 70)
            self.logger.info("Processing complete")
            self.logger.info(f"Students processed: {self.stats['processed']}")
            self.logger.info(f"Files printed: {self.stats['printed']}")
            self.logger.info(f"Students skipped: {self.stats['skipped']}")
            self.logger.info(f"Errors: {self.stats['errors']}")
            self.logger.info(f"Billing files updated in: {PRINT_COST_FOLDER}")
            self.logger.info("=" * 70)
            
            # Show completion message
            messagebox.showinfo(
                "Printing Complete",
                f"Processing finished!\n\n"
                f"Students processed: {self.stats['processed']}\n"
                f"Files printed: {self.stats['printed']}\n"
                f"Skipped: {self.stats['skipped']}\n"
                f"Errors: {self.stats['errors']}\n\n"
                f"Billing records updated in:\n{PRINT_COST_FOLDER}\n\n"
                f"Log file: {LOG_FILE}"
            )
            
        except Exception as e:
            error_msg = f"Fatal error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            messagebox.showerror("Error", error_msg)
            
    def run(self):
        """Main entry point"""
        csv_path = self.select_csv_file()
        
        if not csv_path:
            self.logger.info("No file selected. Exiting.")
            return
            
        self.process_all(csv_path)

if __name__ == "__main__":
    app = PrintAgent()
    app.run()
