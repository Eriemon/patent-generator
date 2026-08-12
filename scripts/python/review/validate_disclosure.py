#!/usr/bin/env python3
"""对正式交底书草稿执行本地自检并输出受管报告。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、哈希、按路径加载模块、标准输出和路径能力，供自检入口稳定运行。
import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 固定共享运行时支持模块路径，避免通过修改 sys.path 导入公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 固定正文质量合同路径，确保验证评分与起草阶段使用同一受控质量规则。
PATH_QUALITY_CONTRACT = Path(__file__).resolve().parents[1] / "support" / "disclosure_quality_contract.py"  # 正文质量合同模块路径

# 固定统一审查合同路径，使最终验证覆盖创造性、权利要求支撑和AI专项规则。
PATH_EXAMINATION_CONTRACT = Path(__file__).resolve().parents[1] / "support" / "examination_quality_contract.py"  # 统一审查合同模块路径

# 固定版本二结构化合同验证器路径，避免依赖调用方模块搜索路径。
PATH_STRUCTURED_CONTRACT_VALIDATOR = Path(__file__).resolve().parent / "structured_contract_validator.py"  # 结构化合同验证器路径

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

# 按受管路径加载正文质量合同，避免通过 sys.path 注入模块。
def load_quality_contract_module() -> Any:
    """按路径加载正文质量合同模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行的正文质量合同模块对象。

    异常：
    - 合同模块缺失或无法加载时抛出 `ImportError`。
    """

    # 从正式 support 目录构造模块加载规格。
    obj_specification = importlib.util.spec_from_file_location(  # 正文质量合同模块加载规格
        "readable_patent_disclosure_quality_contract",  # 质量合同内部模块名
        PATH_QUALITY_CONTRACT,  # 正文质量合同源码路径
    )

    # 加载规格不完整时阻断自检，避免跳过语义评分卡。
    if obj_specification is None or obj_specification.loader is None:

        # 报告正式质量合同缺失，便于调用方修复技能结构。
        raise ImportError("> ERR: [Python] 无法加载 support/disclosure_quality_contract.py。")

    # 根据已验证规格创建模块对象，等待执行质量规则定义。
    module_quality_contract = importlib.util.module_from_spec(obj_specification)  # 正文质量合同模块对象

    # 执行质量合同模块，暴露评分卡与阻断规则。
    obj_specification.loader.exec_module(module_quality_contract)

    # 返回完成初始化的质量合同模块供自检主流程调用。
    return module_quality_contract

# 按受管路径加载统一审查合同，避免验证阶段复制规则。
def load_examination_contract_module() -> Any:
    """加载统一审查合同模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行的统一审查合同模块对象。

    异常：
    - 合同模块缺失或无法加载时抛出 `ImportError`。
    """

    # 根据正式合同路径创建隔离加载规格。
    obj_specification = importlib.util.spec_from_file_location(  # 统一审查合同加载规格
        "readable_patent_examination_contract",  # 合同内部模块名
        PATH_EXAMINATION_CONTRACT,  # 正式合同源码路径
    )

    # 加载规格不完整时阻断验证，不能跳过新增审查规则。
    if obj_specification is None or obj_specification.loader is None:

        # 报告统一合同缺失，要求先修复正式技能资产。
        raise ImportError("> ERR: [Python] 无法加载 support/examination_quality_contract.py。")

    # 根据已验证规格创建独立模块对象。
    module_examination_contract = importlib.util.module_from_spec(obj_specification)  # 统一审查合同模块

    # 执行正式合同源码，暴露统一案件评估入口。
    obj_specification.loader.exec_module(module_examination_contract)

    # 交回包含创造性和专项规则入口的模块对象。
    return module_examination_contract

# 按受管路径加载版本二结构化合同验证器，禁止模型存在时跳过深层规则。
def load_structured_contract_validator_module() -> Any:
    """按路径加载结构化交底模型验证器。

    参数：
    - 无。

    返回：
    - `Any`：已执行源码的结构化合同验证模块。

    异常：
    - `ImportError`：模块规格或加载器缺失时抛出。
    """

    # 使用稳定内部名称创建隔离加载规格，不修改解释器搜索路径。
    str_module_name = "readable_patent_structured_contract_validator"  # 结构化验证模块内部名称

    # 根据正式验证器文件构造模块加载规格。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, PATH_STRUCTURED_CONTRACT_VALIDATOR)  # 结构化验证加载规格

    # 模块规格不完整时立即阻断，避免案件模型被静默忽略。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出符合当前项目日志合同的明确导入错误。
        raise ImportError("> ERR: [Python] 无法加载 structured_contract_validator.py。")

    # 根据已验证规格创建独立模块实例。
    module_validator = importlib.util.module_from_spec(obj_specification)  # 结构化合同验证模块

    # 执行正式源码，使调用方获得统一跨对象验证入口。
    obj_specification.loader.exec_module(module_validator)

    # 返回已初始化模块供案件模型注入函数调用。
    return module_validator

# 在案件提供版本二模型时追加章节、证据、公式和引用合同 findings。
def append_structured_model_findings(
    path_case_dir: Path,
    list_findings: list[dict[str, str]],
    module_runtime_support: Any,
) -> None:
    """读取可选结构化模型并追加跨对象校验发现。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `list_findings`：现有验证流程的统一 finding 列表。
    - `module_runtime_support`：共享 JSON 文件读取模块。

    返回：
    - `None`：模型存在时原地追加 findings；旧案件缺失模型时保持不变。

    异常：
    - 模型 JSON 损坏或验证模块不可用时由底层异常上抛。
    """

    # 固定新版模型文件位置，避免验证器在案件目录内模糊搜索。
    path_model = path_case_dir / "03_drafts" / "latest_disclosure_model.json"  # 结构化交底模型路径

    # 旧案件没有版本二模型时保持可读取兼容，不伪称已执行新合同。
    if not path_model.exists():

        # 缺失模型不在此兼容接入点追加 finding，由新版生成链负责强制产出。
        return

    # 读取真实案件模型，任何 JSON 损坏都不得被降级为空对象。
    dict_model = module_runtime_support.read_json_file(path_model)  # 当前案件结构化交底模型

    # 为当前案件模型取得跨对象规则入口，确保四类合同检查使用同一结果列表。
    module_validator = load_structured_contract_validator_module()  # 当前案件跨对象规则实例

    # 追加全部 blocker findings，使既有 build_report 自动切换到 blocked。
    list_findings.extend(module_validator.validate_structured_model(dict_model))

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

# 执行统一审查评估并把结果合并到既有自检finding协议。
def append_examination_findings(
    path_case_dir: Path,
    list_findings: list[dict[str, str]],
    module_runtime_support: Any,
    module_examination_contract: Any,
) -> dict[str, Any]:
    """追加创造性、权利要求支撑和AI专项问题。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `list_findings`：既有自检问题列表。
    - `module_runtime_support`：共享JSON和查新记录支持模块。
    - `module_examination_contract`：统一审查合同模块。

    返回：
    - `dict[str, Any]`：可独立落盘的统一审查评估结果。

    异常：
    - 必需案件JSON缺失或损坏时由底层异常上抛。
    """

    # 读取案件配置，确定通用或AI专项规则的适用范围。
    dict_case_config = module_runtime_support.read_json_file(path_case_dir / "case_config.json")  # 当前案件配置

    # 读取研究事实，供AI专项披露和类型信息检查使用。
    dict_research_facts = module_runtime_support.read_json_file(path_case_dir / "02_facts" / "research_facts.json")  # 当前研究事实

    # 读取已核验查新记录，避免未经核验内容进入创造性判断。
    list_prior_art_records = module_runtime_support.read_verified_prior_art_records(path_case_dir)  # 已核验现有技术记录

    # 固定权利要求映射路径，兼容缺失文件时由既有完整性规则单独报告。
    path_claims_map = path_case_dir / "03_drafts" / "claims_map.json"  # 新版权利要求映射路径

    # 文件存在时读取实际权利要求集合，否则使用空映射保持报告可生成。
    dict_claims_map = module_runtime_support.read_json_file(path_claims_map) if path_claims_map.exists() else {}  # 当前权利要求支撑映射

    # 执行同源统一评估，得到稳定状态和错误码。
    dict_assessment = module_examination_contract.assess_examination_quality(  # 统一审查评估结果
        dict_case_config,  # 案件技术类型及AI范围
        dict_research_facts,  # 研发事实和专项披露
        list_prior_art_records,  # 已核验最接近现有技术
        dict_claims_map,  # 实际生成权利要求及省略候选
    )

    # 将统一合同finding转换为既有validation_report字段名称。
    for dict_finding in dict_assessment["findings"]:

        # 保留级别、编号和信息，仅把action映射为suggestion。
        add_finding(
            list_findings,
            str(dict_finding["level"]),
            str(dict_finding["code"]),
            str(dict_finding["message"]),
            str(dict_finding["action"]),
        )

    # 返回独立评估结果，供04_reviews固定落盘和后续追溯。
    return dict_assessment

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

# 校验正文参数更新式均已进入受控行内公式语法。
def validate_inline_math_markers(
    str_markdown: str,
    list_findings: list[dict[str, str]],
    module_quality_contract: Any,
) -> None:
    """阻止确定性数学表达式以普通文字进入 DOCX。

    参数：
    - `str_markdown`：正文草稿 Markdown 全文。
    - `list_findings`：待追加的 finding 列表。
    - `module_quality_contract`：正文数学表达式检测规则模块。

    返回：
    - `None`：发现漏标表达式时原地追加 blocker。

    异常：
    - 无。
    """

    # 收集未被行内公式语法保护的参数更新式，保留原始表达便于定位。
    list_unmarked = module_quality_contract.find_unmarked_inline_math_expressions(str_markdown)  # 未标记表达式列表

    # 每条漏标表达式独立形成 finding，使报告能够明确指出修订对象。
    for str_expression in list_unmarked:

        # 使用稳定代码阻止导出器把当前数学表达式继续写成普通 Word 文本。
        add_finding(
            list_findings,
            "blocker",
            "unmarked_inline_math_expression",
            f"正文数学表达式未使用行内公式标记：{str_expression}",
            "使用 $...$ 标记该表达式后重新生成并导出。",
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

    # 缺少可回查来源时阻断正式完成态，防止无证据背景进入交付包。
    add_finding(
        list_findings,
        "blocker",
        "missing_verified_prior_art",
        "未发现已核验的 prior_art_records.json 记录。",
        "补齐来源类型、公开号或标题、公开日、来源、相同特征和区别特征；非专利来源还需 reference_text。",
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

# 将质量评分卡中的语义缺陷追加到统一 finding 列表。
def append_quality_scorecard_findings(
    list_findings: list[dict[str, str]],
    dict_scorecard: dict[str, Any],
) -> None:
    """把正文评分卡的缺陷合并到统一 validation findings。

    参数：
    - `list_findings`：现有结构化 finding 列表。
    - `dict_scorecard`：正文质量合同生成的评分卡。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 逐条转换评分卡 finding，保持原始等级、代码和信息。
    for dict_scorecard_finding in dict_scorecard.get("findings", []):

        # 通过统一入口追加 finding，避免报告计数字段和正文列表漂移。
        add_finding(
            list_findings,
            str(dict_scorecard_finding["level"]),
            str(dict_scorecard_finding["code"]),
            str(dict_scorecard_finding["message"]),
            str(dict_scorecard_finding["suggestion"]),
        )

# 校验视觉验收回执与当前正文、模板哈希一致，防止旧回执放行新内容。
def is_visual_review_complete(path_case_dir: Path, module_runtime_support: Any) -> bool:
    """判断当前案件是否具有绑定 Word 原生公式证据的视觉验收回执。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `bool`：回执、版本哈希、Word 原生检查和公式证据哈希均匹配时为真。

    异常：
    - JSON 读取失败时由底层异常上抛。
    """

    # 固定视觉验收回执和预览状态路径，二者共同决定最终完成资格。
    path_visual_review = path_case_dir / "04_reviews" / "visual_review.json"  # 视觉验收回执路径

    # 预览状态提供本轮正文与模板的权威哈希，供回执逐项匹配。
    path_preview_status = path_case_dir / "03_drafts" / "preview_status.json"  # 当前预览状态路径

    # 最终公式对象证据由 DOCX 导出器从交付文件包内结构生成。
    path_formula_evidence = path_case_dir / "05_exports" / "formula_evidence.json"  # 最终公式对象证据路径

    # 任一合同文件缺失都表示视觉验收尚未形成可追踪证据。
    if not path_visual_review.exists() or not path_preview_status.exists() or not path_formula_evidence.exists():

        # 缺少回执或哈希事实源时保持视觉验收未完成。
        return False

    # 读取人工视觉验收回执，获取通过状态和所审文档哈希。
    dict_visual_review = module_runtime_support.read_json_file(path_visual_review)  # 视觉验收回执数据

    # 读取当前预览状态，作为正文和模板哈希的权威事实源。
    dict_preview_status = module_runtime_support.read_json_file(path_preview_status)  # 当前预览哈希数据

    # 读取最终公式对象证据，确认 DOCX 结构门已经通过。
    dict_formula_evidence = module_runtime_support.read_json_file(path_formula_evidence)  # 最终公式对象验收数据

    # 回执必须明确标记 passed，其他状态均不得进入最终完成态。
    if dict_visual_review.get("status") != "passed":

        # 待复核或失败回执不具备完成资格。
        return False

    # 对象证据自身未通过时，任何视觉回执都不能把案件推进到 completed。
    if not bool(dict_formula_evidence.get("passed")):

        # 保持未完成状态，要求重新导出并修复公式对象结构。
        return False

    # 视觉验收必须明确使用 Microsoft Word，避免 LibreOffice 渲染掩盖原生公式占位框。
    if dict_visual_review.get("renderer") != "Microsoft Word":

        # 非 Word 或缺失渲染器声明的回执不满足原生对象视觉门。
        return False

    # 读取 Word 原生公式复核明细，逐项确认对象检查与占位框检查已完成。
    dict_word_review = dict_visual_review.get("word_native_formula_review")  # Word 原生公式复核字段

    # 复核字段必须是结构化字典，旧版三字段回执不能继续放行。
    if not isinstance(dict_word_review, dict):

        # 缺少结构化 Word 复核证据时保持视觉验收未完成。
        return False

    # 公式对象和占位框两项都必须由 Word 原生视图明确确认。
    bool_word_checks_passed = (  # Word 原生公式检查是否完整通过
        bool(dict_word_review.get("formula_objects_checked"))  # 已逐项检查公式对象
        and bool(dict_word_review.get("placeholder_boxes_absent"))  # 已确认无虚线占位框
    )

    # 任一 Word 原生检查缺失都不能视为视觉验收完成。
    if not bool_word_checks_passed:

        # 返回未完成，要求审查者补齐真实 Word 检查。
        return False

    # 对最终公式证据文件计算 SHA-256，使视觉回执绑定实际审阅的对象统计版本。
    str_formula_evidence_hash = hashlib.sha256(path_formula_evidence.read_bytes()).hexdigest()  # 当前公式对象证据 SHA-256

    # 回执中的哈希必须精确匹配，阻止审阅后重新导出公式对象而沿用旧回执。
    bool_formula_evidence_matches = dict_word_review.get("formula_evidence_sha256") == str_formula_evidence_hash  # 公式证据哈希是否匹配

    # 正文哈希必须与当前确认版本一致，阻止审阅后正文漂移。
    bool_draft_matches = dict_visual_review.get("draft_hash") == dict_preview_status.get("draft_hash")  # 正文哈希是否匹配

    # 模板哈希必须与当前确认模板一致，阻止审阅后版式基准漂移。
    bool_template_matches = dict_visual_review.get("template_hash") == dict_preview_status.get("template_hash")  # 模板哈希是否匹配

    # 正文、模板和公式对象证据三条版本链同时匹配时才确认完成。
    return bool_draft_matches and bool_template_matches and bool_formula_evidence_matches

# 汇总结构化自检结果，统一产出 blocked、needs_revision 或 visual_review_required 状态。
def build_report(
    path_draft: Path,
    list_findings: list[dict[str, str]],
    dict_scorecard: dict[str, Any],
    module_runtime_support: Any,
) -> dict[str, Any]:
    """汇总结构化自检报告。

    参数：
    - path_draft：正文草稿路径。
    - list_findings：结构化 finding 列表。
    - dict_scorecard：正文质量合同生成的语义评分卡。
    - module_runtime_support：共享运行时支持模块对象。

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

    # 在没有语义缺陷时保留视觉验收待完成状态，禁止仅凭文件存在进入 completed。
    else:

        # 评分卡只会在无缺陷时返回 visual_review_required，作为最终 DOCX 的视觉复核门。
        str_status = str(dict_scorecard["status"])  # 语义通过后的统一流程状态

    # 返回完整结构化报告，供 JSON 落盘与 Markdown 渲染共同复用。
    return {
        "generated_at": module_runtime_support.iso_now(),
        "draft": str(path_draft.resolve()),
        "status": str_status,
        "finding_count": len(list_findings),
        "findings": list_findings,
        "scorecard": dict_scorecard,
        "visual_review": {
            "status": "passed" if str_status == "completed" else "pending",
            "required": str_status != "completed",
        },
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
        f"Score: **{dict_report['scorecard']['score']}/100**",  # 正文语义评分
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
        list_markdown_lines.append("- 未发现语义阻断项；最终 DOCX 仍需完成视觉审阅。")

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

    # 加载正文质量合同，生成可追踪的章节评分与视觉验收前状态。
    module_quality_contract = load_quality_contract_module()  # 正文质量合同模块

    # 加载统一审查合同，启用创造性、支撑和AI专项条件规则。
    module_examination_contract = load_examination_contract_module()  # 创造性及专项规则执行模块

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

    # 校验正文参数更新式不会绕过 MathType 行内公式转换链。
    validate_inline_math_markers(str_markdown, list_findings, module_quality_contract)

    # 校验已核验查新记录，确保当前方案绑定真实且已核验的近似现有技术。
    validate_prior_art(path_case_dir, list_findings, module_runtime_support)

    # 校验附图清单和附图文件，确保附图产物完整且与清单一致。
    validate_figures(path_case_dir, list_findings, module_runtime_support)

    # 校验权利要求草案及映射文件，确保交底书配套产物完整。
    validate_claims(path_case_dir, list_findings)

    # 校验证据映射文件，避免关键技术特征脱离真实研发材料。
    validate_evidence_map(path_case_dir, list_findings, module_runtime_support)

    # 执行新增统一审查合同，并把finding合并到最终状态机。
    dict_examination_assessment = append_examination_findings(  # 待独立落盘的审查结果
        path_case_dir,  # 审查规则读取材料的案件空间
        list_findings,  # 已收集的确定性问题
        module_runtime_support,  # 共享案件读写支持
        module_examination_contract,  # 同源统一审查规则
    )

    # 案件存在版本二模型时执行章节、公式、证据和交叉引用闭包检查。
    append_structured_model_findings(path_case_dir, list_findings, module_runtime_support)

    # 校验高风险占位是否仍进入主骨架标题，避免不成熟内容误入正式主线。
    validate_placeholder_risk(str_markdown, list_findings)

    # 读取与当前正文、模板哈希绑定的视觉验收回执，旧回执不得放行新内容。
    bool_visual_review_complete = is_visual_review_complete(path_case_dir, module_runtime_support)  # 视觉验收是否覆盖当前版本

    # 生成背景、方案、效果和实施方式评分卡，并把视觉验收结果纳入最终状态。
    dict_scorecard = module_quality_contract.build_quality_scorecard(  # 正文质量评分卡
        str_markdown,  # 当前正式交底书 Markdown
        bool_visual_review_complete=bool_visual_review_complete,  # 当前版本视觉验收状态
    )

    # 将评分卡发现的问题合并到统一 findings，确保语义缺陷会阻止错误进入交付态。
    append_quality_scorecard_findings(list_findings, dict_scorecard)

    # 汇总结构化自检结果，生成统一的状态、计数和 finding 列表。
    dict_report = build_report(  # 结构化自检报告
        path_draft,  # 当前正式交底书草稿路径
        list_findings,  # 确定性与语义质量缺陷列表
        dict_scorecard,  # 当前正文语义评分卡
        module_runtime_support,  # 共享时间与路径支持模块
    )

    # 固定自检报告目录路径，JSON 与 Markdown 报告都会落在这里。
    path_review_dir = path_case_dir / "04_reviews"  # 自检报告目录路径

    # 固定结构化 JSON 报告输出路径，供后链工具继续复用。
    path_report_json = path_review_dir / "validation_report.json"  # 结构化 JSON 报告输出路径

    # 固定统一审查评估输出路径，便于单独追溯合同版本和profile。
    path_examination_json = path_review_dir / "examination_assessment.json"  # 统一审查评估输出路径

    # 固定 Markdown 报告输出路径，供人工直接打开审阅。
    path_report_markdown = path_review_dir / "validation_report.md"  # Markdown 报告输出路径

    # 把结构化自检报告写入 JSON 文件，供后链工具读取状态和 finding 列表。
    module_runtime_support.write_json_file(path_report_json, dict_report)

    # 把统一审查评估独立落盘，保留合同版本和专项适用信息。
    module_runtime_support.write_json_file(path_examination_json, dict_examination_assessment)

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
