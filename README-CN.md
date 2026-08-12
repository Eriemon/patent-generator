<p align="center">
  <a href="README.md">English</a>
  <span>&nbsp;|&nbsp;</span>
  <a href="README-CN.md"><strong>中文</strong></a>
</p>

<h1 align="center">Readable Patent Generator</h1>

<p align="center">
  <img src="assets/readme/hero-cn.png" alt="Readable Patent Generator 中文首屏插图" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-1f6feb"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2f81f7"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-v2.1.4-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent--skill-16a34a"></a>
  <a href="references/README.md"><img alt="Target" src="https://img.shields.io/badge/target-%E4%B8%AD%E6%96%87%E4%B8%93%E5%88%A9%E4%BA%A4%E4%BB%98%E5%8C%85-f59e0b"></a>
</p>

<p align="center">
  面向 Codex 的技能，把本地技术材料整理成可审阅的中文专利交付包。
</p>

<p align="center">
  最新版本：<strong>v2.1.4</strong> · 发布日期：<strong>2026-08-12</strong>
</p>

Readable Patent Generator 面向科研人员、工程师和专利撰写协作者，把当前本地工作文件夹中的研究材料、设计文档、实现记录和已确认的专利经验，整理为可审阅的中文专利技术交底书交付包。材料、结构化事实、可编辑公式、权利要求映射、Markdown 草稿、DOCX 模板产物与独立附图在整个流程中保持关联。

## 为什么团队会使用它

本技能提供可重复的本地工作流，而不是一次性生成草稿。流程以预览为起点，明确材料角色，并让每个已接受的数量、术语、公式和附图都拥有可追溯的登记关系。

## 01 —— 从本地材料开始

第一组能力把本地材料整理成清晰路径：盘点输入，为材料赋予发明来源或现有技术角色，登记已接受事实，然后才组成 disclosure model 4.0 与 claims map 3.0。

![来源映射](assets/readme/project-facts-cn.png)

## 02 —— 让事实与作用域保持一致

本技能遵循当前工作文件夹的 `AGENTS.md`，把 installed skill directory 视为只读，并将案件与产物路由到选定的本地研究根目录。公式语义来自 `formula_facts.json` 与 `formula_registry`；定量权利要求始终绑定稳定的 `data_id`。

![受管设计画像](assets/readme/design-profile-cn.png)

## 03 —— 让预览贯穿交付

每个案件从 `preview_pending` 开始。预览汇总已接受材料、术语、事实、公式、权利要求特征和附图登记；只有显式满足预览门禁后，才进入正式 DOCX/Markdown 交付链。

![预览优先渲染](assets/readme/rule-rendering-cn.png)

## 本地交付包

正式交付包由可编辑 DOCX 模板、已确认 Markdown 和独立附图组成。结构、语言、交付和独立 Agent 行为评测全部清零后，才能报告交付就绪。

![本地交付包](assets/readme/local-delivery-cn.png)

## 开始使用

在当前本地工作文件夹中使用 `$readable-patent-generator`。registry 是命令和文档治理的权威入口：

```powershell
python -B scripts/python/registry/build_registry.py --json
python -B scripts/python/registry/query_registry.py "registry" --kind command --json
python -B scripts/python/registry/manage_document_registry.py status --json
```

请先阅读 [SKILL.md](SKILL.md) 了解运行合同，再阅读 [references/README.md](references/README.md) 了解完整流程。运行时案件、材料和生成产物必须留在当前本地工作文件夹或显式选择的研究根目录中。

## 本地开发与 GitHub 镜像

README 和流程变化只在源技能目录中编写；版本化 dist 包从源目录生成，已有 `github/` checkout 只接收完整包。本地开发、安装和远程发布仍然是彼此独立的决定。

```powershell
python path/to/agents-md-generator/scripts/python/release/github_skill_release.py status --project . --skill-dir skills/readable-patent-generator
python path/to/agents-md-generator/scripts/python/release/github_skill_release.py check --project . --skill-dir skills/readable-patent-generator
```

镜像工具保留 `.git`，用选定 dist 包替换 checkout 的其余内容，并比较替换后的文件；它不会替你创建远程仓库，也不会执行 `commit`、`push`、`tag` 或 GitHub Release。

## 技能包包含什么

| 能力 | 维护者得到的结果 |
| --- | --- |
| 材料接收 | 带有明确角色的本地材料地图 |
| 结构化写作 | 事实、术语、公式、权利要求和附图保持关联 |
| 预览门禁 | 显式确认预览后才开始正式产出 |
| 可编辑交付 | DOCX、Markdown 与独立附图一起交付 |

## 作者与引用

Jiyuan Liu 和 He Li 来自东南大学（Southeast University）。本项目与 Heterogeneous Intelligence and Quantum Computing Laboratory (HIQC) 共同开发。

如果你的工作使用了本技能，请通过 [CITATION.cff](CITATION.cff) 引用：

```bibtex
@software{liu_2026_readable_patent_generator,
  author = {Jiyuan Liu and He Li},
  title = {{Readable Patent Generator}: A Governed Local Skill for Chinese Patent Packages},
  year = {2026},
  version = {2.1.4},
  date = {2026-08-12},
  url = {https://github.com/Eriemon/patent-generator},
  license = {Apache-2.0}
}
```

本技能采用 Apache License 2.0。请阅读 [LICENSE](LICENSE)、[CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md) 和 [CITATION.cff](CITATION.cff)。

发布日期：2026-08-12 · 版本：v2.1.4
