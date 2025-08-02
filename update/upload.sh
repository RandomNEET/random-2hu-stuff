#!/usr/bin/env bash

# Random 2hu Stuff 项目上传脚本
# 构建并上传项目到服务器

set -e  # 遇到错误立即退出

# 配置变量
LOCAL_PROJECT_ROOT="$HOME/repo/random-2hu-stuff"
REMOTE_SERVER="root@38.148.249.102"
REMOTE_TARGET="/var/www/"
FRONTEND_DIR="$LOCAL_PROJECT_ROOT/frontend"
BACKEND_DIR="$LOCAL_PROJECT_ROOT/backend"
DEPLOY_DIR="$LOCAL_PROJECT_ROOT/deploy"

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

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    local deps=("node" "npm" "rsync" "ssh")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            log_error "$dep 未安装"
            exit 1
        fi
    done
    
    log_success "所有依赖检查通过"
}

# 测试SSH连接
test_ssh_connection() {
    log_info "测试SSH连接..."
    
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$REMOTE_SERVER" "echo 'SSH连接成功'" 2>/dev/null; then
        log_success "SSH连接测试通过"
    else
        log_error "SSH连接失败，请检查："
        echo "  1. SSH密钥是否正确配置"
        echo "  2. 服务器是否可达"
        echo "  3. 用户权限是否正确"
        exit 1
    fi
}

# 构建前端
build_frontend() {
    log_info "构建前端项目..."
    
    cd "$FRONTEND_DIR"
    
    # 检查package.json是否存在
    if [ ! -f "package.json" ]; then
        log_error "前端package.json不存在"
        exit 1
    fi
    
    # 安装依赖
    log_info "安装前端依赖..."
    npm ci --production=false
    
    # 构建项目
    log_info "构建前端..."
    npm run build
    
    # 检查构建结果
    if [ ! -d "dist" ]; then
        log_error "前端构建失败，dist目录不存在"
        exit 1
    fi
    
    log_success "前端构建完成"
}

# 准备后端文件
prepare_backend() {
    log_info "准备后端文件..."
    
    cd "$BACKEND_DIR"
    
    # 检查必要文件
    local required_files=("server.cjs" "package.json")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "后端文件不存在: $file"
            exit 1
        fi
    done
    
    log_success "后端文件检查完成"
}

# 创建临时上传目录
create_upload_structure() {
    local temp_dir="/tmp/random-2hu-stuff-upload"
    
    # 清理并创建临时目录
    rm -rf "$temp_dir"
    mkdir -p "$temp_dir/random-2hu-stuff"
    
    # 复制前端构建文件（如果存在）
    if [ -d "$FRONTEND_DIR/dist" ]; then
        mkdir -p "$temp_dir/random-2hu-stuff/frontend/dist"
        cp -r "$FRONTEND_DIR/dist/"* "$temp_dir/random-2hu-stuff/frontend/dist/"
    fi
    
    # 复制后端文件
    mkdir -p "$temp_dir/random-2hu-stuff/backend"
    cp "$BACKEND_DIR/server.cjs" "$temp_dir/random-2hu-stuff/backend/"
    cp "$BACKEND_DIR/package.json" "$temp_dir/random-2hu-stuff/backend/"
    
    # 复制 ecosystem.config.js 文件（如果存在）
    if [ -f "$BACKEND_DIR/ecosystem.config.js" ]; then
        cp "$BACKEND_DIR/ecosystem.config.js" "$temp_dir/random-2hu-stuff/backend/"
    fi
    
    # 复制 package-lock.json 文件（如果存在）
    if [ -f "$BACKEND_DIR/package-lock.json" ]; then
        cp "$BACKEND_DIR/package-lock.json" "$temp_dir/random-2hu-stuff/backend/"
    fi
    
    # 复制数据库文件（如果存在）
    if [ -f "$BACKEND_DIR/random-2hu-stuff.db" ]; then
        cp "$BACKEND_DIR/random-2hu-stuff.db" "$temp_dir/random-2hu-stuff/backend/"
    fi
    
    echo "$temp_dir"
}

# 仅上传数据库文件
upload_database_only() {
    log_info "仅上传数据库文件..."
    
    # 检查数据库文件是否存在
    if [ ! -f "$BACKEND_DIR/random-2hu-stuff.db" ]; then
        log_error "数据库文件不存在: $BACKEND_DIR/random-2hu-stuff.db"
        exit 1
    fi
    
    # 直接使用 rsync 上传数据库文件
    rsync -avzh --progress \
        "$BACKEND_DIR/random-2hu-stuff.db" \
        "$REMOTE_SERVER:$REMOTE_TARGET/random-2hu-stuff/backend/"
    
    log_success "数据库文件上传完成"
}

# 上传文件到服务器
upload_files() {
    local temp_dir="$1"
    
    log_info "上传文件到服务器..."
    
    # rsync参数说明：
    # -a: 归档模式，保持文件属性
    # -v: 详细输出
    # -z: 压缩传输
    # -h: 人类可读的输出
    # --progress: 显示进度
    # --delete: 删除目标中不存在的文件
    # --exclude: 排除不需要的文件
    
    rsync -avzh --progress --delete \
        --exclude="node_modules" \
        --exclude=".git" \
        --exclude="*.log" \
        --exclude=".DS_Store" \
        --exclude="Thumbs.db" \
        "$temp_dir/random-2hu-stuff/" \
        "$REMOTE_SERVER:$REMOTE_TARGET/random-2hu-stuff/"
    
    log_success "文件上传完成"
}

# 远程安装后端依赖
install_remote_dependencies() {
    log_info "在服务器上安装后端依赖..."
    
    ssh "$REMOTE_SERVER" << 'EOF'
        cd /var/www/random-2hu-stuff/backend
        
        # 尝试使用 npm ci，如果失败则使用 npm install
        if [ -f "package-lock.json" ]; then
            npm ci --production || npm install --production
        else
            npm install --production
        fi
EOF
    
    log_success "远程依赖安装完成"
}

# 远程重启服务
restart_remote_services() {
    log_info "重启远程服务..."
    
    ssh "$REMOTE_SERVER" << 'EOF'
        # 重启PM2服务
        if command -v pm2 &> /dev/null; then
            cd /var/www/random-2hu-stuff/backend
            pm2 restart random-2hu-api || pm2 start ecosystem.config.js
            pm2 save
        fi
        
        # 重启Nginx
        if command -v nginx &> /dev/null; then
            nginx -t && systemctl reload nginx
        fi
        
        echo "服务重启完成"
EOF
    
    log_success "远程服务重启完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    sleep 5  # 等待服务启动
    
    # 检查HTTP响应
    if curl -f -s "https://random-2hu-stuff.randomneet.me/health" > /dev/null; then
        log_success "健康检查通过"
    else
        log_warning "健康检查失败，请手动检查服务状态"
    fi
}

# 清理临时文件
cleanup() {
    local temp_dir="$1"
    if [ -d "$temp_dir" ]; then
        rm -rf "$temp_dir"
        log_info "清理临时文件完成"
    fi
}

# 显示上传信息
show_upload_info() {
    log_info "上传信息:"
    echo "=========================="
    echo "本地项目: $LOCAL_PROJECT_ROOT"
    echo "远程服务器: $REMOTE_SERVER"
    echo "远程路径: $REMOTE_TARGET/random-2hu-stuff/"
    echo "前端地址: https://random-2hu-stuff.randomneet.me"
    echo "后端API: https://random-2hu-stuff.randomneet.me/api"
    echo "=========================="
}

# 主函数
main() {
    log_info "开始上传 Random 2hu Stuff 项目..."
    show_upload_info
    echo ""
    
    # 确认上传
    read -p "确认要上传到生产服务器吗？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "上传已取消"
        exit 0
    fi
    
    local temp_dir
    
    # 执行上传步骤
    check_dependencies
    test_ssh_connection
    build_frontend
    prepare_backend
    
    log_info "创建上传目录结构..."
    temp_dir=$(create_upload_structure)
    
    # 显示包含的文件信息
    if [ -d "$FRONTEND_DIR/dist" ]; then
        log_info "✓ 已包含前端文件"
    else
        log_warning "✗ 前端dist目录不存在，跳过前端文件"
    fi
    
    if [ -f "$BACKEND_DIR/package-lock.json" ]; then
        log_info "✓ 已包含后端依赖锁定文件"
    else
        log_info "✗ 未找到后端package-lock.json文件"
    fi
    
    if [ -f "$BACKEND_DIR/random-2hu-stuff.db" ]; then
        local db_size=$(du -h "$BACKEND_DIR/random-2hu-stuff.db" | cut -f1)
        log_info "✓ 已包含数据库文件 (大小: $db_size)"
    else
        log_warning "✗ 数据库文件不存在，将不会上传数据库"
    fi
    
    # 设置清理trap
    trap "cleanup '$temp_dir'" EXIT
    
    upload_files "$temp_dir"
    install_remote_dependencies
    restart_remote_services
    health_check
    
    log_success "上传完成！"
    log_info "网站地址: https://random-2hu-stuff.randomneet.me"
}

# 处理命令行参数
case "${1:-}" in
    "build-only")
        log_info "仅构建项目..."
        check_dependencies
        build_frontend
        prepare_backend
        log_success "构建完成"
        ;;
    "upload-only")
        log_info "仅上传文件（跳过构建）..."
        check_dependencies
        temp_dir=$(create_upload_structure)
        trap "cleanup '$temp_dir'" EXIT
        upload_files "$temp_dir"
        log_success "上传完成"
        ;;
    "database-only")
        log_info "仅上传数据库文件..."
        check_dependencies
        test_ssh_connection
        upload_database_only
        restart_remote_services
        log_success "数据库上传并重启服务完成"
        ;;
    "")
        main
        ;;
    *)
        echo "用法: $0 [build-only|upload-only|database-only]"
        echo "  无参数: 完整构建并上传"
        echo "  build-only: 仅构建项目"
        echo "  upload-only: 仅上传文件"
        echo "  database-only: 仅上传数据库文件"
        exit 1
        ;;
esac
