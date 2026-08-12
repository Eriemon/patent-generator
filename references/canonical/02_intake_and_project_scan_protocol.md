# 材料接入与项目扫描

## 输入边界
- 研究笔记、README、设计文档、代码片段、PDF、DOCX、PPTX 都可以作为本地输入材料。
- `ref/` 只作为迁移参考源，不直接进入正式案件目录。

## 扫描要求
- 先建立 `research_inventory.json` 和 `research_inventory.md`，让后续 facts 有稳定输入。
- 模板、样例、空表单和明显的管理信息要在 intake 阶段降权或剔除，避免污染事实抽取。

## 转换要求
- Office/PDF 富转换失败时保留统一的 unreadable 提示，不伪造正文内容。
- 所有可选依赖提示都统一指向 `requirements.txt`。
