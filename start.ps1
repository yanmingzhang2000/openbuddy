# FrameMind 一键启动脚本 (Windows PowerShell)
# 用法: .\start.ps1 [命令]
# 命令: start(默认) | stop | restart | logs | clean

param(
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host @"
FrameMind 本地部署脚本

用法:
  .\start.ps1          # 启动所有服务
  .\start.ps1 start    # 同上
  .\start.ps1 stop     # 停止所有服务
  .\start.ps1 restart  # 重启所有服务
  .\start.ps1 logs     # 查看日志
  .\start.ps1 clean    # 清理所有数据(危险!)

服务地址:
  Web UI:     http://localhost:3000
  API Docs:   http://localhost:8000/docs
  Ollama:     http://localhost:11434 (需要单独安装)

首次使用:
  1. 确保已安装 Docker Desktop
  2. (可选) 安装 Ollama: https://ollama.com
  3. (可选) 拉取模型: ollama pull qwen2.5-coder:7b
  4. 运行: .\start.ps1

"@
}

function Test-Docker {
    try {
        docker --version | Out-Null
        docker compose version | Out-Null
    } catch {
        Write-Error "Docker 或 Docker Compose 未安装。请先安装 Docker Desktop。"
        exit 1
    }
}

function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Write-Host "未找到 .env 文件，从模板创建..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "✓ 已创建 .env 文件" -ForegroundColor Green
        Write-Host "提示: 可以编辑 .env 修改模型配置" -ForegroundColor Cyan
    }
}

function Start-Services {
    Write-Host "正在启动 FrameMind 服务..." -ForegroundColor Cyan
    Test-Docker
    Test-EnvFile
    
    docker compose up --build -d
    
    Write-Host @"

✓ FrameMind 服务已启动!

访问地址:
  Web UI:   http://localhost:3000
  API 文档: http://localhost:8000/docs

常用命令:
  查看日志:   .\start.ps1 logs
  停止服务:   .\start.ps1 stop
  重启服务:   .\start.ps1 restart

"@ -ForegroundColor Green
}

function Stop-Services {
    Write-Host "正在停止 FrameMind 服务..." -ForegroundColor Cyan
    docker compose down
    Write-Host "✓ 服务已停止" -ForegroundColor Green
}

function Restart-Services {
    Stop-Services
    Start-Services
}

function Show-Logs {
    docker compose logs -f
}

function Clean-All {
    Write-Host @"

警告: 即将删除所有容器、数据卷和网络!
这将清除所有任务、事件和用户数据。
"@ -ForegroundColor Red
    
    $confirm = Read-Host "确认清理所有数据吗? (yes/no)"
    if ($confirm -eq "yes") {
        docker compose down -v
        Write-Host "✓ 所有数据已清理" -ForegroundColor Green
    } else {
        Write-Host "已取消" -ForegroundColor Yellow
    }
}

# 主逻辑
switch ($Action.ToLower()) {
    { $_ -in "start", "" } { Start-Services }
    "stop"    { Stop-Services }
    "restart" { Restart-Services }
    "logs"    { Show-Logs }
    "clean"   { Clean-All }
    "help"    { Show-Help }
    default   { 
        Write-Host "未知命令: $Action" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
