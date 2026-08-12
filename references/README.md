# References Index

`readable-patent-generator` 的正式长文档只放在这里。根 `SKILL.md` 保持 thin root；具体流程、写作规范、自检规则和保密要求都从本目录进入。

## 安装入口
- Python 依赖只保留一个入口：`pip install -r requirements.txt`
- 如需使用 CNIPA 浏览器检索，再执行：`python -m playwright install chromium`

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
