"""预算护栏生效测试(对应验收标准"预算护栏生效")。

覆盖两层护栏:
1. `app.engine.conversation_runner.StepBudget`:单 Conversation 内的步数/超时/token/成本护栏。
2. `app.core.budget_guard`:任务创建入口的租户级并发配额护栏。
"""

from __future__ import annotations

import time

from app.core.budget_guard import resolve_task_guardrails
from app.db.models import Tenant
from app.engine.conversation_runner import StepBudget


class TestStepBudget:
    def test_exceeds_on_max_steps(self) -> None:
        budget = StepBudget(
            max_steps=3, timeout_seconds=9999, token_budget=999_999, cost_budget_usd=999.0
        )
        budget.started_at = time.monotonic()
        budget.steps_used = 3
        assert budget.exceeded() == "max_steps_exceeded"

    def test_exceeds_on_timeout(self) -> None:
        budget = StepBudget(
            max_steps=999, timeout_seconds=0, token_budget=999_999, cost_budget_usd=999.0
        )
        budget.started_at = time.monotonic() - 1  # 已经过去 1 秒,超过 0 秒超时
        assert budget.exceeded() == "timeout"

    def test_exceeds_on_token_budget(self) -> None:
        budget = StepBudget(
            max_steps=999, timeout_seconds=9999, token_budget=100, cost_budget_usd=999.0
        )
        budget.started_at = time.monotonic()
        budget.tokens_used = 150
        assert budget.exceeded() == "budget_exceeded"

    def test_exceeds_on_cost_budget(self) -> None:
        budget = StepBudget(
            max_steps=999, timeout_seconds=9999, token_budget=999_999, cost_budget_usd=1.0
        )
        budget.started_at = time.monotonic()
        budget.cost_used_usd = 1.5
        assert budget.exceeded() == "budget_exceeded"

    def test_not_exceeded_within_limits(self) -> None:
        budget = StepBudget(
            max_steps=50, timeout_seconds=1800, token_budget=200_000, cost_budget_usd=5.0
        )
        budget.started_at = time.monotonic()
        budget.steps_used = 1
        budget.tokens_used = 100
        budget.cost_used_usd = 0.01
        assert budget.exceeded() is None


class TestTaskGuardrailResolution:
    def _make_tenant(self, max_cost_budget_usd: float = 10.0) -> Tenant:
        tenant = Tenant(name="t")
        tenant.max_cost_budget_usd = max_cost_budget_usd
        tenant.max_concurrent_tasks = 5
        return tenant

    def test_uses_system_defaults_when_task_does_not_specify(self) -> None:
        tenant = self._make_tenant()
        result = resolve_task_guardrails(tenant, None, None, None, None)
        assert result["max_steps"] > 0
        assert result["cost_budget_usd"] <= tenant.max_cost_budget_usd

    def test_task_requested_cost_budget_is_capped_by_tenant_limit(self) -> None:
        """任务请求的预算不能超过租户上限——即使请求方传入一个超大的数字。"""
        tenant = self._make_tenant(max_cost_budget_usd=2.0)
        result = resolve_task_guardrails(
            tenant,
            requested_max_steps=10,
            requested_timeout_seconds=60,
            requested_token_budget=1000,
            requested_cost_budget_usd=9999.0,  # 故意传一个超过租户上限的值
        )
        assert result["cost_budget_usd"] == 2.0, "必须被截断到租户上限,不能按请求值放行"

    def test_task_requested_cost_budget_under_limit_is_respected(self) -> None:
        tenant = self._make_tenant(max_cost_budget_usd=10.0)
        result = resolve_task_guardrails(
            tenant,
            requested_max_steps=10,
            requested_timeout_seconds=60,
            requested_token_budget=1000,
            requested_cost_budget_usd=3.0,
        )
        assert result["cost_budget_usd"] == 3.0
