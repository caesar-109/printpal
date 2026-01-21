"""
Helper script to create a test CSV/Excel file matching the web app export format
The Excel file will have multiple sheets (like the real export)
"""
import csv
import pandas as pd
from datetime import datetime

# Create test data grouped by branch (matching web app export format)
test_data_cse_a = [
    {
        'Date': datetime.now().strftime('%d-%m-%Y'),
        'Student Name': 'Test Student 1',
        'Semester': 'S3',
        'Branch': 'CSE-A',
        'Username': 'student1'  # This is the admission_id
    },
    {
        'Date': datetime.now().strftime('%d-%m-%Y'),
        'Student Name': 'Test Student 2',
        'Semester': 'S4',
        'Branch': 'CSE-A',
        'Username': 'student2'
    }
]

test_data_cse_b = [
    {
        'Date': datetime.now().strftime('%d-%m-%Y'),
        'Student Name': 'Test Student 3',
        'Semester': 'S5',
        'Branch': 'CSE-B',
        'Username': 'student3'  # This is the admission_id
    }
]

test_data_ai_ds = [
    {
        'Date': datetime.now().strftime('%d-%m-%Y'),
        'Student Name': 'Test Student 4',
        'Semester': 'S6',
        'Branch': 'AI&DS',
        'Username': 'student4'  # This is the admission_id
    }
]

# Create CSV file (single sheet, all students combined)
csv_filename = 'test_print_requests.csv'
all_data = test_data_cse_a + test_data_cse_b + test_data_ai_ds
with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['Date', 'Student Name', 'Semester', 'Branch', 'Username'])
    writer.writeheader()
    writer.writerows(all_data)

print(f"✓ Created CSV file: {csv_filename}")

# Create Excel file with MULTIPLE SHEETS (matching web app export format)
excel_filename = 'test_print_requests.xlsx'

with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
    # Sheet 1: CSE-A
    df_cse_a = pd.DataFrame(test_data_cse_a)
    df_cse_a.to_excel(writer, sheet_name='CSE-A', index=False, startrow=2)
    worksheet = writer.sheets['CSE-A']
    worksheet.merge_range('A1:E1', 'CSE-A - S3', writer.book.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#f0f0f0'
    }))
    
    # Sheet 2: CSE-B
    df_cse_b = pd.DataFrame(test_data_cse_b)
    df_cse_b.to_excel(writer, sheet_name='CSE-B', index=False, startrow=2)
    worksheet = writer.sheets['CSE-B']
    worksheet.merge_range('A1:E1', 'CSE-B - S5', writer.book.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#f0f0f0'
    }))
    
    # Sheet 3: AI&DS
    df_ai_ds = pd.DataFrame(test_data_ai_ds)
    df_ai_ds.to_excel(writer, sheet_name='AI&DS', index=False, startrow=2)
    worksheet = writer.sheets['AI&DS']
    worksheet.merge_range('A1:E1', 'AI&DS - S6', writer.book.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#f0f0f0'
    }))

print(f"✓ Created Excel file: {excel_filename}")
print(f"  - Sheet 1: CSE-A (2 students)")
print(f"  - Sheet 2: CSE-B (1 student)")
print(f"  - Sheet 3: AI&DS (1 student)")
print(f"  - Total: 4 students across 3 sheets")
print("\nYou can now use these files to test PrintAgent.exe")
print("The Excel file tests multi-sheet reading functionality!")
