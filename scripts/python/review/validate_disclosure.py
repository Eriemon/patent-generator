#!/usr/bin/env python3
"""对正式交底书草稿执行本地自检并输出受管报告。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、按路径加载模块、标准输出和路径能力，供自检入口稳定运行。
import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 固定共享运行时支持模块路径，避免通过修改 sys.path 导入公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 固定正文主骨架必须覆盖的章节标题，供自检时统一校验。
REQUIRED_HEADINGS = [  # 正文主骨架必需章节标题列表
    "## 一、发明名称",  # 发明名称章节
    "## 二、所属技术领域",  # 技术领域章节
    "## 三、现有技术（背景技术）",  # 现有技术章节
    "### 3.1相关技术背景以及最接近的现有技术",  # 相关技术背景小节
    "### 3.2与本发明最相似的现有技术实现方案",  # 最相似现有技术小节
    "### 3.3现有技术的缺点",  # 现有技术缺点小节
    "## 四、发明内容：",  # 发明内容章节
    "### 4.2 技术解决方案",  # 技术解决方案小节
    "#### 4.2.1 装置、结构类",  # 装置结构小节
    "#### 4.2.2 方法类",  # 方法类小节
    "### 4.3、技术效果",  # 技术效果小节
    "## 五、附图及附图的简单说明",  # 附图说明章节
    "## 六、具体实施方式",  # 具体实施方式章节
]

# 固定主交底书草稿禁止残留的内部或模板提示文本。
FORBIDDEN_MAIN_DRAFT_TEXTS = [  # 主草稿禁止文本片段
    "## 七、术语说明",  # 内部术语章节
    "## 八、来源证据摘要",  # 内部证据章节
    "## 九、待确认事项",  # 内部待确认章节
    "【",  # 模板提示左括号
    "】",  # 模板提示右括号
    "待确认",  # 待确认占位
    "TODO",  # 英文待办占位
    "todo",  # 小写待办占位
]

# 按文件路径加载共享运行时支持模块，避免在导入期改写解释器模块搜索路径。
def load_runtime_support_module() -> Any:
    """按路径加载共享运行时支持模块。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的共享运行时支持模块对象。

    异常：
    - 支持模块缺失或无法加载时抛出 `ImportError`。
    """

    # 先根据共享支持模块文件路径创建模块加载规格。
    obj_spec = importlib.util.spec_from_file_location("readable_patent_runtime_support", PATH_RUNTIME_SUPPORT)  # 共享支持模块加载规格

    # 在加载规格或加载器缺失时立即报错，避免后续空对象异常难以定位。
    if obj_spec is None or obj_spec.loader is None:

        # 抛出明确导入错误，提醒调用方先修复 support/runtime_support.py。
        raise ImportError("> ERR: [Python] 无法加载 support/runtime_support.py。")

    # 根据加载规格创建临时模块对象，供后续执行共享支持源码。
    module_runtime_support = importlib.util.module_from_spec(obj_spec)  # 临时共享支持模块对象

    # 执行共享支持模块源码，把公共文件、时间和文本工具装入模块对象。
    obj_spec.loader.exec_module(module_runtime_support)

    # 返回已完成加载的共享支持模块，供自检入口复用。
    return module_runtime_support

# 构造命令行参数解析器，统一声明案件目录和可选输入草稿参数。
def build_parser() -> argparse.ArgumentParser:
    """构造自检入口的命令行解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册参数的解析器对象。

    异常：
    - 无。
    """

    # 先准备解析器说明文本，避免初始化语句过长。
    str_description = "Validate the governed disclosure draft and its companion artifacts."  # 入口说明文本

    # 初始化当前自检入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 自检入口解析器

    # 注册案件目录参数，确保自检固定作用于当前案件空间。
    obj_parser.add_argument("--case-dir", required=True)

    # 注册可选输入草稿参数，允许覆盖自动定位的 disclosure draft。
    obj_parser.add_argument("--input", help="Optional disclosure markdown path.")

    # 返回完成参数注册的解析器对象。
    return obj_parser

# 追加一条结构化 finding，统一约束 level、code、message 和 suggestion 字段。
def add_finding(
    list_findings: list[dict[str, str]],
    str_level: str,
    str_code: str,
    str_message: str,
    str_suggestion: str,
) -> None:
    """追加一条结构化 finding。

    参数：
    - `list_findings`：待追加的 finding 列表。
    - `str_level`：问题级别，例如 blocker 或 major。
    - `str_code`：问题代码。
    - `str_message`：问题说明。
    - `str_suggestion`：修复建议。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 组装当前 finding 结构化记录，保持后续 JSON 与 Markdown 报告共用同一份数据。
    dict_finding = {  # 单条 finding 结构化记录
        "level": str_level,  # 问题级别
        "code": str_code,  # 问题代码
        "message": str_message,  # 问题说明
        "suggestion": str_suggestion,  # 修复建议
    }

    # 把当前 finding 追加到结果列表，保持发现顺序可追溯。
    list_findings.append(dict_finding)

# 校验预览确认状态，确保未确认预览的案件不会误入正式后链交付。
def validate_preview_status(
    path_case_dir: Path,
    list_findings: list[dict[str, str]],
    module_runtime_support: Any,
) -> None:
    """校验预览确认状态。

    参数：
    - `path_case_dir`：案件根目录路径。
    - `list_findings`：待追加的 finding 列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`。

    异常：
    - 预览状态文件存在但 JSON 非法时由底层异常上抛。
    """

    # 固定预览确认状态文件路径，供正式后链进入前统一把关。
    path_preview_status = path_case_dir / "03_drafts" / "preview_status.json"  # 预览确认状态文件路径

    # 在预览状态文件缺失时追加 blocker，阻止正式后链继续推进。
    if not path_preview_status.exists():

        # 记录缺少预览状态文件的 blocker finding。
        add_finding(
            list_findings,
            "blocker",
            "missing_preview_status",
            "缺少 preview_status.json。",
            "先生成并确认预览，再进入正式后链。",
        )

        # 在关键状态文件缺失时提前返回，避免继续读取不存在的 JSON。
        return

    # 读取预览状态 JSON，检查当前案件是否已经被明确确认。
    dict_preview_status = module_runtime_support.read_json_file(path_preview_status)  # 预览状态结构化数据

    # 在预览尚未确认时追加 blocker，阻止正文、附图和导出进入交付态。
    if not dict_preview_status.get("confirmed"):

        # 记录预览未确认的 blocker finding。
        add_finding(
            list_findings,
            "blocker",
            "preview_not_confirmed",
            "预览尚未确认。",
            "由用户确认 pre_draft_preview.md 后重新执行后链。",
        )

# 校验正文主骨架章节，确保正式交底书具备最基本的说明书结构。
def validate_required_headings(
    str_markdown: str,
    list_findings: list[dict[str, str]],
) -> None:
    """校验正文主骨架章节。

    参数：
    - `str_markdown`：正文草稿 Markdown 全文。
    - `list_findings`：待追加的 finding 列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 逐项检查必需章节标题，缺失任一章节都应视为正文主骨架不完整。
    for str_heading in REQUIRED_HEADINGS:

        # 在当前章节标题缺失时追加 blocker，提醒先补齐正文骨架。
        if str_heading not in str_markdown:

            # 记录缺少关键章节的 blocker finding。
            add_finding(
                list_findings,
                "blocker",
                "missing_heading",
                f"缺少关键章节：{str_heading}",
                "补齐说明书主骨架后再进入导出和交付。",
            )

# 校验主草稿没有混入内部审查章节或模板提示占位。
def validate_main_draft_clean(
    str_markdown: str,
    list_findings: list[dict[str, str]],
) -> None:
    """校验主草稿内部材料清理状态。

    参数：
    - `str_markdown`：正文草稿 Markdown 全文。
    - `list_findings`：待追加的 finding 列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 逐项扫描主草稿禁止文本，确保内部材料只进入 sidecar。
    for str_forbidden_text in FORBIDDEN_MAIN_DRAFT_TEXTS:

        # 禁止文本一旦出现在主草稿中，就阻止进入最终交付。
        if str_forbidden_text in str_markdown:

            # 记录主草稿残留内部或模板提示文本的 blocker finding。
            add_finding(
                list_findings,
                "blocker",
                "main_draft_internal_or_placeholder_text",
                f"主交底书草稿残留禁止文本：{str_forbidden_text}",
                "将术语、证据、待确认事项和模板提示移入内部 sidecar 或补齐正式正文。",
            )

# 校验已核验查新记录，确保正文至少绑定一组真实、已核验的近似现有技术。
def validate_prior_art(
    path_case_dir: Path,
    list_findings: list[dict[str, str]],
    module_runtime_support: Any,
) -> None:
    """校验已核验查新记录。

    参数：
    - `path_case_dir`：案件根目录路径。
    - `list_findings`：待追加的 finding 列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`。

    异常：
    - 查新记录读取失败时由底层异常上抛。
    """

    # 读取当前案件已核验的近似现有技术记录列表。
    list_records = module_runtime_support.read_verified_prior_art_records(path_case_dir)  # 已核验查新记录列表

    # 在存在已核验记录时无需追加 finding，说明查新主链至少已补齐基本证据。
    if list_records:

        # 已有核验记录时直接返回，避免误报。
        return

    # 记录缺少已核验查新记录的 major finding。
    add_finding(
        list_findings,
        "major",
        "missing_verified_prior_art",
        "未发现已核验的 prior_art_records.json 记录。",
        "补齐最接近现有技术的公开号/标题、公开日、来源、相同特征和区别特征。",
    )

# 校验附图清单和附图文件，确保清单与落盘文件一一对应。
def validate_figures(
    path_case_dir: Path,
    list_findings: list[dict[str, str]],
    module_runtime_support: Any,
) -> None:
    """校验附图清单和附图文件。

    参数：
    - `path_case_dir`：案件根目录路径。
    - `list_findings`：待追加的 finding 列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`。

    异常：
    - 附图清单存在但 JSON 非法时由底层异常上抛。
    """

    # 固定附图清单 JSON 路径，供附图产物一致性校验复用。
    path_manifest = path_case_dir / "05_figures" / "figures_manifest.json"  # 附图清单 JSON 路径

    # 在附图清单缺失时追加 major finding，提醒先补齐附图主链。
    if not path_manifest.exists():

        # 记录缺少附图清单的 major finding。
        add_finding(
            list_findings,
            "major",
            "missing_figures_manifest",
            "未生成 figures_manifest.json。",
            "先运行附图入口生成正式附图草案。",
        )

        # 在清单缺失时提前返回，避免继续读取不存在的 JSON。
        return

    # 读取附图清单 JSON，检查清单中登记的文件是否都已真正落盘。
    dict_manifest = module_runtime_support.read_json_file(path_manifest)  # 附图清单结构化数据

    # 逐项遍历清单中的附图记录，核对每个文件是否实际存在。
    for dict_figure in dict_manifest.get("figures", []):

        # 拼出当前附图文件路径，供落盘存在性校验使用。
        path_figure = path_case_dir / "05_figures" / dict_figure["file"]  # 当前附图文件路径

        # 在清单登记的文件未落盘时追加 major finding。
        if not path_figure.exists():

            # 记录附图文件缺失的 major finding。
            add_finding(
                list_findings,
                "major",
                "missing_figure_file",
                f"缺少附图文件：{dict_figure['file']}",
                "重新生成附图，确保清单与文件一致。",
            )

# 校验权利要求草案及其说明书映射文件，作为内部辅助材料完整性提示。
def validate_claims(path_case_dir: Path, list_findings: list[dict[str, str]]) -> None:
    """校验权利要求草案及映射文件。

    参数：
    - `path_case_dir`：案件根目录路径。
    - `list_findings`：待追加的 finding 列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 固定权利要求草案 Markdown 路径，供权利要求产物存在性校验复用。
    path_claims_markdown = path_case_dir / "03_drafts" / "claims_draft.md"  # 权利要求草案 Markdown 路径

    # 在权利要求草案缺失时追加 minor finding，不阻断交底书主交付质量。
    if not path_claims_markdown.exists():

        # 记录缺少权利要求草案的 minor finding。
        add_finding(
            list_findings,
            "minor",
            "missing_claims_draft",
            "未生成 claims_draft.md。",
            "如用户需要权利要求辅助材料，再生成权利要求草案。",
        )

    # 固定权利要求映射 JSON 路径，供权利要求与说明书映射关系校验复用。
    path_claims_map = path_case_dir / "03_drafts" / "claims_map.json"  # 权利要求映射 JSON 路径

    # 在权利要求映射缺失时追加 minor finding，不作为主交底书完成硬门槛。
    if not path_claims_map.exists():

        # 记录缺少权利要求映射的 minor finding。
        add_finding(
            list_findings,
            "minor",
            "missing_claims_map",
            "未生成 claims_map.json。",
            "如用户需要权利要求辅助材料，再补齐权利要求与说明书的映射文件。",
        )

# 校验正文来源证据映射，确保关键技术特征不会脱离真实研发材料。
def validate_evidence_map(
    path_case_dir: Path,
    list_findings: list[dict[str, str]],
    module_runtime_support: Any,
) -> None:
    """校验证据映射文件。

    参数：
    - `path_case_dir`：案件根目录路径。
    - `list_findings`：待追加的 finding 列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`。

    异常：
    - 证据映射文件存在但 JSON 非法时由底层异常上抛。
    """

    # 固定来源证据映射路径，供步骤与支撑材料一致性校验复用。
    path_support_map = path_case_dir / "03_drafts" / "latest_evidence_map.json"  # 来源证据映射 JSON 路径

    # 在证据映射缺失时追加 major finding，提醒先补齐来源支撑关系。
    if not path_support_map.exists():

        # 记录缺少来源证据映射的 major finding。
        add_finding(
            list_findings,
            "major",
            "missing_evidence_map",
            "未生成 latest_evidence_map.json。",
            "补齐关键技术特征的来源映射。",
        )

        # 在映射缺失时提前返回，避免继续读取不存在的 JSON。
        return

    # 读取来源证据映射 JSON，检查各特征是否都绑定了证据编号。
    dict_support_map = module_runtime_support.read_json_file(path_support_map)  # 来源证据映射结构化数据

    # 逐项遍历特征列表，核查每个步骤是否都带有支持证据编号。
    for dict_feature in dict_support_map.get("features", []):

        # 在当前特征缺少支持证据编号时追加 major finding。
        if not dict_feature.get("support_ids"):

            # 读取当前特征对应的步骤编号，缺失时回退到显式未知占位。
            str_step_id = dict_feature.get("step", "[unknown]")  # 缺少证据的步骤编号

            # 记录当前步骤缺少证据编号的 major finding。
            add_finding(
                list_findings,
                "major",
                "unsupported_feature",
                f"步骤 {str_step_id} 缺少来源证据编号。",
                "删除无来源内容或补充真实研发材料。",
            )

# 校验高风险占位是否残留在正文主骨架中，避免待确认内容直接进入正式说明书主线。
def validate_placeholder_risk(
    str_markdown: str,
    list_findings: list[dict[str, str]],
) -> None:
    """校验高风险占位残留。

    参数：
    - `str_markdown`：正文草稿 Markdown 全文。
    - `list_findings`：待追加的 finding 列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 在正文中既没有待确认也没有待查新占位时无需继续校验该项风险。
    if "[待确认" not in str_markdown and "[待查新" not in str_markdown:

        # 没有高风险占位时直接返回，避免产生噪声 finding。
        return

    # 先准备正文主骨架标题行列表，只保留二级和三级标题。
    list_outline_lines: list[str] = []  # 正文主骨架标题行列表

    # 逐行遍历正文草稿，只收下二级和三级标题行供占位风险判断复用。
    for str_line in str_markdown.splitlines():

        # 在当前行属于正文主骨架标题时把它追加到标题行列表中。
        if str_line.startswith("## ") or str_line.startswith("### "):

            # 记录当前命中的正文主骨架标题行。
            list_outline_lines.append(str_line)

    # 把主骨架标题行拼成单独文本，供占位是否进入主骨架的风险判定复用。
    str_outline = "\n".join(list_outline_lines)  # 正文主骨架标题文本

    # 在高风险占位进入主骨架标题时追加 major finding。
    if "[待确认" in str_outline or "[待查新" in str_outline:

        # 记录主骨架标题仍残留高风险占位的 major finding。
        add_finding(
            list_findings,
            "major",
            "placeholder_in_outline",
            "正文主骨架仍残留待确认占位。",
            "将占位收敛到“待确认事项”小节，不要进入主方案描述。",
        )

# 汇总结构化自检结果，统一产出 blocked、needs_revision 或 pass 三种状态。
def build_report(
    path_draft: Path,
    list_findings: list[dict[str, str]],
    module_runtime_support: Any,
) -> dict[str, Any]:
    """汇总结构化自检报告。

    参数：
    - `path_draft`：正文草稿路径。
    - `list_findings`：结构化 finding 列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：完整自检报告结构化数据。

    异常：
    - 无。
    """

    # 先准备 blocker 级别的 finding code 集合，供最终状态判断复用。
    set_blocker_codes: set[str] = set()  # 用于判定 blocked 状态的 finding code 集合

    # 单独准备会触发待修订而非阻断的 major code 集合，避免和 blocker 逻辑混淆。
    set_major_codes: set[str] = set()  # 用于决定是否输出 needs_revision 的 code 集合

    # 逐项遍历所有 finding，根据级别把 code 收进对应集合。
    for dict_item in list_findings:

        # 命中 blocker 级别时，把对应 code 收进阻断状态判定集合。
        if dict_item["level"] == "blocker":

            # 登记这个 blocker code，便于最终状态切换到 blocked。
            set_blocker_codes.add(dict_item["code"])

        # 命中 major 级别时，把对应 code 收进待修订状态判定集合。
        if dict_item["level"] == "major":

            # 把当前 major code 收入修订集合，供 blocked 之外的次级状态判断使用。
            set_major_codes.add(dict_item["code"])

    # 在存在 blocker finding 时把状态标记为 blocked。
    if set_blocker_codes:

        # 记录 blocked 状态，阻止当前案件进入正式交付。
        str_status = "blocked"  # 当前自检报告状态

    # 在没有 blocker 但存在 major finding 时标记为 needs_revision。
    elif set_major_codes:

        # 记录需要先修订再复检的状态值，提醒当前案件暂不能直接交付。
        str_status = "needs_revision"  # 需要先修订后再复检的报告状态

    # 在既没有 blocker 也没有 major finding 时标记为通过。
    else:

        # 记录当前案件通过本地自检的状态值，说明这轮检查没有阻断项。
        str_status = "pass"  # 本轮本地自检通过时使用的报告状态

    # 返回完整结构化报告，供 JSON 落盘与 Markdown 渲染共同复用。
    return {
        "generated_at": module_runtime_support.iso_now(),
        "draft": str(path_draft.resolve()),
        "status": str_status,
        "finding_count": len(list_findings),
        "findings": list_findings,
    }

# 渲染 Markdown 自检报告，供人工快速审阅问题级别、问题说明和修复建议。
def render_report_markdown(
    path_draft: Path,
    dict_report: dict[str, Any],
    module_runtime_support: Any,
) -> str:
    """渲染 Markdown 自检报告。

    参数：
    - `path_draft`：正文草稿路径。
    - `dict_report`：结构化自检报告字典。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `str`：Markdown 自检报告文本。

    异常：
    - 无。
    """

    # 先准备 Markdown 报告行列表，固定标题、状态、草稿名和 Findings 小节骨架。
    list_markdown_lines = [  # 自检报告 Markdown 文本行列表
        "# Validation Report",  # 报告标题
        "",  # 标题后的空行
        f"Status: **{module_runtime_support.clean_text(dict_report['status'])}**",  # 报告状态
        f"Draft: `{path_draft.name}`",  # 草稿文件名
        "",  # 草稿名后的空行
        "## Findings",  # Findings 小节标题
        "",  # Findings 小节标题后的空行
    ]

    # 在当前报告存在 finding 时逐条渲染级别、代码、问题和修复建议。
    if dict_report["findings"]:

        # 逐项遍历 finding 列表，把结构化结果转成 Markdown 可读条目。
        for dict_finding in dict_report["findings"]:

            # 为当前 finding 追加分级标题、问题描述和修复建议。
            list_markdown_lines.extend(
                [
                    f"### {dict_finding['level']} / {dict_finding['code']}",  # 单条 finding 标题
                    f"- 问题：{dict_finding['message']}",  # 问题描述
                    f"- 建议：{dict_finding['suggestion']}",  # 建议优先执行的修复动作
                    "",  # 单条 finding 结尾空行
                ]
            )

    # 在没有 finding 时追加通过说明，便于人工快速确认结果。
    else:

        # 追加无阻断性问题说明，标记当前报告为干净状态。
        list_markdown_lines.append("- 未发现阻断性问题。")

    # 返回完整 Markdown 报告文本，供案件目录落盘。
    return "\n".join(list_markdown_lines)

# 执行正式自检入口，读取正文草稿并输出 JSON 与 Markdown 两份受管报告。
def main() -> int:
    """执行正式自检入口。

    参数：
    - 无。

    返回：
    - `int`：`blocked` 返回 `1`，`needs_revision` 返回 `2`，通过返回 `0`。

    异常：
    - 找不到正文草稿时抛出 `FileNotFoundError`。
    - 共享支持加载、文件读取或报告写入失败时由底层异常上抛。
    """

    # 加载共享运行时支持模块，复用正文后链的一致文件、时间和文本工具。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 解析命令行参数，读取案件目录和可选输入草稿路径。
    namespace_arguments = build_parser().parse_args()  # 自检入口参数对象

    # 解析案件目录绝对路径，确保自检固定作用于当前案件空间。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 当前案件根目录

    # 在调用方显式给出输入草稿时解析其绝对路径，否则保留空值供自动定位逻辑处理。
    path_input = Path(namespace_arguments.input).resolve() if namespace_arguments.input else None  # 显式指定的输入草稿路径

    # 定位当前案件可用的 disclosure draft，优先使用显式输入路径。
    path_draft = module_runtime_support.find_disclosure_draft(path_case_dir, path_input)  # 当前案件正文草稿路径

    # 在找不到可用正文草稿时立即报错，避免生成与案件脱节的空报告。
    if path_draft is None or not path_draft.exists():

        # 抛出明确错误，提醒调用方先完成 disclosure draft 阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 disclosure draft markdown。")

    # 读取正文草稿全文，供章节、占位和骨架校验逻辑复用。
    str_markdown = path_draft.read_text(encoding="utf-8")  # 正文草稿 Markdown 全文

    # 先准备结构化 finding 列表，后续所有自检规则都会向其中追加结果。
    list_findings: list[dict[str, str]] = []  # 结构化 finding 列表

    # 校验预览确认状态，阻止未确认预览的案件进入正式交付。
    validate_preview_status(path_case_dir, list_findings, module_runtime_support)

    # 校验正文主骨架标题，确保最基本的说明书结构已经具备。
    validate_required_headings(str_markdown, list_findings)

    # 校验主草稿没有残留内部章节、模板提示或待确认占位。
    validate_main_draft_clean(str_markdown, list_findings)

    # 校验已核验查新记录，确保当前方案绑定真实且已核验的近似现有技术。
    validate_prior_art(path_case_dir, list_findings, module_runtime_support)

    # 校验附图清单和附图文件，确保附图产物完整且与清单一致。
    validate_figures(path_case_dir, list_findings, module_runtime_support)

    # 校验权利要求草案及映射文件，确保交底书配套产物完整。
    validate_claims(path_case_dir, list_findings)

    # 校验证据映射文件，避免关键技术特征脱离真实研发材料。
    validate_evidence_map(path_case_dir, list_findings, module_runtime_support)

    # 校验高风险占位是否仍进入主骨架标题，避免不成熟内容误入正式主线。
    validate_placeholder_risk(str_markdown, list_findings)

    # 汇总结构化自检结果，生成统一的状态、计数和 finding 列表。
    dict_report = build_report(path_draft, list_findings, module_runtime_support)  # 结构化自检报告

    # 固定自检报告目录路径，JSON 与 Markdown 报告都会落在这里。
    path_review_dir = path_case_dir / "04_reviews"  # 自检报告目录路径

    # 固定结构化 JSON 报告输出路径，供后链工具继续复用。
    path_report_json = path_review_dir / "validation_report.json"  # 结构化 JSON 报告输出路径

    # 固定 Markdown 报告输出路径，供人工直接打开审阅。
    path_report_markdown = path_review_dir / "validation_report.md"  # Markdown 报告输出路径

    # 把结构化自检报告写入 JSON 文件，供后链工具读取状态和 finding 列表。
    module_runtime_support.write_json_file(path_report_json, dict_report)

    # 渲染面向人工的 Markdown 自检报告文本。
    str_report_markdown = render_report_markdown(path_draft, dict_report, module_runtime_support)  # Markdown 自检报告文本

    # 把 Markdown 自检报告写入案件目录，便于人工审阅与回看。
    module_runtime_support.write_text_file(path_report_markdown, str_report_markdown)

    # 把 JSON 自检报告绝对路径作为机器可读输出写回上游流程。
    sys.stdout.write(str(path_report_json.resolve()) + "\n")

    # 在当前报告状态为 blocked 时返回阻断退出码。
    if dict_report["status"] == "blocked":

        # 用退出码 1 表示当前案件存在 blocker，禁止继续交付。
        return 1

    # 在当前报告状态为 needs_revision 时返回待修订退出码。
    if dict_report["status"] == "needs_revision":

        # 用退出码 2 表示当前案件需要修订后重新自检。
        return 2

    # 在通过场景下返回成功退出码。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
