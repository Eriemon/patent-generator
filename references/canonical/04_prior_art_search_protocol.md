# 查新策略

## 正式产物
- `prior_art_query_plan.md`
- 需要时补充 `prior_art_records.json`

## 最小要求
- 在正文起草前，至少形成可复核的查新问题和检索方向。
- 在需要更强自检结论时，补齐最接近现有技术的公开号/标题、公开日、来源、相同特征和区别特征。

## CNIPA 入口
- `search/cnipa_epub_parse.py`：解析本地 HTML
- `search/cnipa_epub_crawler.py`：保存本地或在线 HTML 快照
- `search/cnipa_epub_search.py`：直接解析本地 HTML，或用检索词请求结果页
