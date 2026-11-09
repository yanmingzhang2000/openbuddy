#!/bin/bash
# FrameMind 一键启动脚本 (Linux/Mac)
# 用法: ./start.sh [命令]
# 命令: start(默认) | stop | restart | logs | clean

set -e

ACTION="${1:-start}"

show_help() {
    cat << EOF
FrameMind 本地部署脚本

用法:
  ./start.sh          # 启动所有服务
  ./start.sh start    # 同上
  ./start.sh stop     # 停止所有服务
  ./start.sh restart  # 重启所有服务
  ./start.sh logs     # 查看日志
  ./start.sh clean    # 清理所有数据(危险!)

服务地址:
  Web UI:     http://localhost:3000
  API Docs:   http://localhost:8000/docs
  Ollama:     http://localhost:11434 (需要单独安装)

首次使用:
  1. 确保已安装 Docker 和 Docker Compose
  2. (可选) 安装 Ollama: https://ollama.com
  3. (可选) 拉取模型: ollama pull qwen2.5-coder:7b
  4. 运行: ./start.sh

EOF
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "错误: Docker 未安装"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        echo "错误: Docker Compose 未安装"
        exit 1
    fi
}

check_env_file() {
    if [ ! -f ".env" ]; then
        echo "未找到 .env 文件，从模板创建..."
        cp .env.example .env
        echo "✓ 已创建 .env 文件"
        echo "提示: 可以编辑 .env 修改模型配置"
    fi
}

start_services() {
    echo "正在启动 FrameMind 服务..."
    check_docker
    check_env_file
    
    docker compose up --build -d
    
    cat << EOF

✓ FrameMind 服务已启动!

访问地址:
  Web UI:   http://localhost:3000
  API 文档: http://localhost:8000/docs

常用命令:
  查看日志:   ./start.sh logs
  停止服务:   ./start.sh stop
  重启服务:   ./start.sh restart

EOF
}

stop_services() {
    echo "正在停止 FrameMind 服务..."
    docker compose down
    echo "✓ 服务已停止"
}

restart_services() {
    stop_services
    start_services
}

show_logs() {
    docker compose logs -f
}

clean_all() {
    cat << EOF

警告: 即将删除所有容器、数据卷和网络!
这将清除所有任务、事件和用户数据。
EOF
    
    read -p "确认清理所有数据吗? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        docker compose down -v
        echo "✓ 所有数据已清理"
    else
        echo "已取消"
    fi
}

# 主逻辑
case "$ACTION" in
    start|"")
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_all
        ;;
    help)
        show_help
        ;;
    *)
        echo "未知命令: $ACTION"
        show_help
        exit 1
        ;;
esac
