# 查新策略

## 正式产物
- `prior_art_query_plan.md`
- 需要时补充 `prior_art_records.json`

## 最小要求
- 在正文起草前，至少形成可复核的查新问题和检索方向。
- 在需要更强自检结论时，补齐最接近现有技术的公开号/标题、公开日、来源、相同特征和区别特征。
- 正式创造性审阅必须继续补齐“区别特征—区别特征产生的技术效果—重新确定的实际技术问题—现有技术是否给出技术启示及其证据”完整链；浅层相似性记录只能作为检索线索。
- 只有显式记录 `verified: true` 的条目才能进入正文引用和正式审查；字段齐全但未经人工核验的记录仍属于工作底稿。
- `difference_effects` 必须以每条 `different_features` 原文为键并逐项填写非空技术效果；单一汇总效果不能替代逐特征映射。
- `technical_motivation` 必须同时包含非空 `conclusion` 与可回查 `evidence`；只有启示结论而没有证据时，创造性链仍不完整。
- `prior_art_records.json` 应满足 `assets/schemas/prior_art_records.schema.json`，缺少完整推理链时统一审查结果为 `needs_revision`。

## CNIPA 入口
- `search/cnipa_epub_parse.py`：解析本地 HTML
- `search/cnipa_epub_crawler.py`：保存本地或在线 HTML 快照
- `search/cnipa_epub_search.py`：直接解析本地 HTML，或用检索词请求结果页
