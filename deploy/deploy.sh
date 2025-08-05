#!/usr/bin/env bash

# Random 2hu Stuff Project Deployment Script
# Used for deploying frontend and backend to production environment

set -e  # Exit immediately on any error

# Configuration variables
PROJECT_ROOT="/home/howl/repo/random-2hu-stuff"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
DEPLOY_TARGET="/var/www/random-2hu-stuff"
NGINX_CONFIG="/etc/nginx/sites-available/random-2hu-stuff"
NGINX_ENABLED="/etc/nginx/sites-enabled/random-2hu-stuff"
PM2_APP_NAME="random-2hu-stuff-backend"

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

# Check if running as root user
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script requires root privileges to run"
        log_info "Please use: sudo $0"
        exit 1
    fi
}

# Check if required commands exist
check_dependencies() {
    log_info "Checking dependencies..."
    
    local deps=("node" "npm" "nginx" "pm2")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            log_error "$dep is not installed"
            exit 1
        fi
    done
    
    log_success "All dependency checks passed"
}

# Stop existing services
stop_services() {
    log_info "Stopping existing services..."
    
    # Stop PM2 processes
    if pm2 list | grep -q "$PM2_APP_NAME"; then
        pm2 stop "$PM2_APP_NAME" || true
        pm2 delete "$PM2_APP_NAME" || true
        log_success "Backend service stopped"
    fi
    
    # Reload nginx configuration
    nginx -t && systemctl reload nginx
    log_success "Nginx configuration reloaded"
}

# Build frontend
build_frontend() {
    log_info "Building frontend project..."
    
    cd "$FRONTEND_DIR"
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm ci --production=false
    
    # Build project
    log_info "Building frontend..."
    npm run build
    
    log_success "Frontend build completed"
}

# Deploy frontend
deploy_frontend() {
    log_info "Deploying frontend..."
    
    # Create deployment directory
    mkdir -p "$DEPLOY_TARGET/frontend"
    
    # Copy built files
    if [ -d "$FRONTEND_DIR/dist" ]; then
        cp -r "$FRONTEND_DIR/dist/"* "$DEPLOY_TARGET/frontend/"
        log_success "Frontend files deployed"
    else
        log_error "Frontend build directory does not exist: $FRONTEND_DIR/dist"
        exit 1
    fi
    
    # Set correct permissions
    chown -R www-data:www-data "$DEPLOY_TARGET/frontend"
    chmod -R 755 "$DEPLOY_TARGET/frontend"
}

# Deploy backend
deploy_backend() {
    log_info "Deploying backend..."
    
    # Create backend directory
    mkdir -p "$DEPLOY_TARGET/backend"
    
    # Copy backend files
    cp "$BACKEND_DIR/server.cjs" "$DEPLOY_TARGET/backend/"
    cp "$BACKEND_DIR/package.json" "$DEPLOY_TARGET/backend/"
    
    # Copy database file (if exists)
    if [ -f "$BACKEND_DIR/mmd.db" ]; then
        cp "$BACKEND_DIR/mmd.db" "$DEPLOY_TARGET/backend/"
        log_info "Database file copied"
    fi
    
    # Copy Python scripts
    cp "$BACKEND_DIR"/*.py "$DEPLOY_TARGET/backend/" 2>/dev/null || true
    
    cd "$DEPLOY_TARGET/backend"
    
    # Install backend dependencies
    log_info "Installing backend dependencies..."
    npm ci --production
    
    # Set permissions
    chown -R www-data:www-data "$DEPLOY_TARGET/backend"
    chmod 755 "$DEPLOY_TARGET/backend/server.cjs"
    
    log_success "Backend deployment completed"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    cd "$DEPLOY_TARGET/backend"
    
    # Start backend service
    pm2 start server.cjs --name "$PM2_APP_NAME" --user www-data
    pm2 save
    pm2 startup
    
    log_success "Backend service started"
    
    # Test service
    sleep 3
    if curl -f http://localhost:3000/health &>/dev/null; then
        log_success "Backend service health check passed"
    else
        log_warning "Backend service health check failed, please check logs"
    fi
}

# Deploy Nginx configuration
deploy_nginx_config() {
    log_info "Deploying Nginx configuration..."
    
    local nginx_source="$DEPLOY_DIR/nginx.conf"
    
    if [ -f "$nginx_source" ]; then
        # Backup existing configuration
        if [ -f "$NGINX_CONFIG" ]; then
            cp "$NGINX_CONFIG" "$NGINX_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
            log_info "Existing Nginx configuration backed up"
        fi
        
        # Copy new configuration
        cp "$nginx_source" "$NGINX_CONFIG"
        
        # Create symbolic link to enable site
        if [ ! -L "$NGINX_ENABLED" ]; then
            ln -sf "$NGINX_CONFIG" "$NGINX_ENABLED"
            log_info "Nginx site enabled"
        fi
        
        # Test configuration
        if nginx -t; then
            systemctl reload nginx
            log_success "Nginx configuration deployed and reloaded"
        else
            log_error "Nginx configuration test failed"
            # Restore backup
            if [ -f "$NGINX_CONFIG.backup.$(date +%Y%m%d_%H%M%S)" ]; then
                cp "$NGINX_CONFIG.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONFIG"
                nginx -t && systemctl reload nginx
                log_info "Backup configuration restored"
            fi
            exit 1
        fi
    else
        log_warning "Nginx configuration file does not exist: $nginx_source"
    fi
}

# Check Nginx configuration
check_nginx_config() {
    log_info "Checking Nginx configuration..."
    
    if [ -f "$NGINX_CONFIG" ]; then
        log_success "Nginx configuration file exists"
    else
        log_warning "Nginx configuration file does not exist: $NGINX_CONFIG"
        log_info "Please ensure Nginx is properly configured"
    fi
    
    # Test configuration
    if nginx -t; then
        log_success "Nginx configuration test passed"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
}

# Create backup
create_backup() {
    if [ -d "$DEPLOY_TARGET" ]; then
        local backup_dir="/var/backups/random-2hu-stuff-$(date +%Y%m%d_%H%M%S)"
        log_info "Creating backup: $backup_dir"
        mkdir -p "/var/backups"
        cp -r "$DEPLOY_TARGET" "$backup_dir"
        log_success "Backup created"
    fi
}

# Show status
show_status() {
    log_info "Deployment status:"
    echo "=========================="
    
    # PM2 status
    echo "PM2 process status:"
    pm2 list | grep "$PM2_APP_NAME" || echo "No PM2 process found"
    
    # Nginx status
    echo ""
    echo "Nginx status:"
    systemctl is-active nginx
    
    # Port check
    echo ""
    echo "Port listening status:"
    netstat -tlnp | grep ":3000" || echo "Port 3000 not listening"
    netstat -tlnp | grep ":80\|:443" || echo "HTTP/HTTPS ports not listening"
    
    echo "=========================="
}

# Main function
main() {
    log_info "Starting deployment of Random 2hu Stuff project..."
    echo "Project path: $PROJECT_ROOT"
    echo "Deploy target: $DEPLOY_TARGET"
    echo ""
    
    # Confirm deployment
    read -p "Are you sure you want to deploy to production environment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    # Execute deployment steps
    check_root
    check_dependencies
    create_backup
    deploy_nginx_config
    stop_services
    build_frontend
    deploy_frontend
    deploy_backend
    check_nginx_config
    start_services
    show_status
    
    log_success "Deployment completed!"
    log_info "Frontend URL: https://random-2hu-stuff.randomneet.me"
    log_info "Backend API: https://random-2hu-stuff.randomneet.me/api"
}

# Handle command line arguments
case "${1:-}" in
    "frontend")
        log_info "Deploying frontend only..."
        check_root
        build_frontend
        deploy_frontend
        log_success "Frontend deployment completed"
        ;;
    "backend")
        log_info "Deploying backend only..."
        check_root
        stop_services
        deploy_backend
        start_services
        log_success "Backend deployment completed"
        ;;
    "nginx")
        log_info "Deploying Nginx configuration only..."
        check_root
        deploy_nginx_config
        log_success "Nginx configuration deployment completed"
        ;;
    "status")
        show_status
        ;;
    "")
        main
        ;;
    *)
        echo "Usage: $0 [frontend|backend|nginx|status]"
        echo "  No arguments: Full deployment"
        echo "  frontend: Deploy frontend only"
        echo "  backend: Deploy backend only"
        echo "  nginx: Deploy Nginx configuration only"
        echo "  status: Show status"
        exit 1
        ;;
esac
