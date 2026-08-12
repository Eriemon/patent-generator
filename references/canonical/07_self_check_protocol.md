# 自检规则

## 必查项
- 预览是否已确认
- 正文主骨架是否完整
- 附图和权利要求草案是否已生成
- 来源证据映射是否存在且关键步骤有支撑
- `claims_map.json` 中实际主权项是否均有说明书和研发材料支撑
- 最接近现有技术记录是否形成完整创造性推理链
- AI案件是否按 `ai_scope` 补齐模型结构、训练过程或场景结合披露，并完成人工伦理与公共利益复核

## 统一审查合同
- 通用规则始终适用，AI规则只在用户明确选择 `technical_profile=ai_algorithm` 时启用。
- 系统识别到疑似AI术语时只在 `preview_status.json.profile_check` 中提出建议；必须由用户明确保持 `general` 或切换AI，禁止自动改写案件类型。
- 评估同时写入 `04_reviews/examination_assessment.json`，并将 findings 合并进 `validation_report.json` 的最终状态机。
- AI人工复核若记录为 `reviewed_issue_identified`，必须同时保留风险摘要与证据，并生成 `major` 处置项；工具不得把“已完成复核”误写成“风险已解决”。

## 结果约定
- `pass`：当前草稿可继续导出或交给人工复核
- `needs_revision`：存在需要补强但不阻断当前内部审阅的问题
- `blocked`：存在预览或技术类型未确认、主骨架缺失、无支撑主权项、AI充分公开缺项或关键治理文件缺失等阻断项
