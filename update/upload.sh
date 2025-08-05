#!/usr/bin/env bash

# Random 2hu Stuff Project Upload Script
# Build and upload project to server

set -e  # Exit immediately on any error

# Configuration variables
LOCAL_PROJECT_ROOT="$HOME/repo/random-2hu-stuff"
REMOTE_SERVER="root@38.148.249.102"
REMOTE_TARGET="/var/www/"
FRONTEND_DIR="$LOCAL_PROJECT_ROOT/frontend"
BACKEND_DIR="$LOCAL_PROJECT_ROOT/backend"
DEPLOY_DIR="$LOCAL_PROJECT_ROOT/deploy"

# Color output configuration
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    local deps=("node" "npm" "rsync" "ssh")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            log_error "$dep is not installed"
            exit 1
        fi
    done
    
    log_success "All dependency checks passed"
}

# Test SSH connection
test_ssh_connection() {
    log_info "Testing SSH connection..."
    
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$REMOTE_SERVER" "echo 'SSH connection successful'" 2>/dev/null; then
        log_success "SSH connection test passed"
    else
        log_error "SSH connection failed, please check:"
        echo "  1. SSH key is properly configured"
        echo "  2. Server is reachable"
        echo "  3. User permissions are correct"
        exit 1
    fi
}

# Build frontend
build_frontend() {
    log_info "Building frontend project..."
    
    cd "$FRONTEND_DIR"
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        log_error "Frontend package.json does not exist"
        exit 1
    fi
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm ci --production=false
    
    # Build project
    log_info "Building frontend..."
    npm run build
    
    # Check build result
    if [ ! -d "dist" ]; then
        log_error "Frontend build failed, dist directory does not exist"
        exit 1
    fi
    
    log_success "Frontend build completed"
}

# Prepare backend files
prepare_backend() {
    log_info "Preparing backend files..."
    
    cd "$BACKEND_DIR"
    
    # Check required files
    local required_files=("server.cjs" "package.json")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Backend file does not exist: $file"
            exit 1
        fi
    done
    
    log_success "Backend file check completed"
}

# Create temporary upload directory
create_upload_structure() {
    local temp_dir="/tmp/random-2hu-stuff-upload"
    
    # Clean and create temporary directory
    rm -rf "$temp_dir"
    mkdir -p "$temp_dir/random-2hu-stuff"
    
    # Copy frontend build files (if exists)
    if [ -d "$FRONTEND_DIR/dist" ]; then
        mkdir -p "$temp_dir/random-2hu-stuff/frontend/dist"
        cp -r "$FRONTEND_DIR/dist/"* "$temp_dir/random-2hu-stuff/frontend/dist/"
    fi
    
    # Copy backend files
    mkdir -p "$temp_dir/random-2hu-stuff/backend"
    cp "$BACKEND_DIR/server.cjs" "$temp_dir/random-2hu-stuff/backend/"
    cp "$BACKEND_DIR/package.json" "$temp_dir/random-2hu-stuff/backend/"
    
    # Copy ecosystem.config.js file (if exists)
    if [ -f "$BACKEND_DIR/ecosystem.config.js" ]; then
        cp "$BACKEND_DIR/ecosystem.config.js" "$temp_dir/random-2hu-stuff/backend/"
    fi
    
    # Copy package-lock.json file (if exists)
    if [ -f "$BACKEND_DIR/package-lock.json" ]; then
        cp "$BACKEND_DIR/package-lock.json" "$temp_dir/random-2hu-stuff/backend/"
    fi
    
    # Copy database file (if exists)
    if [ -f "$BACKEND_DIR/random-2hu-stuff.db" ]; then
        cp "$BACKEND_DIR/random-2hu-stuff.db" "$temp_dir/random-2hu-stuff/backend/"
    fi
    
    echo "$temp_dir"
}

# Upload database file only
upload_database_only() {
    log_info "Uploading database file only..."
    
    # Check if database file exists
    if [ ! -f "$BACKEND_DIR/random-2hu-stuff.db" ]; then
        log_error "Database file does not exist: $BACKEND_DIR/random-2hu-stuff.db"
        exit 1
    fi
    
    # Upload database file directly using rsync
    rsync -avzh --progress \
        "$BACKEND_DIR/random-2hu-stuff.db" \
        "$REMOTE_SERVER:$REMOTE_TARGET/random-2hu-stuff/backend/"
    
    log_success "Database file upload completed"
}

# Upload files to server
upload_files() {
    local temp_dir="$1"
    
    log_info "Starting file upload..."
    
    # Upload files using rsync
    if rsync -avz --delete --progress \
        "$temp_dir/random-2hu-stuff/" \
        "$REMOTE_SERVER:$REMOTE_TARGET/random-2hu-stuff/"; then
        log_success "File upload completed successfully"
        return 0
    else
        log_error "File upload failed"
        return 1
    fi
}

# Install backend dependencies on remote server
install_remote_dependencies() {
    log_info "Installing backend dependencies on remote server..."
    
    if ssh "$REMOTE_SERVER" "cd $REMOTE_TARGET/random-2hu-stuff/backend && npm ci --production"; then
        log_success "Backend dependencies installed successfully"
        return 0
    else
        log_error "Failed to install backend dependencies"
        return 1
    fi
}

# Restart PM2 process on remote server
restart_pm2_on_remote() {
    log_info "Restarting PM2 process on remote server..."
    
    if ssh "$REMOTE_SERVER" "cd $REMOTE_TARGET/random-2hu-stuff/backend && pm2 restart ecosystem.config.js --env production"; then
        log_success "PM2 process restarted successfully"
        return 0
    else
        log_error "Failed to restart PM2 process"
        return 1
    fi
}

# Restart services on remote server
restart_remote_services() {
    log_info "Restarting services on remote server..."
    
    # Restart PM2 service
    if ssh "$REMOTE_SERVER" "cd $REMOTE_TARGET/random-2hu-stuff/backend && pm2 restart ecosystem.config.js"; then
        log_success "PM2 service restarted successfully"
    else
        log_warning "Failed to restart PM2 service"
    fi
    
    # Restart nginx service
    if ssh "$REMOTE_SERVER" "sudo systemctl reload nginx"; then
        log_success "nginx service reloaded successfully"
    else
        log_warning "Failed to reload nginx service"
    fi
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    sleep 5  # Wait for services to start
    
    # Check HTTP response
    if curl -f -s "https://random-2hu-stuff.randomneet.me/health" > /dev/null; then
        log_success "Health check passed"
    else
        log_warning "Health check failed, please manually check service status"
    fi
}

# Clean up temporary files
cleanup() {
    local temp_dir="$1"
    if [ -d "$temp_dir" ]; then
        rm -rf "$temp_dir"
        log_info "Temporary file cleanup completed"
    fi
}

# Display upload information
show_upload_info() {
    log_info "Upload information:"
    echo "=========================="
    echo "Local project: $LOCAL_PROJECT_ROOT"
    echo "Remote server: $REMOTE_SERVER"
    echo "Remote path: $REMOTE_TARGET/random-2hu-stuff/"
    echo "Frontend URL: https://random-2hu-stuff.randomneet.me"
    echo "Backend API: https://random-2hu-stuff.randomneet.me/api"
    echo "=========================="
}

# Main function
main() {
    log_info "Starting Random 2hu Stuff project upload..."
    show_upload_info
    echo ""
    
    # Confirm upload
    read -p "Are you sure you want to upload to production server? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Upload cancelled"
        exit 0
    fi
    
    local temp_dir
    
    # Execute upload steps
    check_dependencies
    test_ssh_connection
    build_frontend
    prepare_backend
    
    log_info "Creating upload directory structure..."
    temp_dir=$(create_upload_structure)
    
    # Display included file information
    if [ -d "$FRONTEND_DIR/dist" ]; then
        log_info "✓ Frontend files included"
    else
        log_warning "✗ Frontend dist directory not found, skipping frontend files"
    fi
    
    if [ -f "$BACKEND_DIR/package-lock.json" ]; then
        log_info "✓ Backend dependency lock file included"
    else
        log_info "✗ Backend package-lock.json file not found"
    fi
    
    if [ -f "$BACKEND_DIR/random-2hu-stuff.db" ]; then
        local db_size=$(du -h "$BACKEND_DIR/random-2hu-stuff.db" | cut -f1)
        log_info "✓ Database file included (size: $db_size)"
    else
        log_warning "✗ Database file does not exist, will not upload database"
    fi
    
    # Set cleanup trap
    trap "cleanup '$temp_dir'" EXIT
    
    upload_files "$temp_dir"
    install_remote_dependencies
    restart_remote_services
    health_check
    
    log_success "Upload completed!"
    log_info "Website URL: https://random-2hu-stuff.randomneet.me"
}

# Handle command line arguments
case "${1:-}" in
    "build-only")
        log_info "Building project only..."
        check_dependencies
        build_frontend
        prepare_backend
        log_success "Build completed"
        ;;
    "upload-only")
        log_info "Uploading files only (skipping build)..."
        check_dependencies
        temp_dir=$(create_upload_structure)
        trap "cleanup '$temp_dir'" EXIT
        upload_files "$temp_dir"
        log_success "Upload completed"
        ;;
    "database-only")
        log_info "Uploading database file only..."
        check_dependencies
        test_ssh_connection
        upload_database_only
        restart_remote_services
        log_success "Database upload and service restart completed"
        ;;
    "")
        main
        ;;
    *)
        echo "Usage: $0 [build-only|upload-only|database-only]"
        echo "  No arguments: Complete build and upload"
        echo "  build-only: Build project only"
        echo "  upload-only: Upload files only"
        echo "  database-only: Upload database file only"
        exit 1
        ;;
esac
