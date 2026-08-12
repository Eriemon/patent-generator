"""统一校验结构化交底模型的章节、证据、公式和引用闭包。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 标准库负责读取正式合同资产、计算内容摘要并按路径复用专用模块。
import hashlib
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 第三方库执行 Draft 2020-12 schema，而不是把 JSON 文件当作文档。
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

# 固定正式章节合同资产路径，避免在验证代码中复制章节业务枚举。
PATH_SECTION_CONTRACT = Path(__file__).resolve().parents[3] / "assets" / "section_contract.json"  # 章节合同资产路径

# 固定 Model 4.0 schema 路径，使运行时和发布资产消费同一合同。
PATH_MODEL_SCHEMA = Path(__file__).resolve().parents[3] / "assets" / "schemas" / "disclosure_model.schema.json"  # 版本四模型结构合同路径

# 固定 claims map 3.0 schema 路径，避免权利要求入口只信任生成器输出。
PATH_CLAIMS_SCHEMA = Path(__file__).resolve().parents[3] / "assets" / "schemas" / "claims_map.schema.json"  # 权利要求映射结构合同路径

# 固定公式 schema 路径，用 registry 解析 Model 4.0 的相对引用。
PATH_FORMULA_SCHEMA = Path(__file__).resolve().parents[3] / "assets" / "schemas" / "formula_registry.schema.json"  # 公式 schema 路径

# 固定同目录公式校验模块路径，使公式规则保持单一实现来源。
PATH_FORMULA_VALIDATOR = Path(__file__).resolve().parent / "formula_contract_validator.py"  # 公式校验模块路径

# 固定事实完整性合同路径，使模型登记表门禁进入正式验证链。
PATH_FACT_INTEGRITY_CONTRACT = Path(__file__).resolve().parents[1] / "support" / "fact_integrity_contract.py"  # 事实合同模块路径

# 固定安全容器模块路径，使 schema 失败后的深层诊断保持 type-total。
PATH_MODEL_SAFE_TYPES = Path(__file__).resolve().parent / "model_safe_types.py"  # Model 4 安全容器模块

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

# 动态加载安全容器模块，避免验证器继续承担规整细节。
def load_model_safe_types() -> Any:
    """加载 Model 4 安全容器规整模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行源码的安全容器模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 根据正式路径创建隔离模块加载规格。
    obj_specification = importlib.util.spec_from_file_location(  # 安全容器模块加载规格
        "patent_model_safe_types",  # 与其他动态模块隔离的名称
        PATH_MODEL_SAFE_TYPES,  # 正式安全容器模块路径
    )  # 安全容器模块规格

    # 规格不可用时阻断深层诊断，禁止退回不安全读取。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出符合项目日志合同的明确导入错误。
        raise ImportError("> ERR: [Python] 无法加载 model_safe_types.py。")

    # 根据已验证规格创建本轮独享的安全容器模块。
    module_safe_types = importlib.util.module_from_spec(obj_specification)  # 待执行规整模块实例

    # 执行正式模块源码，使两个规整入口可供验证器调用。
    obj_specification.loader.exec_module(module_safe_types)

    # 返回已初始化模块供模型和 claims 共同复用。
    return module_safe_types

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

    # 先准备章节内容发现，空正文不能靠章节编号存在性绕过门禁。
    list_findings: list[dict[str, str]] = []  # 章节完整性发现

    # 逐项收集章节标识，保持类型错误记录与有效目标隔离。
    for dict_section in list_sections:

        # 只有映射章节才能提供稳定 id 字段。
        if isinstance(dict_section, Mapping):

            # 登记当前章节标识，供缺失项和交叉引用闭包共同使用。
            str_section_id = str(dict_section.get("id", ""))  # 当前章节编号

            # 非空编号才参与章节闭包，避免空键伪造存在性。
            if str_section_id:

                # 记录真实章节编号。
                set_present_ids.add(str_section_id)

            # 必填章节正文为空时逐项形成可定位 blocker。
            if str_section_id in set_required_ids and not str(dict_section.get("content", "")).strip():

                # 空章节没有可实施披露，必须回到真实材料补齐。
                list_findings.append(build_blocker("SEC003", f"合同章节正文为空:{str_section_id}", "依据本地材料补齐可实施内容"))

    # 计算合同要求但模型缺失的叶子章节，排序保证消息稳定。
    list_missing_ids = sorted(set_required_ids - set_present_ids)  # 缺失章节标识

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

# 读取 Draft 2020-12 schema 并执行自身合同检查。
def load_schema(path_schema: Path) -> dict[str, Any]:
    """读取并检查正式 JSON Schema。

    参数：
    - `path_schema`：正式 schema 文件路径。

    返回：
    - `dict[str, Any]`：可交给 Draft 2020-12 验证器的 schema。

    异常：
    - `FileNotFoundError`：schema 缺失时由文件读取上抛。
    - `json.JSONDecodeError`：schema 损坏时由解析器上抛。
    - `jsonschema.exceptions.SchemaError`：schema 不符合 Draft 2020-12 时上抛。
    """

    # 读取 schema 原始内容，确保运行时不使用代码内副本。
    dict_schema = json.loads(path_schema.read_text(encoding="utf-8"))  # 正式 schema 对象

    # 验证 schema 自身后再用于案件数据，避免损坏合同制造假绿。
    Draft202012Validator.check_schema(dict_schema)

    # 返回已验证 schema 供实例校验复用。
    return dict_schema

# 用正式 schema 执行模型实例校验，并转换为统一 blocker。
def validate_model_schema(dict_model: Mapping[str, Any]) -> list[dict[str, str]]:
    """执行 Model 4.0 Draft 2020-12 结构校验。

    参数：
    - `dict_model`：待验证结构化交底模型。

    返回：
    - `list[dict[str, str]]`：按实例路径排序的 schema blockers。

    异常：
    - schema 文件缺失或损坏时由底层异常上抛。
    """

    # 加载模型和公式 schema，供相对引用解析使用。
    dict_schema = load_schema(PATH_MODEL_SCHEMA)  # 版本四模型正式结构合同

    # 公式 schema 作为独立资源注册到其正式 URI。
    dict_formula_schema = load_schema(PATH_FORMULA_SCHEMA)  # 公式登记表 schema

    # 将公式资源绑定到 schema 声明的绝对标识。
    str_formula_uri = str(dict_formula_schema["$id"])  # 公式 schema 资源标识

    # 注册资源后 Draft 2020-12 验证器可以解析相对 $ref。
    obj_registry = Registry().with_resource(  # 公式相对引用资源注册表
        str_formula_uri,  # 公式合同正式资源标识
        Resource.from_contents(dict_formula_schema),  # 公式合同可解析资源
    )

    # 创建真正执行正式合同的 Draft 2020-12 验证器。
    obj_validator = Draft202012Validator(dict_schema, registry=obj_registry)  # Model 4.0 实例验证器

    # 按实例路径排序，保证不同运行中的 finding 顺序稳定。
    list_errors = sorted(  # 按实例路径排序的模型结构失败
        obj_validator.iter_errors(dict(dict_model)),  # 当前模型结构错误迭代器
        key=lambda obj_error: list(obj_error.absolute_path),  # 当前模型错误实例路径
    )

    # 每个失败位置形成独立 blocker，保留具体路径和原始消息。
    return [
        build_blocker(
            "SCH001",
            (
                "Model 4.0 schema 失败:"
                f"{'/'.join(str(obj_part) for obj_part in obj_error.absolute_path) or '<root>'}:"
                f"{obj_error.message}"
            ),
            "按 disclosure_model.schema.json 修复结构和非空字段",
        )
        for obj_error in list_errors
    ]

# 语义审查验证器独立承载审查记录和历史图规则，保持聚合模块低于尺寸上限。
PATH_SEMANTIC_REVIEW_VALIDATOR = Path(__file__).resolve().parent / "semantic_review_validator.py"  # 语义审查验证模块路径

# 动态加载同目录语义审查验证器，兼容按文件路径导入的现有调用方。
def load_semantic_review_validator() -> Any:
    """加载语义审查验证模块。

    参数：
    - 无。

    返回：
    - `Any`：已加载的语义审查验证模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 为历史图规则建立独立模块规格，避免与公式验证器共享加载身份。
    obj_specification = importlib.util.spec_from_file_location(  # 语义审查模块加载规格
        "patent_semantic_review_validator",  # 审查规则专用模块名
        PATH_SEMANTIC_REVIEW_VALIDATOR,  # 正式语义审查模块路径
    )  # 语义审查模块规格

    # 规格不可用时阻断审查诊断，禁止退回不完整规则。
    if obj_specification is None or obj_specification.loader is None:

        # 明确报告缺失的规则模块，便于定位部署资产不完整。
        raise ImportError("> ERR: [Python] 无法加载 semantic_review_validator.py。")

    # 根据已验证规格创建本轮独享的语义审查模块。
    module_validator = importlib.util.module_from_spec(obj_specification)  # 待执行语义审查模块

    # 执行正式模块源码，使审查和历史图规则可供聚合入口调用。
    obj_specification.loader.exec_module(module_validator)

    # 返回已初始化模块供验证入口和现有外部调用方复用。
    return module_validator

# 加载一次正式模块，确保所有兼容导出共享同一实现。
MODULE_SEMANTIC_REVIEW_VALIDATOR = load_semantic_review_validator()  # 已初始化语义审查模块

# 恢复写入前单条记录的正式 schema 验证入口。
validate_review_record_schema = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_review_record_schema  # 审查候选结构验证器

# 恢复审查事实与证据集合的确定性摘要入口。
calculate_semantic_review_hash = MODULE_SEMANTIC_REVIEW_VALIDATOR.calculate_semantic_review_hash  # 语义审查哈希计算器

# 恢复证据登记表身份集合提取入口。
collect_evidence_ids = MODULE_SEMANTIC_REVIEW_VALIDATOR.collect_evidence_ids  # 有效证据身份收集器

# 恢复技术特征章节和证据闭包判定入口。
feature_has_support_closure = MODULE_SEMANTIC_REVIEW_VALIDATOR.feature_has_support_closure  # 特征支持闭包判定器

# 恢复技术特征登记表的完整性验证入口。
validate_feature_registry = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_feature_registry  # 特征登记表验证器

# 恢复代理审查目标解析入口。
resolve_review_target = MODULE_SEMANTIC_REVIEW_VALIDATOR.resolve_review_target  # 代理审查目标解析器

# 恢复人工确认目标解析入口。
resolve_human_confirmation_target = MODULE_SEMANTIC_REVIEW_VALIDATOR.resolve_human_confirmation_target  # 人工确认目标解析器

# 恢复活动审查记录按目标归并入口。
collect_active_review_records = MODULE_SEMANTIC_REVIEW_VALIDATOR.collect_active_review_records  # 活动记录索引器

# 恢复代理审查覆盖范围和哈希验证入口。
validate_agent_review_records = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_agent_review_records  # 代理记录验证器

# 恢复人工确认覆盖范围和哈希验证入口。
validate_human_confirmation_records = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_human_confirmation_records  # 人工记录验证器

# 恢复记录集合到身份域的归一入口。
review_collection_domain = MODULE_SEMANTIC_REVIEW_VALIDATOR.review_collection_domain  # 审查身份域解析器

# 恢复单条 supersession 双向链接验证入口。
validate_supersession_record = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_supersession_record  # 直接历史链接验证器

# 恢复唯一活动末端到全部历史的可达性验证入口。
validate_history_reachability = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_history_reachability  # 历史图可达性验证器

# 恢复全局身份唯一性、活动目标和历史图闭包入口。
validate_record_audit_invariants = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_record_audit_invariants  # 审计历史不变量验证器

# 验证嵌入式语义审查的覆盖维度、裁决和内容哈希。
def validate_semantic_review(
    dict_model: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """验证 Model 4.0 嵌入式代理审查和人工确认。

    参数：
    - `dict_model`：当前版本四模型。
    - `dict_claims_map`：与当前模型共同交付的实时权利要求映射。

    返回：
    - `list[dict[str, str]]`：缺失覆盖、过期哈希和确认缺口 blockers。

    异常：
    - 无。
    """

    # 审查容器缺失时使用独立代码阻断。
    obj_review = dict_model.get("semantic_review")  # 原始语义审查容器

    # 非对象审查无法形成权威记录。
    if not isinstance(obj_review, Mapping):

        # 缺失嵌入式审查是明确的版本四 blocker。
        return [
            build_blocker(
                "REV004",
                "Model 4.0 缺少 semantic_review",
                "在输出模型内记录代理审查和人工确认",
            )
        ]

    # 先执行跨集合全局身份、活动目标和历史闭包检查。
    list_audit_findings = validate_record_audit_invariants(obj_review)  # 当前记录审计不变量 findings

    # 验证当前活动代理审查并取得有效覆盖。
    tuple_agent_result = validate_agent_review_records(  # 代理审查发现与有效目标
        dict_model,  # 提供全部代理审查目标事实
        obj_review.get("agent_reviews", []),  # 当前代理审查原始数组
    )

    # 拆出代理审查发现供后续继续追加。
    list_findings = [*list_audit_findings, *tuple_agent_result[0]]  # 当前代理审查及审计不变量发现

    # 拆出有效代理目标供覆盖闭包比较。
    set_valid_targets = tuple_agent_result[1]  # 当前有效代理目标

    # 建立章节和特征的全部必审目标。
    set_required_targets = {
        ("section", str(dict_section.get("id")))  # 当前章节审查目标
        for dict_section in dict_model.get("sections", [])  # 建立必审章节目标
        if isinstance(dict_section, Mapping) and dict_section.get("id")  # 必审目标排除损坏章节
    }  # 全部章节审查目标

    # 把全部稳定特征追加到必审目标集合。
    set_required_targets.update(
        {
            ("feature", str(dict_feature.get("feature_id")))  # 当前特征审查目标
            for dict_feature in dict_model.get("feature_registry", [])  # 遍历稳定特征
            if isinstance(dict_feature, Mapping) and dict_feature.get("feature_id")  # 保留有效特征
        }
    )

    # 每个缺失目标形成可定位 blocker。
    for tuple_target_key in sorted(set_required_targets - set_valid_targets):

        # 消息保留目标类型和稳定编号。
        list_findings.append(
            build_blocker(
                "REV004",
                f"缺少有效语义审查:{tuple_target_key[0]}:{tuple_target_key[1]}",
                "记录五维 pass/revise/block 审查并嵌入输出模型",
            )
        )

    # 验证当前活动人工确认并合并哈希发现。
    tuple_human_result = validate_human_confirmation_records(  # 人工确认发现与有效目标
        dict_model,  # 提供全部人工确认目标事实
        obj_review.get("human_confirmations", []),  # 当前人工确认原始数组
        dict_claims_map,  # 提供独立项实时 feature_ids 和证据闭包
    )

    # 拆出人工确认发现并并入统一列表。
    list_human_findings = tuple_human_result[0]  # 当前人工确认发现

    # 拆出有效人工目标供逐项确认闭包使用。
    set_confirmation_targets = tuple_human_result[1]  # 当前有效人工目标

    # 合并人工确认阶段的目标和摘要问题。
    list_findings.extend(list_human_findings)

    # 每个受管数据事实必须由人逐项确认。
    for dict_data_record in dict_model.get("data_registry", []):

        # 只处理具有稳定 data_id 的事实。
        if isinstance(dict_data_record, Mapping) and dict_data_record.get("data_id"):

            # 当前事实没有有效确认时阻断。
            if ("data", str(dict_data_record["data_id"])) not in set_confirmation_targets:

                # 定量、实验和对比事实共用逐项确认规则。
                list_findings.append(
                    build_blocker(
                        "HUM001",
                        f"受管事实缺少人工确认:{dict_data_record['data_id']}",
                        "逐项确认定量、实验或对比事实",
                    )
                )

    # AI 适用性无论结论为何都必须由人确认。
    if ("ai_applicability", "model") not in set_confirmation_targets:

        # 当前任务要求形成通用人工确认。
        list_findings.append(
            build_blocker(
                "HUM002",
                "AI 适用性缺少人工确认",
                "人工确认 applicable、not_applicable 或 pending",
            )
        )

    # 代理审查待办必须显式清空。
    if obj_review.get("pending_reviews"):

        # 未关闭代理待办不能进入完成态。
        list_findings.append(
            build_blocker(
                "REV006",
                "semantic_review.pending_reviews 尚未清空",
                "完成活动审查后刷新待办状态",
            )
        )

    # 人工确认待办必须显式清空。
    if obj_review.get("pending_confirmations"):

        # 未关闭人工待办不能进入完成态。
        list_findings.append(
            build_blocker(
                "HUM005",
                "semantic_review.pending_confirmations 尚未清空",
                "完成人工确认后刷新待办状态",
            )
        )

    # 迁移工件在 state=pending 时始终保持阻断。
    obj_migration = dict_model.get("migration")  # 当前模型迁移元数据

    # pending 表示结构转换后尚未完成语义审查。
    if isinstance(obj_migration, Mapping) and obj_migration.get("state") == "pending":

        # 要求完成迁移审查后再更新权威状态。
        list_findings.append(
            build_blocker(
                "MIG001",
                "Model 4.0 迁移仍处于 pending",
                "完成特征映射和全部审查后将迁移状态更新为 complete",
            )
        )

    # 返回所有嵌入式审查和确认问题。
    return list_findings

# 从 Model 4.0 特征闭包派生 claims map 支撑状态。
def validate_claims_map(
    dict_claims_map: Mapping[str, Any],
    dict_model: Mapping[str, Any],
) -> list[dict[str, str]]:
    """验证 claims map 3.0 的稳定特征引用和派生支撑状态。

    参数：
    - `dict_claims_map`：待验证权利要求映射。
    - `dict_model`：提供章节、证据和特征登记表的版本四模型。

    返回：
    - `list[dict[str, str]]`：版本、schema、支撑闭包和人工确认 blockers。

    异常：
    - claims schema 缺失或损坏时由底层异常上抛。
    """

    # 旧 claims map 必须显式迁移，不能由运行时兼容解释。
    list_findings: list[dict[str, str]] = []  # 权利要求映射 findings

    # 版本不符时登记稳定迁移代码并继续汇总内容问题。
    if dict_claims_map.get("contract_version") != "3.0":

        # 上层可依据同一代码调用显式迁移入口。
        list_findings.append(
            build_blocker(
                "MIGRATION_REQUIRED",
                "claims map 不是版本3.0",
                "运行 migrate_model_contract.py 显式迁移",
            )
        )

    # 使用 Draft 2020-12 执行 claims map 结构合同。
    dict_schema = load_schema(PATH_CLAIMS_SCHEMA)  # 版本三权利要求映射合同

    # 创建实例验证器并稳定排序错误。
    obj_validator = Draft202012Validator(dict_schema)  # 权利要求映射实例验证器

    # schema 错误均进入 blocker 报告。
    list_schema_errors = sorted(  # 按实例路径排序的映射结构错误
        obj_validator.iter_errors(dict(dict_claims_map)),  # 当前 claims 结构错误
        key=lambda obj_error: list(obj_error.absolute_path),  # 依据嵌套实例路径排序
    )

    # 把 schema 失败转换为统一结构。
    list_findings.extend(
        [
            build_blocker(
                "CLM_SCHEMA",
                (
                    "claims map schema 失败:"
                    f"{'/'.join(str(obj_part) for obj_part in obj_error.absolute_path) or '<root>'}:"
                    f"{obj_error.message}"
                ),
                "按 claims_map.schema.json 修复映射",
            )
            for obj_error in list_schema_errors
        ]
    )

    # schema finding 已保留；后续语义检查使用安全副本继续汇总。
    module_safe_types = load_model_safe_types()  # Model 与 claims 共用规整职责

    # 先收敛 claims 嵌套数组，保证坏输入仍能执行引用闭包检查。
    dict_claims_map = module_safe_types.normalize_claims_map(dict_claims_map)  # 可继续执行支撑闭包诊断的权利要求副本

    # 再收敛 Model 4 嵌套容器，保证全部语义规则可累计 finding。
    dict_model = module_safe_types.normalize_model(dict_model)  # type-total 模型副本

    # 建立实际章节、证据和特征索引，支撑状态只从这些事实派生。
    set_section_ids = {
        str(dict_section.get("id"))  # claims 支撑闭包章节编号
        for dict_section in dict_model.get("sections", [])  # 建立 claims 章节集合
        if isinstance(dict_section, Mapping) and dict_section.get("id")  # 支撑闭包保留有效章节
    }  # 模型章节编号

    # 建立章节到证据的精确绑定，禁止只凭全局证据存在性推断支撑。
    dict_section_evidence = {
        str(dict_section.get("id")): {  # claims 章节稳定编号
            str(obj_evidence_id)  # 当前章节引用证据编号
            for obj_evidence_id in dict_section.get("evidence_ids", [])  # 提取 claims 章节证据
        }
        for dict_section in dict_model.get("sections", [])  # 建立 claims 章节索引
        if isinstance(dict_section, Mapping) and dict_section.get("id")  # claims 索引排除损坏章节
    }  # claims 支撑章节证据索引

    # 证据编号只来自模型登记表。
    set_evidence_ids = collect_evidence_ids(dict_model.get("evidence_registry"))  # 模型证据编号

    # 特征索引允许 claims map 通过稳定 ID 查询。
    dict_features = {
        str(dict_feature.get("feature_id")): dict_feature  # 当前稳定特征索引项
        for dict_feature in dict_model.get("feature_registry", [])  # 建立 claims 特征索引
        if isinstance(dict_feature, Mapping) and dict_feature.get("feature_id")  # claims 索引保留有效特征
    }  # 稳定技术特征索引

    # 人工确认集合用于独立项特征集检查。
    obj_semantic_review = dict_model.get("semantic_review", {})  # 模型审查容器

    # 读取独立项确认记录，后续依据当前 feature_ids 和证据集合复算摘要。
    list_human_confirmations = (
        obj_semantic_review.get("human_confirmations", [])  # 已嵌入人工确认数组
        if isinstance(obj_semantic_review, Mapping)  # 审查容器类型有效
        else []  # 损坏审查容器视为空确认集合
    )  # 当前模型人工确认记录

    # 逐项根据特征、章节和证据重新计算支撑状态。
    for dict_claim in dict_claims_map.get("claims", []):

        # 非对象项由 schema 报告，本层不重复读取字段。
        if not isinstance(dict_claim, Mapping):

            # 跳过损坏记录。
            continue

        # 读取当前权利要求稳定特征集合。
        list_feature_ids = [
            str(obj_id)  # 当前权利要求引用的规范特征编号
            for obj_id in dict_claim.get("feature_ids", [])  # 遍历权利要求特征
        ]  # 当前权利要求特征集合

        # 记录无法通过三层闭包的特征编号。
        list_unsupported_feature_ids: list[str] = []  # 当前权利要求无支撑特征

        # 每个特征必须存在且具有真实章节、证据和效果。
        for str_feature_id in list_feature_ids:

            # 取回当前稳定特征记录。
            dict_feature = dict_features.get(str_feature_id)  # 当前技术特征记录

            # 不存在的特征直接列为无支撑。
            if dict_feature is None:

                # 保存悬空 feature_id 供修复。
                list_unsupported_feature_ids.append(str_feature_id)

                # 继续检查剩余特征。
                continue

            # 任一闭包条件失败都将特征标为无支撑。
            if not feature_has_support_closure(
                dict_feature,
                set_section_ids,
                set_evidence_ids,
                dict_section_evidence,
            ):

                # 保留当前 feature_id 供 claims map 精确补料。
                list_unsupported_feature_ids.append(str_feature_id)

        # 至少一个稳定特征且所有特征闭包成立才派生为 supported。
        str_derived_status = (
            "supported"  # 全部特征闭包成立
            if list_feature_ids and not list_unsupported_feature_ids  # 存在特征且无缺口
            else "unsupported"  # 缺少特征或存在闭包缺口
        )  # 从特征闭包派生的支撑状态

        # 输入状态与派生状态不一致，或独立项实际无支撑时都形成 blocker。
        if dict_claim.get("support_status") != str_derived_status or (
            str(dict_claim.get("claim_type", "")).startswith("independent_")
            and str_derived_status != "supported"
        ):

            # 上层不得信任输入 support_status。
            list_findings.append(
                build_blocker(
                    "CLM001",
                    (
                        f"权利要求{dict_claim.get('claim_no', '')}"
                        f"派生支撑状态为{str_derived_status}:"
                        f"缺口{list_unsupported_feature_ids}"
                    ),
                    "修复 feature_id、章节和证据闭包后重新生成 claims map",
                )
            )

        # 每个独立项特征集都必须由人确认。
        if str(dict_claim.get("claim_type", "")).startswith("independent_"):

            # 权利要求编号作为通用人工确认目标。
            str_claim_id = str(dict_claim.get("claim_no", ""))  # 当前独立项确认编号

            # 独立项确认摘要同时绑定特征集合和这些特征的证据并集。
            list_claim_evidence_ids = sorted(  # 当前独立项全部研发证据
                {
                    str(obj_evidence_id)  # 当前特征绑定的规范证据编号
                    for str_feature_id in list_feature_ids  # 遍历独立项特征
                    for obj_evidence_id in dict_features.get(  # 读取当前特征的证据数组
                        str_feature_id,  # 当前独立项稳定特征编号
                        {},  # 缺失特征使用空映射
                    ).get("evidence_ids", [])  # 遍历当前特征证据
                }
            )  # 当前独立项证据并集

            # 摘要同时绑定独立项特征集合和证据并集。
            str_expected_claim_hash = calculate_semantic_review_hash(  # 当前独立项确认摘要
                "independent_claim",  # 独立权利要求确认目标类型
                str_claim_id,  # 当前独立权利要求编号
                list_feature_ids,  # 当前独立项稳定特征集合
                list_claim_evidence_ids,  # 绑定确认时可见的证据范围
                str(dict_model.get("contract_version", "")),  # 当前合同版本
            )

            # 只有摘要新鲜且明确 confirm 的记录有效。
            bool_confirmed = (
                any(  # 查找当前独立项的有效人工确认
                    isinstance(dict_item, Mapping)  # 当前确认记录必须是映射
                    and dict_item.get("confirmation_type") == "independent_claim_feature_set"  # 事项类别匹配
                    and dict_item.get("target_type") == "independent_claim"  # 目标类型匹配
                    and str(dict_item.get("target_id", "")) == str_claim_id  # 目标编号匹配
                    and dict_item.get("decision") == "confirm"  # 决定明确确认
                    and dict_item.get("target_hash") == str_expected_claim_hash  # 摘要仍然新鲜
                    for dict_item in list_human_confirmations  # 遍历模型人工确认
                )
                if isinstance(list_human_confirmations, list)  # 确认容器类型有效
                else False  # 损坏容器不能形成有效确认
            )  # 当前独立项是否具有有效人工确认

            # 缺失或过期人工确认时不能进入最终权利要求。
            if not bool_confirmed:

                # Task 1 只实现通用确认器，不决定具体保护范围。
                list_findings.append(
                    build_blocker(
                        "HUM003",
                        f"独立权利要求特征集缺少人工确认:{str_claim_id}",
                        "逐项确认独立项包含的 feature_ids",
                    )
                )

    # 返回 schema、支撑和人工确认问题。
    return list_findings

# 把畸形核心容器替换为安全空值，供深层验证继续汇总。
def normalize_model_containers(
    dict_model: Mapping[str, Any],
) -> dict[str, Any]:
    """规范化版本四模型的核心容器类型。

    参数：
    - `dict_model`：已经过 schema 校验但可能含畸形值的模型。

    返回：
    - `dict[str, Any]`：可由深层验证器安全迭代的模型副本。

    异常：
    - 无。
    """

    # 统一委托独立模块规整全部嵌套容器。
    module_safe_types = load_model_safe_types()  # 当前安全容器模块

    # 返回可供全部深层验证器消费的模型副本。
    return module_safe_types.normalize_model(dict_model)

# 统一执行 Model 4.0 的 schema、章节、证据、公式、特征和审查合同。
def validate_structured_model(
    dict_model: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """验证 Model 4.0 结构化交底模型的跨对象闭包。

    参数：
    - `dict_model`：Model 4.0 结构化交底模型。
    - `dict_claims_map`：与模型共同交付的实时权利要求映射。

    返回：
    - `list[dict[str, str]]`：现有验证报告可直接消费的 blocker findings。

    异常：
    - 正式章节合同或公式验证模块不可读时由底层异常上抛。
    """

    # 旧模型必须显式迁移，禁止通过兼容回退继续形成确认稿。
    list_version_findings: list[dict[str, str]] = []  # Model 4.0 版本状态发现

    # 只有版本四合同可以进入正式验证。
    if dict_model.get("contract_version") != "4.0":

        # 记录上层可执行迁移器识别的稳定 blocker。
        list_version_findings.append(
            build_blocker(
                "MIGRATION_REQUIRED",
                "结构化模型不是版本4.0",
                "运行 migrate_model_contract.py 显式迁移",
            )
        )

    # Draft 2020-12 schema 在运行时实际执行，失败保持 blocker。
    list_schema_findings = validate_model_schema(dict_model)  # 版本四模型结构失败

    # 深层验证使用安全副本，schema findings 仍保留原始类型错误。
    dict_model = normalize_model_containers(dict_model)  # 容器类型安全的模型副本

    # 从正式资产读取章节要求，防止代码与合同文件发生枚举漂移。
    set_required_ids = load_required_section_ids()  # 合同要求章节标识

    # 章节检查同时返回实际标识，供后续交叉引用闭包复用。
    tuple_section_result = validate_sections(dict_model.get("sections"), set_required_ids)  # 章节检查结果

    # 分离章节 findings 与实际标识集合，使汇总顺序清晰稳定。
    list_findings = list_version_findings + list_schema_findings + list(tuple_section_result[0])  # 统一结构化 findings

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

    # 特征登记表必须形成非空内容、章节、证据和技术效果闭包。
    list_findings.extend(validate_feature_registry(dict_model))

    # 嵌入式审查必须覆盖全部章节和稳定特征，并保持哈希新鲜。
    list_findings.extend(validate_semantic_review(dict_model, dict_claims_map))

    # 返回统一 findings；任一条都会使现有状态机构建 blocked。
    return list_findings
