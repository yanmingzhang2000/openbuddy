"""MCP(Model Context Protocol)客户端配置。

直接复用 openhands-sdk 内置的 MCP 集成能力(见 docs/ARCHITECTURE.md 2.1),
本模块只负责:按租户/任务生成 MCP server 配置列表,不实现 MCP 协议本身。
"""

from __future__ import annotations

from pydantic import BaseModel


class McpServerConfig(BaseModel):
    name: str
    transport: str = "stdio"  # stdio | sse | streamable_http
    command: str | None = None
    args: list[str] = []
    url: str | None = None


# 平台内置、对所有租户可用的默认 MCP server(不含任何需要凭证的服务)。
DEFAULT_MCP_SERVERS: list[McpServerConfig] = [
    McpServerConfig(
        name="fetch",
        transport="stdio",
        command="uvx",
        args=["mcp-server-fetch"],
    ),
]


def resolve_mcp_servers_for_task(
    tenant_mcp_overrides: list[McpServerConfig] | None = None,
) -> list[McpServerConfig]:
    """返回某任务应加载的 MCP server 列表:默认集 + 租户自定义集(去重按 name)。"""
    merged: dict[str, McpServerConfig] = {s.name: s for s in DEFAULT_MCP_SERVERS}
    for override in tenant_mcp_overrides or []:
        merged[override.name] = override
    return list(merged.values())
