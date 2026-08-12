"""统一校验结构化交底模型的章节、证据、公式和引用闭包。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 标准库负责读取正式合同资产并按路径复用公式校验模块。
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 固定正式章节合同资产路径，避免在验证代码中复制章节业务枚举。
PATH_SECTION_CONTRACT = Path(__file__).resolve().parents[3] / "assets" / "section_contract.json"  # 章节合同资产路径

# 固定同目录公式校验模块路径，使公式规则保持单一实现来源。
PATH_FORMULA_VALIDATOR = Path(__file__).resolve().parent / "formula_contract_validator.py"  # 公式校验模块路径

# 固定事实完整性合同路径，使模型登记表门禁进入正式验证链。
PATH_FACT_INTEGRITY_CONTRACT = Path(__file__).resolve().parents[1] / "support" / "fact_integrity_contract.py"  # 事实合同模块路径

# 将各专用规则发现统一为现有验证报告可直接消费的结构。
def build_blocker(str_code: str, str_message: str, str_suggestion: str) -> dict[str, str]:
    """构造结构化合同 blocker finding。

    参数：
    - `str_code`：稳定规则代码。
    - `str_message`：可定位的问题说明。
    - `str_suggestion`：不虚构事实的修复建议。

    返回：
    - `dict[str, str]`：现有验证报告兼容的 finding。

    异常：
    - 无。
    """

    # 版本二合同缺陷均影响正式可交付性，因此统一使用 blocker 级别。
    return {"level": "blocker", "code": str_code, "message": str_message, "suggestion": str_suggestion}

# 从正式章节合同加载叶子章节标识，保持验证规则与资产同步。
def load_required_section_ids() -> set[str]:
    """读取正式章节合同中的全部叶子章节标识。

    参数：
    - 无。

    返回：
    - `set[str]`：版本二要求的章节标识集合。

    异常：
    - `FileNotFoundError`：正式章节合同缺失时由文件读取上抛。
    - `json.JSONDecodeError`：合同 JSON 损坏时由解析器上抛。
    """

    # 读取正式资产而不是在代码中维护第二套章节列表。
    dict_contract = json.loads(PATH_SECTION_CONTRACT.read_text(encoding="utf-8"))  # 正式章节合同

    # 返回叶子章节标识集合，供完整性和交叉引用闭包共同使用。
    return {str(dict_section["id"]) for dict_section in dict_contract["sections"]}

# 动态加载同技能内的公式验证器，避免依赖调用方 sys.path 状态。
def load_formula_validator() -> Any:
    """加载正式公式合同验证模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行源码的公式验证模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 使用稳定内部名称隔离动态加载的公式模块实例。
    str_module_name = "patent_formula_contract_validator"  # 公式模块内部名称

    # 根据正式文件路径创建隔离加载规格。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, PATH_FORMULA_VALIDATOR)  # 公式模块加载规格

    # 规格或加载器缺失意味着公式规则不可用，必须阻断验证流程。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出明确错误，禁止跨对象验证静默跳过公式合同。
        raise ImportError("> ERR: [Python] 无法加载 formula_contract_validator.py。")

    # 根据已验证规格创建公式规则模块实例。
    module_validator = importlib.util.module_from_spec(obj_specification)  # 公式验证模块实例

    # 执行正式源码，使调用方复用已经门禁通过的公式规则。
    obj_specification.loader.exec_module(module_validator)

    # 返回已初始化模块供统一验证入口调用。
    return module_validator

# 动态加载事实完整性合同，避免依赖调用方模块搜索路径。
def load_fact_integrity_contract() -> Any:
    """加载正式事实完整性合同模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行源码的事实完整性模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 使用稳定内部名称隔离事实合同模块实例。
    str_module_name = "patent_fact_integrity_contract"  # 事实合同内部模块名

    # 将事实合同源码绑定到当前验证进程的独立模块名。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, PATH_FACT_INTEGRITY_CONTRACT)  # 事实合同加载规格

    # 规格或加载器缺失意味着事实门禁不可用。
    if obj_specification is None or obj_specification.loader is None:

        # 阻断验证流程，禁止静默跳过核心事实规则。
        raise ImportError("> ERR: [Python] 无法加载 fact_integrity_contract.py。")

    # 根据已验证规格创建事实合同模块实例。
    module_contract = importlib.util.module_from_spec(obj_specification)  # 事实合同模块实例

    # 执行正式源码，使调用方消费当前版本规则。
    obj_specification.loader.exec_module(module_contract)

    # 返回已初始化模块供统一模型验证复用。
    return module_contract

# 校验模型章节是否覆盖合同要求，并返回正文已声明标识集合。
def validate_sections(
    list_sections: Any,
    set_required_ids: set[str],
) -> tuple[list[dict[str, str]], set[str]]:
    """校验章节容器与叶子章节完整性。

    参数：
    - `list_sections`：模型中的原始章节值。
    - `set_required_ids`：正式合同要求的章节标识。

    返回：
    - `tuple[list[dict[str, str]], set[str]]`：章节发现与已声明标识集合。

    异常：
    - 无。
    """

    # 非列表章节无法建立顺序和完整性，使用空集合继续汇总其他问题。
    if not isinstance(list_sections, list):

        # 返回容器问题和空标识集合，避免后续引用检查误放行。
        dict_finding = build_blocker("SEC002", "模型 sections 必须为数组", "按章节合同重建数组")  # 章节容器发现

        # 返回单条发现及空章节集合，供调用方继续执行其余合同检查。
        return [dict_finding], set()

    # 仅从映射章节读取非空标识，损坏记录不会被当作有效目标。
    set_present_ids: set[str] = set()  # 已声明章节标识

    # 逐项收集章节标识，保持类型错误记录与有效目标隔离。
    for dict_section in list_sections:

        # 只有映射章节才能提供稳定 id 字段。
        if isinstance(dict_section, Mapping):

            # 登记当前章节标识，供缺失项和交叉引用闭包共同使用。
            set_present_ids.add(str(dict_section.get("id", "")))

    # 计算合同要求但模型缺失的叶子章节，排序保证消息稳定。
    list_missing_ids = sorted(set_required_ids - set_present_ids)  # 缺失章节标识

    # 每个缺失章节形成独立 finding，便于起草器精确补齐。
    list_findings: list[dict[str, str]] = []  # 章节完整性发现

    # 逐个生成发现，使章节编号与修复动作保持一一对应。
    for str_section_id in list_missing_ids:

        # 追加当前缺失章节的稳定 blocker 记录。
        list_findings.append(build_blocker("SEC002", f"缺少合同章节:{str_section_id}", "依据章节合同补齐内容与证据"))

    # 返回章节发现和可用于交叉引用闭包的实际标识集合。
    return list_findings, set_present_ids

# 校验章节使用的证据编号是否都存在于证据登记表。
def validate_evidence_references(list_sections: Any, dict_evidence_map: Any) -> list[dict[str, str]]:
    """检查章节证据引用是否悬空。

    参数：
    - `list_sections`：模型中的章节数组。
    - `dict_evidence_map`：证据记录及映射对象。

    返回：
    - `list[dict[str, str]]`：悬空证据引用 findings。

    异常：
    - 无。
    """

    # 类型错误时使用空容器，让所有显式引用都被识别为悬空。
    list_safe_sections = list_sections if isinstance(list_sections, list) else []  # 可迭代章节记录

    # 仅从映射形式证据表读取 records，其他类型视为空登记表。
    list_records = dict_evidence_map.get("records", []) if isinstance(dict_evidence_map, Mapping) else []  # 证据记录列表

    # 提取已登记证据编号，损坏记录不参与引用闭包。
    set_evidence_ids: set[str] = set()  # 可用证据编号

    # 逐项读取证据记录，防止非对象值被视为有效来源。
    for dict_record in list_records:

        # 映射记录才具备可追踪的 id 字段。
        if isinstance(dict_record, Mapping):

            # 登记当前证据编号，供章节使用集合执行差集。
            set_evidence_ids.add(str(dict_record.get("id", "")))

    # 汇总章节引用但未登记的证据编号，使用循环保持表达式可审阅。
    set_used_ids: set[str] = set()  # 章节使用证据编号

    # 逐章收集证据编号，非映射章节已由章节结构规则负责报告。
    for dict_section in list_safe_sections:

        # 只有映射章节才具备 evidence_ids 字段。
        if isinstance(dict_section, Mapping):

            # 将当前章节全部证据编号规范为字符串并并入使用集合。
            set_used_ids.update(str(str_evidence_id) for str_evidence_id in dict_section.get("evidence_ids", []))

    # 排序悬空编号，保证 JSON 和 Markdown 报告跨运行稳定。
    list_missing_ids = sorted(set_used_ids - set_evidence_ids)  # 悬空证据编号

    # 每个悬空编号形成独立 blocker，禁止将无来源内容计为已支撑。
    return [
        build_blocker("EVD001", f"证据引用不存在:{str_evidence_id}", "补充真实证据或移除引用")
        for str_evidence_id in list_missing_ids
    ]

# 校验模型显式交叉引用的源和目标都指向已声明章节。
def validate_cross_references(list_references: Any, set_section_ids: set[str]) -> list[dict[str, str]]:
    """检查章节交叉引用闭包。

    参数：
    - `list_references`：模型中的显式交叉引用数组。
    - `set_section_ids`：正文实际声明的章节标识。

    返回：
    - `list[dict[str, str]]`：无效引用 findings。

    异常：
    - 无。
    """

    # 非列表引用容器不能逐项检查，直接形成结构问题。
    if not isinstance(list_references, list):

        # 返回引用容器问题，提醒上游恢复数组结构。
        return [build_blocker("XRF001", "cross_references 必须为数组", "按源章节和目标章节重建引用数组")]

    # 收集源或目标不在正文章节集合中的引用记录。
    list_invalid: list[Any] = []  # 无效交叉引用

    # 逐项拆分源目标判断，避免复合表达式掩盖失败原因。
    for dict_reference in list_references:

        # 非映射记录无法表达源和目标，直接作为无效引用收集。
        if not isinstance(dict_reference, Mapping):

            # 保留原始记录，供 finding 消息定位损坏输入。
            list_invalid.append(dict_reference)

            # 跳过当前损坏记录的字段读取。
            continue

        # 分别提取引用源和目标，供闭包判断复用。
        str_source = str(dict_reference.get("source", ""))  # 当前引用源章节

        # 目标章节必须与模型实际章节标识完全匹配。
        str_target = str(dict_reference.get("target", ""))  # 当前引用目标章节

        # 任一端不存在都会使交叉引用无法在正文中解析。
        if str_source not in set_section_ids or str_target not in set_section_ids:

            # 收集无效映射，稍后统一生成稳定 findings。
            list_invalid.append(dict_reference)

    # 为每条损坏引用生成定位消息，禁止错误章节号进入实施方式。
    return [
        build_blocker("XRF001", f"交叉引用目标无效:{dict_reference}", "修正为真实章节标识")
        for dict_reference in list_invalid
    ]

# 统一执行版本二模型的四类合同检查并保持 findings 顺序稳定。
def validate_structured_model(dict_model: Mapping[str, Any]) -> list[dict[str, str]]:
    """验证结构化交底模型的跨对象闭包。

    参数：
    - `dict_model`：版本二结构化交底模型。

    返回：
    - `list[dict[str, str]]`：现有验证报告可直接消费的 blocker findings。

    异常：
    - 正式章节合同或公式验证模块不可读时由底层异常上抛。
    """

    # 旧模型必须重新生成，禁止通过兼容回退继续形成确认稿。
    list_version_findings: list[dict[str, str]] = []  # 版本三模型状态发现

    # 只有版本三合同可以进入后续正式验证。
    if dict_model.get("contract_version") != "3.0":

        # 记录稳定 blocker，同时继续汇总旧模型的具体内容问题。
        list_version_findings.append(build_blocker("MOD001", "结构化模型不是版本3.0", "重新运行起草流程生成 latest_disclosure_model.json"))

    # 从正式资产读取章节要求，防止代码与合同文件发生枚举漂移。
    set_required_ids = load_required_section_ids()  # 合同要求章节标识

    # 章节检查同时返回实际标识，供后续交叉引用闭包复用。
    tuple_section_result = validate_sections(dict_model.get("sections"), set_required_ids)  # 章节检查结果

    # 分离章节 findings 与实际标识集合，使汇总顺序清晰稳定。
    list_findings = list_version_findings + list(tuple_section_result[0])  # 统一结构化 findings

    # 保存模型实际章节标识，用于判断引用源和目标是否存在。
    set_present_ids = tuple_section_result[1]  # 正文已声明章节标识

    # 证据检查紧随章节完整性，优先暴露正文事实支撑缺口。
    list_findings.extend(validate_evidence_references(dict_model.get("sections"), dict_model.get("evidence_registry")))

    # 调用既有公式验证器，保持 FOR001-FOR007 的单一规则来源。
    module_formula_validator = load_formula_validator()  # 正式公式验证模块

    # 公式登记表非列表时传入空数组，并单独形成基础结构问题。
    obj_formula_registry = dict_model.get("formula_registry")  # 原始公式登记表值

    # 公式容器类型错误会阻断正式交付，不能静默当成无公式案件。
    if not isinstance(obj_formula_registry, list):

        # 登记公式容器问题后使用空列表继续交叉引用检查。
        list_findings.append(build_blocker("FOR001", "formula_registry 必须为数组", "按公式 schema 重建登记表"))

        # 空列表仅用于安全调用公式模块，不代表原始输入通过。
        list_formula_registry: list[Any] = []  # 安全公式记录列表

    # 合法列表保持原对象顺序，供专用验证器逐项检查。
    else:

        # 使用已验证的列表对象执行公式语义规则。
        list_formula_registry = obj_formula_registry  # 待校验公式记录列表

    # 将专用公式 findings 转换为现有报告结构并追加到统一列表。
    for dict_formula_finding in module_formula_validator.validate_formula_registry(list_formula_registry):

        # 公式规则只返回代码和消息，统一层补充 blocker 级别和修复边界。
        str_code = str(dict_formula_finding["code"])  # 当前公式 finding 代码

        # 保留专用验证器的问题消息，避免统一层丢失公式定位信息。
        str_message = str(dict_formula_finding["message"])  # 当前公式 finding 消息

        # 补充统一修复边界，并把公式问题加入现有验证报告。
        list_findings.append(build_blocker(str_code, str_message, "依据本地材料补齐公式语义，不得推测变量"))

    # 最后检查显式章节引用，使报告先呈现内容问题再呈现导航问题。
    list_findings.extend(validate_cross_references(dict_model.get("cross_references", []), set_present_ids))

    # 执行材料、数值、待办和附图来源的模型级事实完整性门禁。
    module_fact_contract = load_fact_integrity_contract()  # 正式事实完整性模块

    # 将事实合同 findings 直接并入现有阻断状态机。
    list_findings.extend(module_fact_contract.validate_delivery_model(dict_model))

    # 返回统一 findings；任一条都会使现有状态机构建 blocked。
    return list_findings
