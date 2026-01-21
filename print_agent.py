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
        self.logger.info(f"Work folder ready: {LOCAL_WORK_FOLDER}")
        
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
        """Read admission IDs (usernames) from CSV/Excel file"""
        admission_ids = []
        
        try:
            # Handle Excel files
            if csv_path.lower().endswith('.xlsx'):
                try:
                    import pandas as pd
                    
                    # Read ALL sheets from Excel file
                    excel_file = pd.ExcelFile(csv_path)
                    sheet_names = excel_file.sheet_names
                    self.logger.info(f"Found {len(sheet_names)} sheet(s): {', '.join(sheet_names)}")
                    
                    all_admission_ids = []
                    
                    # Process each sheet
                    for sheet_name in sheet_names:
                        # Skip first 2 rows (merged header + empty row), use row 2 as headers
                        # This matches the web app export format: startrow=2
                        df = pd.read_excel(csv_path, sheet_name=sheet_name, header=2)
                        self.logger.info(f"Processing sheet '{sheet_name}' - columns: {list(df.columns)}")
                        
                        sheet_ids = []
                        
                        # Try to find Username column (since username = admission_id)
                        if 'Username' in df.columns:
                            sheet_ids = df['Username'].dropna().astype(str).tolist()
                            self.logger.info(f"  Found 'Username' column with {len(sheet_ids)} entries")
                        elif 'admission_id' in df.columns:
                            sheet_ids = df['admission_id'].dropna().astype(str).tolist()
                            self.logger.info(f"  Found 'admission_id' column with {len(sheet_ids)} entries")
                        elif len(df.columns) > 0:
                            # Use first column as fallback
                            sheet_ids = df.iloc[:, 0].dropna().astype(str).tolist()
                            self.logger.info(f"  Using first column with {len(sheet_ids)} entries")
                        else:
                            self.logger.warning(f"  No columns found in sheet '{sheet_name}', skipping")
                            continue
                        
                        # Add to combined list
                        all_admission_ids.extend(sheet_ids)
                        self.logger.info(f"  Added {len(sheet_ids)} IDs from sheet '{sheet_name}'")
                    
                    # Remove duplicates while preserving order
                    admission_ids = []
                    seen = set()
                    for id in all_admission_ids:
                        id_clean = id.strip()
                        if id_clean and id_clean not in seen:
                            admission_ids.append(id_clean)
                            seen.add(id_clean)
                    
                    self.logger.info(f"Total unique admission IDs across all sheets: {len(admission_ids)}")
                    
                    if not admission_ids:
                        raise ValueError("No admission IDs found in any sheet")
                        
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
                    
                    # Try to find Username column
                    if 'Username' in fieldnames:
                        admission_ids = [row['Username'] for row in reader if row.get('Username')]
                        self.logger.info(f"Found 'Username' column with {len(admission_ids)} entries")
                    elif 'admission_id' in fieldnames:
                        admission_ids = [row['admission_id'] for row in reader if row.get('admission_id')]
                        self.logger.info(f"Found 'admission_id' column with {len(admission_ids)} entries")
                    else:
                        # Read first column
                        f.seek(0)
                        reader = csv.reader(f)
                        next(reader)  # Skip header
                        admission_ids = [row[0] for row in reader if row and row[0]]
                        self.logger.info(f"Using first column with {len(admission_ids)} entries")
                        
        except Exception as e:
            self.logger.error(f"Error reading file: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Failed to read file:\n{str(e)}")
            return []
            
        # Clean and validate IDs
        admission_ids = [id.strip() for id in admission_ids if id and id.strip()]
        self.logger.info(f"Total valid admission IDs: {len(admission_ids)}")
        return admission_ids
        
    def copy_student_files(self, admission_id):
        """Copy all files from student's print folder to local work folder"""
        # Construct path: base_path/admission_id/print/
        student_folder = self.base_path / admission_id / "print"
        copied_files = []
        
        try:
            if not student_folder.exists():
                self.logger.warning(f"Folder not found: {student_folder}")
                return copied_files
                
            if not student_folder.is_dir():
                self.logger.warning(f"Path is not a directory: {student_folder}")
                return copied_files
                
            # Check read access
            try:
                test_access = os.access(str(student_folder), os.R_OK)
                if not test_access:
                    self.logger.warning(f"No read access: {student_folder}")
                    return copied_files
            except Exception as e:
                self.logger.warning(f"Access check failed: {str(e)}")
                
            # Get all files
            files = list(student_folder.glob("*"))
            files = [f for f in files if f.is_file()]
            
            if not files:
                self.logger.info(f"Empty folder: {student_folder}")
                return copied_files
                
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
            
        return copied_files
        
    def print_file(self, file_path):
        """Print a file silently without opening it"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return False
            
        ext = file_path.suffix.lower()
        file_str = str(file_path.resolve())  # Get absolute path
        
        # Check if file type is printable
        if ext not in PRINTABLE_EXTENSIONS:
            self.logger.warning(f"Unknown file type: {ext}, attempting silent print anyway")
        
        try:
            if ext == '.pdf':
                # Try SumatraPDF first (truly silent)
                if Path(SUMATRA_PDF_PATH).exists():
                    self.logger.info(f"Using SumatraPDF for: {file_path.name}")
                    result = subprocess.run(
                        [SUMATRA_PDF_PATH, '-print-to-default', '-silent', file_str],
                        check=False,
                        timeout=30,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    if result.returncode == 0:
                        self.logger.info(f"✓ Sent to printer: {file_path.name}")
                        return True
                    else:
                        self.logger.warning(f"SumatraPDF failed, trying PowerShell: {file_path.name}")
                
                # Fallback: PowerShell silent print for PDF
                ps_command = f'Start-Process -FilePath "{file_str}" -Verb Print -WindowStyle Hidden'
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    check=False,
                    timeout=30,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0:
                    self.logger.info(f"✓ Sent to printer: {file_path.name}")
                    return True
                else:
                    self.logger.warning(f"Print failed: {file_path.name}")
                    return False
                    
            elif ext in {'.doc', '.docx', '.txt', '.rtf', '.xps'}:
                # Use PowerShell silent print
                ps_command = f'Start-Process -FilePath "{file_str}" -Verb Print -WindowStyle Hidden'
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    check=False,
                    timeout=30,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0:
                    self.logger.info(f"✓ Sent to printer: {file_path.name}")
                    return True
                else:
                    self.logger.warning(f"Print failed: {file_path.name}")
                    return False
                    
            elif ext in {'.jpg', '.jpeg', '.png', '.bmp'}:
                # Images - PowerShell silent print
                ps_command = f'Start-Process -FilePath "{file_str}" -Verb Print -WindowStyle Hidden'
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    check=False,
                    timeout=30,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0:
                    self.logger.info(f"✓ Sent to printer: {file_path.name}")
                    return True
                else:
                    self.logger.warning(f"Print failed: {file_path.name}")
                    return False
                    
            else:
                # Unknown type - try PowerShell silent print
                self.logger.warning(f"Unknown file type: {ext}, attempting silent print")
                ps_command = f'Start-Process -FilePath "{file_str}" -Verb Print -WindowStyle Hidden'
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    check=False,
                    timeout=30,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0:
                    self.logger.info(f"✓ Sent to printer: {file_path.name}")
                    return True
                else:
                    self.logger.warning(f"Print failed: {file_path.name}")
                    return False
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Print timeout: {file_path.name}")
            return False
        except Exception as e:
            self.logger.error(f"Error printing {file_path.name}: {str(e)}")
            return False
            
    def process_all(self, csv_path):
        """Main processing function"""
        self.logger.info("=" * 70)
        self.logger.info("PrintAgent started")
        self.logger.info(f"CSV/Excel file: {csv_path}")
        self.logger.info(f"Base path: {self.base_path}")
        self.logger.info(f"Mode: {'TEST' if TEST_MODE else 'PRODUCTION'}")
        self.logger.info("=" * 70)
        
        try:
            # Read admission IDs
            admission_ids = self.read_admission_ids(csv_path)
            
            if not admission_ids:
                messagebox.showwarning(
                    "No IDs Found",
                    "No admission IDs (usernames) found in the file.\n\n"
                    "Make sure the file contains a 'Username' column."
                )
                return
                
            # Confirm before processing
            if not TEST_MODE:
                response = messagebox.askyesno(
                    "Confirm Printing",
                    f"Found {len(admission_ids)} student(s) to process.\n\n"
                    f"This will print files from:\n{self.base_path}\n\n"
                    "Continue?"
                )
                if not response:
                    self.logger.info("User cancelled processing")
                    return
                
            # Process each student
            for idx, admission_id in enumerate(admission_ids, 1):
                self.stats['processed'] += 1
                self.logger.info(f"[{idx}/{len(admission_ids)}] Processing student: {admission_id}")
                
                # Copy files
                copied_files = self.copy_student_files(admission_id)
                
                if not copied_files:
                    self.stats['skipped'] += 1
                    self.logger.warning(f"No files found for {admission_id}")
                    continue
                    
                # Print each file (with small delay to prevent printer queue overload)
                for file_path in copied_files:
                    if self.print_file(file_path):
                        self.stats['printed'] += 1
                        self.files_to_print.append(file_path)
                        # Small delay between prints to prevent printer queue overload
                        # Especially important when processing many files (100+ students)
                        time.sleep(0.3)  # 300ms delay between prints
                    else:
                        self.stats['errors'] += 1
                        
            # Summary
            self.logger.info("=" * 70)
            self.logger.info("Processing complete")
            self.logger.info(f"Students processed: {self.stats['processed']}")
            self.logger.info(f"Files printed: {self.stats['printed']}")
            self.logger.info(f"Students skipped: {self.stats['skipped']}")
            self.logger.info(f"Errors: {self.stats['errors']}")
            self.logger.info("=" * 70)
            
            # Show completion message
            messagebox.showinfo(
                "Printing Complete",
                f"Processing finished!\n\n"
                f"Students processed: {self.stats['processed']}\n"
                f"Files printed: {self.stats['printed']}\n"
                f"Skipped: {self.stats['skipped']}\n"
                f"Errors: {self.stats['errors']}\n\n"
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
