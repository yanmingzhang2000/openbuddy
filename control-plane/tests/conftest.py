"""测试配置。

两类测试:
1. 需要真实 Postgres 的集成测试(test_tenant_isolation.py)——通过环境变量
   `TEST_DATABASE_URL` 指向一个临时测试库,CI 中由 docker-compose 的 postgres 服务提供。
   如果未设置该环境变量,这些测试会被 skip,而不是假装通过。
2. 纯单元测试(test_credential_gateway.py / test_budget_guard.py)——用内存对象 /
   mock 数据库会话,不需要真实 Postgres,任何环境下都应该能跑。
"""

from __future__ import annotations

import os

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_APP_DATABASE_URL")
TEST_OWNER_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

requires_postgres = pytest.mark.skipif(
    not TEST_OWNER_DATABASE_URL,
    reason="需要设置 TEST_DATABASE_URL 环境变量指向可用的 Postgres 实例才能运行此集成测试",
)
