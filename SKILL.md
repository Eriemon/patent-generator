---
name: readable-patent-generator
description: >-
  Use when users need to extract invention points from local technical materials and
  generate, rewrite, review, or iteratively refine Chinese patent technical
  disclosure delivery packages for patent agents, with governed DOCX, Markdown,
  and figure outputs under strict local-only workflows and language-routing contracts.
---

# Readable Patent Generator

本技能把当前本地工作文件夹中的研究材料、设计文档和实现证据，组织为可审阅的中文专利技术交底书交付包。正式交付包含模板 DOCX、已确认的 Markdown 源稿和独立附图包；installed skill directory as read-only，运行时案件、材料和输出必须留在 current local work folder 或用户明确选择的研究根目录。

## 不可变合同

- 首轮只能返回 `preview_pending`；只有显式预览确认后才能进入正式交付后链（Keep the hard preview gate）。
- 外部材料只是审查输入。材料进入正式模型前必须有人确认并赋予 explicit `source_roles`：`invention_evidence` 或 `prior_art`；拒绝、待定、冲突和未知角色不得进入正式模型。
- 每个数量、阈值、样本数、参数和性能陈述都必须在 `data_registry` 中经 explicit acceptance 确认并绑定 stable `data_id`；Do not copy 外部数字。公式语义必须由 `formula_facts.json` 和 `formula_registry` 提供，禁止从变量名猜测。
- 使用 disclosure model 4.0、claims map 3.0 和 `assets/examination_quality_contract.json`。硬 AI 事实强制适用 AI 审查规则；适用 AI 规则时必须提供 `ai_scope`。
- 语义复核绑定精确内容哈希；定量事实、每组独立权利要求特征和 AI 适用性都需要当前人工确认。无支持映射的权利要求阻断交付。
- 背景技术按 patent reference date 划分；之后发表的材料只能作为 later references，不得倒推基准现有技术。
- 公式必须导出为可编辑方程对象：默认 `mathtype` 使用 native MathType OLE/MTEF，显式 `office` 才使用 native OMML；图片、纯文本回退和 silent fallback 均禁止。
- 正式 model 4.0 必须保留 `evidence_registry`、`term_registry`、`figure_registry` 及其来源绑定。

## 受管工作流

1. 检查根 `AGENTS.md`、当前治理状态和恢复检查；只读取完成当前任务所需的本地材料。
2. 依次执行材料角色确认、事实/术语/来源登记、发明点提炼、查新和预览生成；预览确认前不得生成正式交付物。
3. 通过 `assets/cn_technical_disclosure_template.docx` 导出，并独立验证模板信息表、必需章节、中文排版、公式、附图登记和无内部占位符。
4. 运行结构、语言、交付证据和独立 Agent 行为评测；所有阻断项清零后才能报告完成。

## 代码与产物路由

- Python 文件统一放在 `scripts/python/<function>/`，创建或修改必须先经过 `readable-python-generator` dispatcher/classification、intent contract、profile、真实落盘目标检查和 `run_post_generation_checks.py`。
- bat/cmd、shell/bash、PowerShell、Tcl 目标统一放在对应 `scripts/<family>/`，创建或修改必须先经过 `readable-script-generator` 的同一套 dispatcher/classification、intent contract、目标语言 profile、落盘目标检查和 post-generation gate。
- 运行产物写入工作区根 `runs/`，验证报告写入根 `reports/`；正式实现、模板、schema、评测和 canonical 文档留在本技能目录的受管位置。
- registry 元数据以 `config/registry/manifest.json` 及其 JSON 源为准（JSON is authoritative），Markdown 是知识正文权威，SQLite 只能由 `scripts/python/registry/build_registry.py` 原子重建。

## Canonical references

具体端到端流程、材料盘点、查新、写作、自检、迭代、保密和权利要求策略见 [references/README.md](references/README.md) 及其 `canonical/` 文档。独立 Agent 行为合同见 [evals/agent_behavior.json](evals/agent_behavior.json)；评测命令和 fail-closed 规则见 [references/README.md](references/README.md)。

## Registry commands

`registry.build`：只读完整性检查，运行 `python -B scripts/python/registry/build_registry.py --json`。

`registry.ask`：查询注册入口，运行 `python -B scripts/python/registry/query_registry.py QUERY --kind command|workflow|document|knowledge --json`。

`registry.document-governance`：文档治理，运行 `python -B scripts/python/registry/manage_document_registry.py status|scan|check|init|finalize --json`；写操作仅在明确授权并满足其二次确认合同后执行。
