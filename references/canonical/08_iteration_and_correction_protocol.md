# 迭代修订规则

## 准备修订
- 用 `iteration/iterate_disclosure.py prepare` 基于当前正文生成带时间戳的新修订稿。
- 旧稿保留，新稿单独落盘，避免覆盖历史版本。

## 记录修订
- 用 `iteration/iterate_disclosure.py log` 记录本轮请求、摘要和产物。
- 修订日志保留在案件目录内，供后续人工追踪。
