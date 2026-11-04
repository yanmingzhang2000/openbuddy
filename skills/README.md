# Skills 目录

本目录存放平台级 Skills,遵循 OpenHands SDK 的 Skill 触发器约定(frontmatter 中的
`trigger` 字段用于匹配用户指令,匹配后对应 Markdown 正文作为额外的 system 提示注入)。

- 新增 skill:添加一个 `*.md` 文件,带 `name` / `description` / `trigger` frontmatter。
- 平台会在任务启动时通过 `app.tools.skills.list_available_skills()` 枚举此目录。
- 租户/项目级 skill 可以放在任务工作区仓库内的 `.openhands/skills/` 下(遵循 SDK 约定),
  优先级高于平台内置 skill。
