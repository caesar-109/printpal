#!/bin/bash

# Colors for output1
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Starting Database Health Check..."

# Check if SQLite database file exists
check_db_exists() {
    if [ -f "instance/print_requests.db" ]; then
        echo -e "${GREEN}✓ Database file exists${NC}"
        return 0
    else
        echo -e "${RED}✗ Database file not found!${NC}"
        return 1
    fi
}

# Check database file permissions
check_db_permissions() {
    if [ -r "instance/print_requests.db" ] && [ -w "instance/print_requests.db" ]; then
        echo -e "${GREEN}✓ Database file permissions are correct${NC}"
        return 0
    else
        echo -e "${RED}✗ Incorrect database file permissions!${NC}"
        return 1
    fi
}

# Check database integrity using SQLite
check_db_integrity() {
    echo "Checking database integrity..."
    if sqlite3 instance/print_requests.db "PRAGMA integrity_check;" | grep -q "ok"; then
        echo -e "${GREEN}✓ Database integrity check passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Database integrity check failed!${NC}"
        return 1
    fi
}

# Check critical tables exist
check_tables() {
    local tables=("users" "print_requests" "system_status")
    local missing_tables=()
    
    for table in "${tables[@]}"; do
        if ! sqlite3 instance/print_requests.db ".tables" | grep -q "$table"; then
            missing_tables+=("$table")
        fi
    done
    
    if [ ${#missing_tables[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ All required tables exist${NC}"
        return 0
    else
        echo -e "${RED}✗ Missing tables: ${missing_tables[*]}${NC}"
        return 1
    fi
}

# Check for faculty account
check_faculty_account() {
    if sqlite3 instance/print_requests.db "SELECT COUNT(*) FROM users WHERE role='faculty';" | grep -q "1"; then
        echo -e "${GREEN}✓ Faculty account exists${NC}"
        return 0
    else
        echo -e "${RED}✗ No faculty account found!${NC}"
        return 1
    fi
}

# Check data consistency
check_data_consistency() {
    # Check for orphaned print requests
    orphaned=$(sqlite3 instance/print_requests.db \
        "SELECT COUNT(*) FROM print_requests WHERE user_id NOT IN (SELECT id FROM users);")
    
    if [ "$orphaned" -eq 0 ]; then
        echo -e "${GREEN}✓ No orphaned print requests found${NC}"
    else
        echo -e "${RED}✗ Found $orphaned orphaned print requests!${NC}"
        return 1
    fi
    
    # Check for invalid status values
    invalid_status=$(sqlite3 instance/print_requests.db \
        "SELECT COUNT(*) FROM print_requests WHERE status NOT IN ('pending', 'printed', 'cancelled', 'expired');")
    
    if [ "$invalid_status" -eq 0 ]; then
        echo -e "${GREEN}✓ All print request statuses are valid${NC}"
    else
        echo -e "${RED}✗ Found $invalid_status requests with invalid status!${NC}"
        return 1
    fi
    
    return 0
}

# Check database size and growth
check_db_size() {
    local size=$(du -h "instance/print_requests.db" | cut -f1)
    echo -e "${YELLOW}ℹ Database size: $size${NC}"
    
    # Optional: Add warning if size exceeds threshold
    if [ $(du -b "instance/print_requests.db" | cut -f1) -gt 104857600 ]; then # 100MB
        echo -e "${YELLOW}⚠ Warning: Database size exceeds 100MB${NC}"
    fi
}

# Create backup if it doesn't exist today
create_backup() {
    local backup_dir="backups"
    local date=$(date +%Y%m%d)
    local backup_file="${backup_dir}/print_requests_${date}.db"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$backup_dir"
    
    # Create backup if it doesn't exist for today
    if [ ! -f "$backup_file" ]; then
        cp "instance/print_requests.db" "$backup_file"
        echo -e "${GREEN}✓ Created new backup: $backup_file${NC}"
    else
        echo -e "${YELLOW}ℹ Today's backup already exists${NC}"
    fi
}

# Run all checks
main() {
    local failed=0
    
    check_db_exists || failed=1
    check_db_permissions || failed=1
    check_db_integrity || failed=1
    check_tables || failed=1
    check_faculty_account || failed=1
    check_data_consistency || failed=1
    check_db_size
    create_backup
    
    echo "----------------------------------------"
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}✅ All database checks passed!${NC}"
    else
        echo -e "${RED}❌ Some checks failed! Please review the issues above.${NC}"
    fi
}

# Run the script
main 
