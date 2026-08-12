# References Index

`readable-patent-generator` 的正式长文档只放在这里。根 `SKILL.md` 保持 thin root；具体流程、写作规范、自检规则和保密要求都从本目录进入。

## 安装入口
- Python 依赖只保留一个入口：`pip install -r requirements.txt`
- CNIPA 在线检索复用标准库 `urllib` 生产入口，无需安装浏览器运行时。

## 独立 Agent 行为评测
- `evals/evals.json` 保留产品结构与 runtime 用例；`evals/agent_behavior.json` 单独声明 Agent prompt、行为合同和风险。
- 将真实响应写成 `{"responses": [{"case_id": "...", "variant": "with_skill", "text": "..."}]}` 后运行：
  `python -B scripts/python/support/evaluate_agent_behavior.py --manifest evals/agent_behavior.json --responses <responses.json> --output <report.json>`。
- `with_skill` 每个用例都必须有合规响应；`without_skill` 只在显式提供时作为可选对照，缺失响应不会被伪装成通过。
- 报告只保留术语缺口、禁止项和顺序问题，不回显完整 Agent 响应；缺失响应、重复响应和清单错误均 fail-closed。

## Canonical References
- [01_end_to_end_pipeline.md](canonical/01_end_to_end_pipeline.md)
- [02_intake_and_project_scan_protocol.md](canonical/02_intake_and_project_scan_protocol.md)
- [04_prior_art_search_protocol.md](canonical/04_prior_art_search_protocol.md)
- [05_disclosure_drafting_protocol.md](canonical/05_disclosure_drafting_protocol.md)
- [07_self_check_protocol.md](canonical/07_self_check_protocol.md)
- [08_iteration_and_correction_protocol.md](canonical/08_iteration_and_correction_protocol.md)
- [10_confidentiality_and_desensitization.md](canonical/10_confidentiality_and_desensitization.md)
- [11_claims_and_protection_strategy.md](canonical/11_claims_and_protection_strategy.md)

## Boundaries
- 本目录只存放当前有效的正式说明文档，不存历史截图、上游原始协议或重复副本。
- 运行时模板和 schema 放 `assets/`；正式实现放 `scripts/`；根级测试和夹具放 `tests/`。
- Python 文件必须通过 `readable-python-generator` 创建或修改；脚本文件必须通过 `readable-script-generator` 创建或修改。
