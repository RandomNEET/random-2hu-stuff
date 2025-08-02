#!/usr/bin/env bash

# Random 2hu Stuff 项目部署脚本
# 用于部署前端和后端到生产环境

set -e  # 遇到错误立即退出

# 配置变量
PROJECT_ROOT="/home/howl/repo/random-2hu-stuff"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
DEPLOY_TARGET="/var/www/random-2hu-stuff"
NGINX_CONFIG="/etc/nginx/sites-available/random-2hu-stuff"
NGINX_ENABLED="/etc/nginx/sites-enabled/random-2hu-stuff"
PM2_APP_NAME="random-2hu-stuff-backend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        log_info "请使用: sudo $0"
        exit 1
    fi
}

# 检查必要的命令是否存在
check_dependencies() {
    log_info "检查依赖..."
    
    local deps=("node" "npm" "nginx" "pm2")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            log_error "$dep 未安装"
            exit 1
        fi
    done
    
    log_success "所有依赖检查通过"
}

# 停止现有服务
stop_services() {
    log_info "停止现有服务..."
    
    # 停止PM2进程
    if pm2 list | grep -q "$PM2_APP_NAME"; then
        pm2 stop "$PM2_APP_NAME" || true
        pm2 delete "$PM2_APP_NAME" || true
        log_success "已停止后端服务"
    fi
    
    # 重新加载nginx配置
    nginx -t && systemctl reload nginx
    log_success "已重新加载Nginx配置"
}

# 构建前端
build_frontend() {
    log_info "构建前端项目..."
    
    cd "$FRONTEND_DIR"
    
    # 安装依赖
    log_info "安装前端依赖..."
    npm ci --production=false
    
    # 构建项目
    log_info "构建前端..."
    npm run build
    
    log_success "前端构建完成"
}

# 部署前端
deploy_frontend() {
    log_info "部署前端..."
    
    # 创建部署目录
    mkdir -p "$DEPLOY_TARGET/frontend"
    
    # 复制构建后的文件
    if [ -d "$FRONTEND_DIR/dist" ]; then
        cp -r "$FRONTEND_DIR/dist/"* "$DEPLOY_TARGET/frontend/"
        log_success "前端文件部署完成"
    else
        log_error "前端构建目录不存在: $FRONTEND_DIR/dist"
        exit 1
    fi
    
    # 设置正确的权限
    chown -R www-data:www-data "$DEPLOY_TARGET/frontend"
    chmod -R 755 "$DEPLOY_TARGET/frontend"
}

# 部署后端
deploy_backend() {
    log_info "部署后端..."
    
    # 创建后端目录
    mkdir -p "$DEPLOY_TARGET/backend"
    
    # 复制后端文件
    cp "$BACKEND_DIR/server.cjs" "$DEPLOY_TARGET/backend/"
    cp "$BACKEND_DIR/package.json" "$DEPLOY_TARGET/backend/"
    
    # 复制数据库文件（如果存在）
    if [ -f "$BACKEND_DIR/mmd.db" ]; then
        cp "$BACKEND_DIR/mmd.db" "$DEPLOY_TARGET/backend/"
        log_info "已复制数据库文件"
    fi
    
    # 复制Python脚本
    cp "$BACKEND_DIR"/*.py "$DEPLOY_TARGET/backend/" 2>/dev/null || true
    
    cd "$DEPLOY_TARGET/backend"
    
    # 安装后端依赖
    log_info "安装后端依赖..."
    npm ci --production
    
    # 设置权限
    chown -R www-data:www-data "$DEPLOY_TARGET/backend"
    chmod 755 "$DEPLOY_TARGET/backend/server.cjs"
    
    log_success "后端部署完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    cd "$DEPLOY_TARGET/backend"
    
    # 启动后端服务
    pm2 start server.cjs --name "$PM2_APP_NAME" --user www-data
    pm2 save
    pm2 startup
    
    log_success "后端服务已启动"
    
    # 测试服务
    sleep 3
    if curl -f http://localhost:3000/health &>/dev/null; then
        log_success "后端服务健康检查通过"
    else
        log_warning "后端服务健康检查失败，请检查日志"
    fi
}

# 部署Nginx配置
deploy_nginx_config() {
    log_info "部署Nginx配置..."
    
    local nginx_source="$DEPLOY_DIR/nginx.conf"
    
    if [ -f "$nginx_source" ]; then
        # 备份现有配置
        if [ -f "$NGINX_CONFIG" ]; then
            cp "$NGINX_CONFIG" "$NGINX_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
            log_info "已备份现有Nginx配置"
        fi
        
        # 复制新配置
        cp "$nginx_source" "$NGINX_CONFIG"
        
        # 创建软链接启用站点
        if [ ! -L "$NGINX_ENABLED" ]; then
            ln -sf "$NGINX_CONFIG" "$NGINX_ENABLED"
            log_info "已启用Nginx站点"
        fi
        
        # 测试配置
        if nginx -t; then
            systemctl reload nginx
            log_success "Nginx配置部署完成并已重载"
        else
            log_error "Nginx配置测试失败"
            # 恢复备份
            if [ -f "$NGINX_CONFIG.backup.$(date +%Y%m%d_%H%M%S)" ]; then
                cp "$NGINX_CONFIG.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONFIG"
                nginx -t && systemctl reload nginx
                log_info "已恢复备份配置"
            fi
            exit 1
        fi
    else
        log_warning "Nginx配置文件不存在: $nginx_source"
    fi
}

# 检查Nginx配置
check_nginx_config() {
    log_info "检查Nginx配置..."
    
    if [ -f "$NGINX_CONFIG" ]; then
        log_success "Nginx配置文件存在"
    else
        log_warning "Nginx配置文件不存在: $NGINX_CONFIG"
        log_info "请确保已正确配置Nginx"
    fi
    
    # 测试配置
    if nginx -t; then
        log_success "Nginx配置测试通过"
    else
        log_error "Nginx配置测试失败"
        exit 1
    fi
}

# 创建备份
create_backup() {
    if [ -d "$DEPLOY_TARGET" ]; then
        local backup_dir="/var/backups/random-2hu-stuff-$(date +%Y%m%d_%H%M%S)"
        log_info "创建备份: $backup_dir"
        mkdir -p "/var/backups"
        cp -r "$DEPLOY_TARGET" "$backup_dir"
        log_success "备份创建完成"
    fi
}

# 显示状态
show_status() {
    log_info "部署状态:"
    echo "=========================="
    
    # PM2状态
    echo "PM2进程状态:"
    pm2 list | grep "$PM2_APP_NAME" || echo "未找到PM2进程"
    
    # Nginx状态
    echo ""
    echo "Nginx状态:"
    systemctl is-active nginx
    
    # 端口检查
    echo ""
    echo "端口监听状态:"
    netstat -tlnp | grep ":3000" || echo "端口3000未监听"
    netstat -tlnp | grep ":80\|:443" || echo "HTTP/HTTPS端口未监听"
    
    echo "=========================="
}

# 主函数
main() {
    log_info "开始部署 Random 2hu Stuff 项目..."
    echo "项目路径: $PROJECT_ROOT"
    echo "部署目标: $DEPLOY_TARGET"
    echo ""
    
    # 确认部署
    read -p "确认要部署到生产环境吗？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
    
    # 执行部署步骤
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
    
    log_success "部署完成！"
    log_info "前端地址: https://random-2hu-stuff.randomneet.me"
    log_info "后端API: https://random-2hu-stuff.randomneet.me/api"
}

# 处理命令行参数
case "${1:-}" in
    "frontend")
        log_info "仅部署前端..."
        check_root
        build_frontend
        deploy_frontend
        log_success "前端部署完成"
        ;;
    "backend")
        log_info "仅部署后端..."
        check_root
        stop_services
        deploy_backend
        start_services
        log_success "后端部署完成"
        ;;
    "nginx")
        log_info "仅部署Nginx配置..."
        check_root
        deploy_nginx_config
        log_success "Nginx配置部署完成"
        ;;
    "status")
        show_status
        ;;
    "")
        main
        ;;
    *)
        echo "用法: $0 [frontend|backend|nginx|status]"
        echo "  无参数: 完整部署"
        echo "  frontend: 仅部署前端"
        echo "  backend: 仅部署后端"
        echo "  nginx: 仅部署Nginx配置"
        echo "  status: 显示状态"
        exit 1
        ;;
esac
