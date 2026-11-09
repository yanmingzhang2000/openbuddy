#!/bin/bash
# FrameMind One-Click Start Script (Linux/Mac)
# Usage: ./start.sh [action]
# Actions: start(default) | stop | restart | logs | clean

set -e

ACTION="${1:-start}"

show_help() {
    echo "FrameMind Local Deployment Script"
    echo ""
    echo "Usage:"
    echo "  ./start.sh          # Start all services"
    echo "  ./start.sh start    # Same as above"
    echo "  ./start.sh stop     # Stop all services"
    echo "  ./start.sh restart  # Restart all services"
    echo "  ./start.sh logs     # View logs"
    echo "  ./start.sh clean    # Clean all data (dangerous!)"
    echo ""
    echo "Services:"
    echo "  Web UI:     http://localhost:3000"
    echo "  API Docs:   http://localhost:8000/docs"
    echo "  Ollama:     http://localhost:11434 (requires separate install)"
    echo ""
    echo "First time setup:"
    echo "  1. Ensure Docker and Docker Compose are installed"
    echo "  2. (Optional) Install Ollama: https://ollama.com"
    echo "  3. (Optional) Pull model: ollama pull qwen2.5-coder:7b"
    echo "  4. Run: ./start.sh"
    echo ""
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker not installed"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        echo "Error: Docker Compose not installed"
        exit 1
    fi
}

check_env_file() {
    if [ ! -f ".env" ]; then
        echo "Creating .env from template..."
        cp .env.example .env
        echo "Created .env file"
        echo "Tip: You can edit .env to change model configuration"
    fi
}

start_services() {
    echo "Starting FrameMind services..."
    check_docker
    check_env_file
    
    docker compose up --build -d
    
    echo ""
    echo "FrameMind services started!"
    echo ""
    echo "Access URLs:"
    echo "  Web UI:   http://localhost:3000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "Common commands:"
    echo "  View logs:   ./start.sh logs"
    echo "  Stop:        ./start.sh stop"
    echo "  Restart:     ./start.sh restart"
    echo ""
}

stop_services() {
    echo "Stopping FrameMind services..."
    docker compose down
    echo "Services stopped"
}

restart_services() {
    stop_services
    start_services
}

show_logs() {
    docker compose logs -f
}

clean_all() {
    echo ""
    echo "WARNING: This will delete all containers, volumes, and networks!"
    echo "This will remove all tasks, events, and user data."
    echo ""
    
    read -p "Confirm clean all data? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        docker compose down -v
        echo "All data cleaned"
    else
        echo "Cancelled"
    fi
}

# Main logic
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
        echo "Unknown action: $ACTION"
        show_help
        exit 1
        ;;
esac
