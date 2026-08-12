"""构建来源、特征、证据和嵌入式审查分离的版本四专利交底模型。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 标准库负责深复制 JSON 数据并生成跨运行稳定的公式摘要。
import hashlib
import importlib.util
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# 固定正式章节合同路径，使生成端与验证端读取同一份章节顺序和标题。
PATH_SECTION_CONTRACT = Path(__file__).resolve().parents[3] / "assets" / "section_contract.json"  # 章节合同资产路径

# 固定共享特征身份模块路径，供正文模型与 claims map 统一编号。
PATH_FEATURE_IDENTITY = Path(__file__).resolve().parents[1] / "support" / "feature_identity.py"  # 稳定特征身份模块路径

# 从共享模块加载唯一的稳定特征身份实现。
def load_feature_identity_module() -> Any:
    """加载稳定特征身份模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行源码的共享特征身份模块。

    异常：
    - `ImportError`：模块规格或加载器缺失时抛出。
    """

    # 根据正式文件路径创建共享身份模块加载规格。
    obj_specification = importlib.util.spec_from_file_location(  # 共享身份模块加载规格
        "readable_patent_feature_identity_for_disclosure",  # 正文模型侧隔离模块名称
        PATH_FEATURE_IDENTITY,  # 共享身份模块正式路径
    )

    # 加载规格或加载器缺失时立即阻断，禁止正文模型回退到位置编号。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出符合项目日志合同的明确导入错误。
        raise ImportError("> ERR: [Python] 无法加载 support/feature_identity.py。")

    # 根据已验证规格创建本次调用独享的模块对象。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 共享特征身份模块对象

    # 执行共享模块源码，使稳定身份函数可用。
    obj_specification.loader.exec_module(obj_module)

    # 返回已加载模块，调用方只使用其中的唯一公共身份函数。
    return obj_module

# 暴露共享身份函数，供生成器和测试使用同一公共合同。
def build_stable_feature_id(dict_feature: Mapping[str, Any]) -> str:
    """调用共享实现生成稳定特征编号。

    参数：
    - `dict_feature`：包含来源身份字段的技术特征记录。

    返回：
    - `str`：共享模块生成的稳定特征编号。

    异常：
    - `ImportError`：共享身份模块无法加载时抛出。
    """

    # 返回共享实现结果，禁止在正文模型侧复制摘要规则。
    return str(load_feature_identity_module().build_stable_feature_id(dict_feature))

# 复制 JSON 兼容对象，确保构建过程不会修改调用方持有的数据。
def copy_json_value(obj_value: Any) -> Any:
    """通过 JSON 往返复制可序列化对象。

    参数：
    - `obj_value`：待复制的 JSON 兼容对象。

    返回：
    - `Any`：与输入语义相同但无共享可变引用的新对象。

    异常：
    - `TypeError`：输入包含不可序列化值时由编码器上抛。
    """

    # JSON 往返同时限定正式模型只能保存可落盘的数据类型。
    str_serialized = json.dumps(obj_value, ensure_ascii=False)  # 临时 JSON 文本

    # 返回独立对象，防止添加内部哈希时污染上游事实记录。
    return json.loads(str_serialized)

# 对排除旧哈希后的公式语义记录计算稳定 SHA-256。
def calculate_formula_hash(dict_formula: Mapping[str, Any]) -> str:
    """计算公式记录的规范化内容摘要。

    参数：
    - `dict_formula`：待绑定正文和图片的公式语义记录。

    返回：
    - `str`：不含既有 `content_hash` 字段的 SHA-256。

    异常：
    - `TypeError`：记录包含不可序列化值时由编码器上抛。
    """

    # 排除派生哈希本身，保证重复构建不会形成递归变化。
    dict_hash_payload = {str_key: obj_value for str_key, obj_value in dict_formula.items() if str_key != "content_hash"}  # 摘要输入记录

    # 排序键和紧凑分隔符共同固定跨运行的规范文本边界。
    str_canonical = json.dumps(dict_hash_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)  # 规范公式文本

    # UTF-8 编码将规范文本转换成哈希算法要求的确定字节序列。
    bytes_canonical = str_canonical.encode("utf-8")  # 规范公式字节

    # 返回十六进制摘要，供公式对象、登记表和正文引用共同绑定。
    return hashlib.sha256(bytes_canonical).hexdigest()

# 为每条公式复制语义字段并加入由内容派生的稳定摘要。
def build_formula_registry(list_formulas: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """构建不修改输入的公式登记表。

    参数：
    - `list_formulas`：已经由事实层确认的公式记录序列。

    返回：
    - `list[dict[str, Any]]`：带稳定 `content_hash` 的新记录列表。

    异常：
    - `TypeError`：输入记录不可 JSON 序列化时由复制或哈希逻辑上抛。
    """

    # 新列表隔离模型内部派生字段与调用方原始事实对象。
    list_registry: list[dict[str, Any]] = []  # 带哈希公式登记表

    # 按输入顺序处理公式，保持正文编号和材料顺序稳定。
    for dict_formula in list_formulas:

        # 深复制当前记录后再增加内部追踪字段。
        dict_formula_copy = copy_json_value(dict_formula)  # 当前公式独立副本

        # 内容摘要绑定复制前后的相同语义，不包含旧摘要字段。
        dict_formula_copy["content_hash"] = calculate_formula_hash(dict_formula_copy)  # 当前公式内容哈希

        # 登记完整副本，后续修改不会影响调用方输入对象。
        list_registry.append(dict_formula_copy)

    # 返回按输入顺序构建的公式登记表。
    return list_registry

# 从既有正文证据映射派生稳定特征身份，不补写材料未声明的技术效果。
def build_feature_registry(
    dict_evidence_map: Mapping[str, Any],
    list_sections: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """把正文特征映射转换为 Model 4.0 稳定特征登记表。

    参数：
    - `dict_evidence_map`：正文生成链已经形成的技术特征和精确证据映射。
    - `list_sections`：可选的真实章节记录，用于建立章节到证据闭包。

    返回：
    - `list[dict[str, Any]]`：不猜测缺失技术效果的稳定特征记录。

    异常：
    - 无。
    """

    # 结果表只保留首个语义完全相同的来源特征。
    list_registry: list[dict[str, Any]] = []  # 稳定技术特征登记表

    # 摘要索引同时承担重复去重和不同内容碰撞检测。
    dict_registry_by_id: dict[str, dict[str, Any]] = {}  # feature_id 到规范记录的索引

    # 按来源映射顺序输出记录，但身份只由当前特征的稳定来源字段决定。
    for dict_feature in dict_evidence_map.get("features", []):

        # 损坏的非对象记录不具备技术特征语义。
        if not isinstance(dict_feature, Mapping):

            # 跳过损坏记录，后续模型门禁会报告覆盖缺口。
            continue

        # 读取材料链已提供的真实技术特征正文。
        str_text = str(dict_feature.get("feature", "")).strip()  # 当前技术特征正文

        # 空正文不能获得稳定 feature_id。
        if not str_text:

            # 跳过空占位，禁止生成伪技术特征。
            continue

        # 先读取特征的明确证据，章节绑定必须由实际章节证据反向派生。
        list_evidence_ids = [  # 当前特征明确证据编号列表
            str(obj_id)  # 当前特征证据编号
            for obj_id in dict_feature.get("support_ids", [])  # 遍历材料链声明的证据
        ]

        # 只绑定实际引用特征证据的章节，禁止使用固定章节占位。
        list_section_ids = [  # 当前特征真实章节编号列表
            str(dict_section.get("id", ""))  # 当前真实章节编号
            for dict_section in list_sections or []  # 遍历本轮真实章节
            if isinstance(dict_section, Mapping)  # 排除损坏章节值
            and {  # 构造当前章节证据集合
                str(obj_id)  # 当前章节证据编号
                for obj_id in dict_section.get("evidence_ids", [])  # 遍历章节证据
            }  # 完成章节证据集合
            & set(list_evidence_ids)  # 要求章节实际引用特征证据
        ]

        # 规范记录用于比较重复来源是否真的是同一技术特征。
        dict_record = {
            "feature_id": build_stable_feature_id(dict_feature),  # 绑定完整规范内容的稳定身份
            "text": str_text,  # 当前技术特征原文
            "section_ids": list_section_ids,  # 实际引用特征证据的章节
            "evidence_ids": list_evidence_ids,  # 当前特征证据引用
            "technical_effects": [  # 当前特征已登记技术效果
                str(obj_effect)  # 当前非空技术效果文本
                for obj_effect in dict_feature.get(  # 读取新版或兼容旧版效果字段
                    "technical_effects",  # Model 4 技术效果字段
                    dict_feature.get("effects", []),  # 兼容旧输入效果字段
                )
                if str(obj_effect).strip()  # 排除空白效果
            ],
        }  # 当前稳定技术特征记录

        # 读取相同摘要已经登记的来源。
        dict_existing = dict_registry_by_id.get(dict_record["feature_id"])  # 同摘要既有记录

        # 完全相同的重复输入保持首次位置并跳过后续副本。
        if dict_existing == dict_record:

            # 相同内容摘要已经保留首次出现位置，无需重复登记。
            continue

        # 不同语义共享摘要说明身份函数发生碰撞，生成阶段必须停线。
        if dict_existing is not None:

            # 报告完整身份并拒绝产生无法区分的特征登记。
            raise ValueError(
                "> ERR: [Python] 稳定 feature_id 碰撞:"
                f"{dict_record['feature_id']}"
            )

        # 首次出现的摘要进入稳定索引和输出顺序。
        dict_registry_by_id[dict_record["feature_id"]] = dict_record  # 当前摘要对应的唯一特征

        # 保持输入首次出现顺序供后续渲染稳定消费。
        list_registry.append(dict_record)

    # 返回保持来源顺序的稳定特征登记表。
    return list_registry

# 组合三个已确认事实域，形成 Markdown 与 DOCX 共同消费的中间真相层。
def build_disclosure_model(
    list_sections: Sequence[Mapping[str, Any]],
    list_formulas: Sequence[Mapping[str, Any]],
    dict_evidence_map: Mapping[str, Any],
    dict_registries: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """构建版本四结构化专利交底模型。

    参数：
    - `list_sections`：按合同顺序排列的章节内容。
    - `list_formulas`：已确认的公式语义记录。
    - `dict_evidence_map`：章节、步骤或公式到来源编号的映射。
    - `dict_registries`：来源、数据、术语、附图、交叉引用和待办登记表集合。

    返回：
    - `dict[str, Any]`：不共享输入可变对象的版本四模型。

    异常：
    - `TypeError`：任一输入不是 JSON 兼容数据时由复制逻辑上抛。
    """

    # 未传入附加登记表时保留显式空结构，供验证层判断是否需要补齐。
    dict_safe_registries = dict_registries if dict_registries is not None else {}  # 可读取附加登记表

    # 原生输入摘要绑定本次构建消费的全部事实域，不使用固定占位摘要。
    dict_native_input = {
        "sections": list_sections,  # 当前十一章节事实
        "formulas": list_formulas,  # 当前公式语义事实
        "evidence_registry": dict_evidence_map,  # 当前证据映射
        "registries": dict_safe_registries,  # 当前附加登记表
    }  # 原生构建摘要载荷

    # 规范 JSON 固定跨运行摘要输入。
    str_native_input = json.dumps(dict_native_input, ensure_ascii=False, separators=(",", ":"), sort_keys=True)  # 原生构建规范文本

    # 空技术效果需要显式人工确认，不能只依赖后置 validator 报错。
    bool_pending_effects = any(  # 是否至少一个技术特征仍缺少可确认效果
        isinstance(dict_feature, Mapping)  # 当前特征必须可解释
        and not dict_feature.get("technical_effects")  # 当前特征尚无技术效果
        for dict_feature in dict_safe_registries.get("feature_registry", [])  # 当前特征登记
    )  # 是否存在待确认技术效果

    # 人工待办从模型真实事实域派生，避免无数据案件永久等待。
    list_pending_confirmations = [
        "independent_claim_feature_sets",  # 独立权利要求特征集确认
        "ai_applicability",  # AI 规则适用性确认
    ]  # 原生模型必需人工确认类别

    # 只有实际存在受管事实时才登记该类别。
    if dict_safe_registries.get("data_registry"):

        # 将受管事实类别放在人工确认队列首位。
        list_pending_confirmations.insert(0, "governed_facts")

    # 技术效果缺失时通过 recorder 专用确认目标关闭。
    if bool_pending_effects:

        # 追加逐特征技术效果确认类别。
        list_pending_confirmations.append("feature_technical_effects")

    # 每类事实分别复制，避免渲染或验证阶段反向污染登记表。
    dict_model = {
        "contract_version": "4.0",  # 当前结构化合同版本
        "source_manifest": copy_json_value(dict_safe_registries.get("source_manifest", [])),  # 材料来源及实际用途登记表
        "evidence_registry": copy_json_value(dict_evidence_map),  # 证据记录与精确引用关系
        "data_registry": copy_json_value(dict_safe_registries.get("data_registry", [])),  # 数值事实及人工批准状态
        "sections": copy_json_value(list_sections),  # 章节事实副本
        "formula_registry": build_formula_registry(list_formulas),  # 公式事实及内容绑定值
        "term_registry": copy_json_value(dict_safe_registries.get("term_registry", [])),  # 术语定义与允许别名
        "figure_registry": copy_json_value(dict_safe_registries.get("figure_registry", [])),  # 附图来源与正文绑定记录
        "cross_references": copy_json_value(dict_safe_registries.get("cross_references", [])),  # 章节显式交叉引用
        "pending_items": copy_json_value(dict_safe_registries.get("pending_items", [])),  # 尚未关闭的人工处理项
        "feature_registry": copy_json_value(dict_safe_registries.get("feature_registry", [])),  # 稳定技术特征及支撑闭包
        "rule_applicability": copy_json_value(  # 复制 AI 专项规则适用性
            dict_safe_registries.get(  # 读取调用方提供的适用性状态
                "rule_applicability",  # AI 专项规则适用性键
                {"ai_applicability": "pending"},  # 未判定时保持待人工确认
            )
        ),  # AI 专项规则适用性
        "semantic_review": copy_json_value(  # 复制嵌入式语义审查状态
            dict_safe_registries.get(  # 读取调用方提供的嵌入式审查
                "semantic_review",  # 嵌入式审查登记表键
                {
                    "agent_reviews": [],  # 尚未嵌入代理审查
                    "human_confirmations": [],  # 尚未嵌入人工确认
                    "agent_review_history": [],  # 已被替代的代理审查历史
                    "human_confirmation_history": [],  # 已被替代的人工确认历史
                    "pending_reviews": ["sections", "feature_registry"],  # 待代理审查事实域
                    "pending_confirmations": list_pending_confirmations,  # 从真实事实域派生的人工待办
                },
            )
        ),  # 嵌入式代理审查和人工确认
        "migration": copy_json_value(  # 复制原生构建或显式迁移状态
            dict_safe_registries.get(  # 读取调用方提供的迁移审计信息
                "migration",  # 模型迁移状态键
                {
                    "state": "native",  # 当前模型由版本四生成器原生产出
                    "source_contract_version": "4.0",  # 原生输入合同版本
                    "input_sha256": hashlib.sha256(str_native_input.encode("utf-8")).hexdigest(),  # 原生输入摘要
                },
            )
        ),  # 原生或迁移来源状态
        "provenance": copy_json_value(  # 初始案件来源链副本
            dict_safe_registries.get(  # 优先采用调用方提供的来源链
                "provenance",  # 来源链登记字段
                {
                    "state": "pending",  # 等待 pipeline 完成案件封印
                    "artifact_role": "initial",  # 初始模型工件角色
                    "producer": "model4_pipeline",  # 封印后允许的生产者
                    "case_id": "pending",  # 等待真实案件身份
                    "parent_model_sha256": "0" * 64,  # 等待封印前模型摘要
                    "root_model_sha256": "0" * 64,  # 等待全链根摘要
                    "draft_sha256": "0" * 64,  # 等待正式正文摘要
                    "preview_sha256": "0" * 64,  # 等待确认预览摘要
                    "claims_sha256": "0" * 64,  # 等待 Claims Map 3 摘要
                    "chain": [],  # 初始模型尚无审查跳转
                },
            )
        ),  # pipeline 在 claims 生成后封印案件来源链
    }  # 版本四结构化交底模型

    # 返回完整模型，调用方负责落盘与执行 schema/语义验证。
    return dict_model

# 将旧版证据索引转换为版本二验证器消费的 records 结构。
def normalize_evidence_map(dict_evidence_map: Mapping[str, Any]) -> dict[str, Any]:
    """规范化证据映射而不丢失旧版字段。

    参数：
    - `dict_evidence_map`：起草阶段生成的来源证据映射。

    返回：
    - `dict[str, Any]`：包含版本二 `records` 的独立证据映射。

    异常：
    - `TypeError`：输入包含不可 JSON 序列化值时由复制逻辑上抛。
    """

    # 复制旧版对象，避免为版本二补充别名时污染既有 sidecar。
    dict_normalized = copy_json_value(dict_evidence_map)  # 独立证据映射副本

    # records 直接复用已生成的证据索引，保持来源编号和正文映射一致。
    dict_normalized["records"] = copy_json_value(dict_evidence_map.get("evidence_index", []))  # 版本二证据记录

    # 返回同时兼容旧版消费者和版本二验证器的证据对象。
    return dict_normalized

# 按证据类型筛选可用于当前章节的来源编号。
def select_evidence_ids(dict_evidence_map: Mapping[str, Any], tuple_kinds: tuple[str, ...]) -> list[str]:
    """选择指定类型的证据编号。

    参数：
    - `dict_evidence_map`：包含 evidence_index 的起草证据映射。
    - `tuple_kinds`：当前章节允许引用的证据类型。

    返回：
    - `list[str]`：保持证据登记顺序的编号列表。

    异常：
    - 无。
    """

    # 只返回真实登记且类型匹配的来源，禁止为补齐章节伪造证据编号。
    return [
        str(dict_record["id"])
        for dict_record in dict_evidence_map.get("evidence_index", [])
        if isinstance(dict_record, Mapping) and str(dict_record.get("kind", "")) in tuple_kinds
    ]

# 从起草上下文生成十一项叶子章节记录。
def build_section_records(
    dict_context: Mapping[str, Any],
    dict_evidence_map: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """把正文起草上下文映射为版本二章节记录。

    参数：
    - `dict_context`：标题、问题、步骤、模块、效果和现有技术摘要上下文。
    - `dict_evidence_map`：起草阶段生成的来源证据映射。

    返回：
    - `list[dict[str, Any]]`：按正式章节合同排序的十一项记录。

    异常：
    - `FileNotFoundError`：正式章节合同缺失时由读取逻辑上抛。
    - `json.JSONDecodeError`：章节合同损坏时由解析逻辑上抛。
    """

    # 从正式资产读取标题和顺序，避免生成器维护第二套章节枚举。
    dict_contract = json.loads(PATH_SECTION_CONTRACT.read_text(encoding="utf-8"))  # 正式章节合同

    # 规整各章节需要复用的正文片段，保持模型与 Markdown 使用同一上游事实。
    str_title = str(dict_context.get("title", ""))  # 发明名称

    # 主问题同时支撑背景缺点和发明目的章节。
    str_problem = str(dict_context.get("problem", ""))  # 主技术问题

    # 方法步骤保持上游顺序，供技术方案和实施方式共同复用。
    list_steps = list(dict_context.get("steps", []))  # 方法步骤

    # 装置模块与方法步骤共同构成完整技术方案。
    list_modules = list(dict_context.get("modules", []))  # 装置模块

    # 技术效果只复制上游已经分类通过的文本。
    list_effects = [str(obj_effect) for obj_effect in dict_context.get("effects", [])]  # 技术效果

    # 现有技术摘要只来自已核验的查新记录。
    list_prior = [str(obj_prior) for obj_prior in dict_context.get("prior_summaries", [])]  # 现有技术摘要

    # JSON 文本保留步骤和模块的结构边界，后续渲染器可无损读取。
    str_solution = json.dumps({"modules": list_modules, "steps": list_steps}, ensure_ascii=False)  # 技术方案内容

    # 每章内容只来自现有起草上下文，不在结构化层新增技术事实。
    dict_content_by_id = {  # 章节标识到正文事实的映射
        "1": str_title,  # 发明名称沿用已规范化标题
        "2": str_title,  # 技术领域沿用标题中的技术对象边界
        "3.1": "\n".join(list_prior),  # 最接近现有技术只使用核验摘要
        "3.2": "\n".join(list_prior + ([str_problem] if str_problem else [])),  # 对比已知方案与主问题
        "3.3": str_problem,  # 技术缺点直接复用已确认主问题
        "4.1": str_problem,  # 发明目的保持单一主问题
        "4.2": str_solution,  # 技术方案保留步骤和模块结构
        "4.3": "\n".join(list_effects),  # 技术效果只收录分类通过条目
        "5": "图1为方法流程图；图2为系统模块图。",  # 默认交付附图清单
        "6": str_solution,  # 实施方式沿用可执行方案事实
        "7": str_solution,  # 替代方式不添加未经材料确认的新方案
    }

    # 各章节只引用与用途相符的既有证据类型，附图章节不强制来源。
    dict_kinds_by_id = {  # 章节标识到允许证据类型的映射
        "1": ("solution",),  # 发明名称由主方案材料支撑
        "2": ("solution",),  # 技术领域同样由主方案材料支撑
        "3.1": ("prior_art",),  # 现有技术章节只引用查新记录
        "3.2": ("prior_art", "problem"),  # 问题机制同时关联查新与问题证据
        "3.3": ("problem",),  # 技术缺点由问题证据支撑
        "4.1": ("problem",),  # 发明目的由问题证据支撑
        "4.2": ("solution",),  # 技术方案由方案证据支撑
        "4.3": ("effect",),  # 技术效果只引用效果证据
        "5": (),  # 附图章节不强制材料来源
        "6": ("solution",),  # 实施过程复用方案证据
        "7": ("solution",),  # 等效替代仍需方案证据约束
    }

    # 按合同顺序组装章节，保证生成端与完整性验证端的标识完全一致。
    return [
        {
            "id": str(dict_section["id"]),
            "title": str(dict_section["title"]),
            "content": dict_content_by_id[str(dict_section["id"])],
            "evidence_ids": select_evidence_ids(dict_evidence_map, dict_kinds_by_id[str(dict_section["id"])]),
        }
        for dict_section in dict_contract["sections"]
    ]

# 从研究根目录读取人工确认的公式语义事实。
def load_confirmed_formula_facts(path_case_dir: Path) -> list[dict[str, Any]]:
    """读取案件研究根目录中的可选公式事实登记。

    参数：
    - `path_case_dir`：包含 case_config.json 的案件根目录。

    返回：
    - `list[dict[str, Any]]`：人工确认的公式语义记录；文件缺失时为空列表。

    异常：
    - `json.JSONDecodeError`：公式事实文件损坏时由解析器上抛。
    """

    # 研究根目录来自案件配置，禁止在技能源码中固化用户材料路径。
    dict_case_config = json.loads((path_case_dir / "case_config.json").read_text(encoding="utf-8"))  # 案件配置

    # 公式事实采用研究材料内固定文件名，便于人工审阅和版本控制。
    path_formula_facts = Path(str(dict_case_config["research_root"])) / "formula_facts.json"  # 公式事实文件路径

    # 没有人工确认登记时返回空列表，后续会为正文公式生成不完整记录并由门禁阻断。
    if not path_formula_facts.exists():

        # 明确返回空登记，让匹配器生成可定位的未确认记录。
        return []

    # 公式事实文件必须是数组，其他类型会使语义边界不明确。
    list_formula_facts: Any = json.loads(path_formula_facts.read_text(encoding="utf-8"))  # 公式事实原始对象

    # 顶层结构错误不能被静默转换为空登记表。
    if not isinstance(list_formula_facts, list):

        # 抛出明确类型错误，要求修复研究材料事实文件。
        raise TypeError("> ERR: [Python] formula_facts.json 顶层必须为数组。")

    # 返回独立记录，避免模型添加哈希时改写研究材料对象。
    return copy_json_value(list_formula_facts)

# 将正文公式块与人工确认事实一一匹配。
def match_formula_records(
    list_formula_blocks: Sequence[str],
    list_confirmed_facts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """为正文公式选择已确认语义，缺失时保留可阻断记录。

    参数：
    - `list_formula_blocks`：正文实际使用的公式表达式。
    - `list_confirmed_facts`：研究材料提供的人工确认公式记录。

    返回：
    - `list[dict[str, Any]]`：与正文公式顺序一致的登记记录。

    异常：
    - 无。
    """

    # 以去空白 LaTeX 文本建立精确匹配，禁止仅凭公式编号错配语义。
    dict_fact_by_latex = {str(dict_fact.get("latex", "")).strip(): dict_fact for dict_fact in list_confirmed_facts}  # 公式事实索引

    # 新列表保持正文公式顺序，不复用调用方可变容器。
    list_records: list[dict[str, Any]] = []  # 正文公式登记记录

    # 逐条正文公式查找确认事实，保持正文出现顺序和编号稳定。
    for int_index, str_formula_block in enumerate(list_formula_blocks, start=1):

        # 去除展示公式边界内的无意义首尾空白。
        str_latex = str(str_formula_block).strip()  # 当前正文公式文本

        # 只接受表达式完全一致的人工事实，避免错绑符号解释。
        dict_confirmed = dict_fact_by_latex.get(str_latex)  # 匹配的人工确认事实

        # 匹配成功时完整复制人工事实；缺失时只保留基础字段让语义门明确阻断。
        dict_record = copy_json_value(dict_confirmed) if dict_confirmed is not None else {  # 当前公式登记记录
            "formula_id": f"F{int_index:03d}",  # 按正文顺序生成可定位标识
            "display_number": str(int_index),  # 展示编号与正文顺序一致
            "latex": str_latex,  # 保留正文实际公式表达式
        }

        # 把当前记录加入与正文顺序一致的公式登记表。
        list_records.append(dict_record)

    # 返回与正文公式一一对应的记录，未确认语义不会被静默伪造。
    return list_records
