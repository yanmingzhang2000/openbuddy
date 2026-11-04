---
name: pr-review
description: 审查 Pull Request 的代码变更,检查常见问题(安全、风格、测试覆盖)
trigger: "review this PR|审查这个 PR|code review"
---

# PR Review Skill

当用户要求审查 Pull Request 或代码变更时:

1. 先用 `git diff` 或工具读取变更范围,不要凭空猜测改动内容。
2. 按以下维度检查:
   - 安全:是否有硬编码凭证、SQL 注入、未校验的用户输入
   - 正确性:逻辑是否符合 PR 描述的意图
   - 测试:是否有对应测试覆盖新增/修改的逻辑
   - 风格:是否符合仓库现有约定(参考 AGENTS.md)
3. 用清单形式输出发现的问题,按严重程度排序,不要只给泛泛的"看起来不错"。
4. 如果发现阻塞性问题,明确标注"建议阻塞合并"及原因。
