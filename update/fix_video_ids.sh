#!/usr/bin/env bash

# ========================================================================
# Video IDs Fix Script Runner for random-2hu-stuff Database
# ========================================================================
# Purpose: Safely fix video table IDs with automatic backup
# Author: Generated script for random-2hu-stuff project
# ========================================================================

set -e # Exit on any error

# Configuration
DB_FILE="random-2hu-stuff.db"
BACKUP_FILE="${DB_FILE}.bak"
SQL_SCRIPT="fix_video_ids.sql"
LOG_FILE="fix_video_ids_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
	local color=$1
	local message=$2
	echo -e "${color}${message}${NC}"
}

# Function to log messages
log_message() {
	local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
	echo "$message" | tee -a "$LOG_FILE"
}

# Check if we're in the correct directory
if [ ! -f "$DB_FILE" ]; then
	print_message $RED "Error: Database file '$DB_FILE' not found!"
	print_message $YELLOW "Please run this script from the backend directory."
	exit 1
fi

if [ ! -f "$SQL_SCRIPT" ]; then
	print_message $RED "Error: SQL script '$SQL_SCRIPT' not found!"
	print_message $YELLOW "Please make sure the script is in the same directory or update directory."
	exit 1
fi

print_message $BLUE "=========================================="
print_message $BLUE "Random 2hu Stuff - Video IDs Fix Script"
print_message $BLUE "=========================================="

# Create log file
log_message "Starting video IDs fix process"

# Check database integrity before backup
print_message $YELLOW "Checking database integrity..."
if ! sqlite3 "$DB_FILE" "PRAGMA integrity_check;" >/dev/null 2>&1; then
	print_message $RED "Error: Database integrity check failed!"
	log_message "ERROR: Database integrity check failed"
	exit 1
fi
print_message $GREEN "Database integrity check passed."
log_message "Database integrity check passed"

# Create backup
print_message $YELLOW "Creating backup: $BACKUP_FILE"
if [ -f "$BACKUP_FILE" ]; then
	print_message $YELLOW "Backup file already exists. Creating timestamped backup..."
	BACKUP_FILE="${DB_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
fi

cp "$DB_FILE" "$BACKUP_FILE"
if [ $? -eq 0 ]; then
	print_message $GREEN "Backup created successfully: $BACKUP_FILE"
	log_message "Backup created: $BACKUP_FILE"
else
	print_message $RED "Error: Failed to create backup!"
	log_message "ERROR: Failed to create backup"
	exit 1
fi

# Get current statistics
print_message $YELLOW "Getting current database statistics..."
BEFORE_STATS=$(sqlite3 "$DB_FILE" "
SELECT 'Videos: ' || COUNT(*) || ', ID range: ' || MIN(id) || '-' || MAX(id) 
FROM videos;
")
print_message $BLUE "Before: $BEFORE_STATS"
log_message "Before modification: $BEFORE_STATS"

# Ask for confirmation
print_message $YELLOW "Ready to fix video IDs. This will:"
print_message $YELLOW "- Reorganize all video IDs to be consecutive"
print_message $YELLOW "- Start IDs from 1"
print_message $YELLOW "- Preserve all data and relationships"
echo
read -p "Do you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
	print_message $YELLOW "Operation cancelled."
	log_message "Operation cancelled by user"
	exit 0
fi

# Execute the SQL script
print_message $YELLOW "Executing video IDs fix script..."
log_message "Starting SQL script execution"

if sqlite3 "$DB_FILE" <"$SQL_SCRIPT" 2>&1 | tee -a "$LOG_FILE"; then
	print_message $GREEN "SQL script executed successfully!"
	log_message "SQL script executed successfully"
else
	print_message $RED "Error: SQL script execution failed!"
	log_message "ERROR: SQL script execution failed"

	# Restore backup
	print_message $YELLOW "Restoring backup..."
	cp "$BACKUP_FILE" "$DB_FILE"
	print_message $YELLOW "Database restored from backup."
	log_message "Database restored from backup due to error"
	exit 1
fi

# Verify results
print_message $YELLOW "Verifying results..."
AFTER_STATS=$(sqlite3 "$DB_FILE" "
SELECT 'Videos: ' || COUNT(*) || ', ID range: ' || MIN(id) || '-' || MAX(id) 
FROM videos;
")
print_message $BLUE "After: $AFTER_STATS"
log_message "After modification: $AFTER_STATS"

# Final integrity check
print_message $YELLOW "Performing final integrity check..."
if sqlite3 "$DB_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
	print_message $GREEN "Final integrity check passed."
	log_message "Final integrity check passed"
else
	print_message $RED "Warning: Final integrity check failed!"
	log_message "WARNING: Final integrity check failed"
fi

print_message $GREEN "=========================================="
print_message $GREEN "Video IDs fix completed successfully!"
print_message $GREEN "=========================================="
print_message $BLUE "Backup saved as: $BACKUP_FILE"
print_message $BLUE "Log saved as: $LOG_FILE"
log_message "Process completed successfully"

# Optional: Clean up old backup files (keep only last 5)
BACKUP_COUNT=$(ls -1 ${DB_FILE}.bak* 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 5 ]; then
	print_message $YELLOW "Cleaning up old backup files (keeping last 5)..."
	ls -t ${DB_FILE}.bak* | tail -n +6 | xargs rm -f
	log_message "Cleaned up old backup files"
fi

print_message $GREEN "All operations completed successfully!"

