"""构建章节、公式和证据分离的版本二专利交底模型。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 标准库负责深复制 JSON 数据并生成跨运行稳定的公式摘要。
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# 固定正式章节合同路径，使生成端与验证端读取同一份章节顺序和标题。
PATH_SECTION_CONTRACT = Path(__file__).resolve().parents[3] / "assets" / "section_contract.json"  # 章节合同资产路径

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

    # 返回十六进制摘要，供公式图片、登记表和正文引用共同绑定。
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

# 组合三个已确认事实域，形成 Markdown 与 DOCX 共同消费的中间真相层。
def build_disclosure_model(
    list_sections: Sequence[Mapping[str, Any]],
    list_formulas: Sequence[Mapping[str, Any]],
    dict_evidence_map: Mapping[str, Any],
) -> dict[str, Any]:
    """构建版本二结构化专利交底模型。

    参数：
    - `list_sections`：按合同顺序排列的章节内容。
    - `list_formulas`：已确认的公式语义记录。
    - `dict_evidence_map`：章节、步骤或公式到来源编号的映射。

    返回：
    - `dict[str, Any]`：不共享输入可变对象的版本二模型。

    异常：
    - `TypeError`：任一输入不是 JSON 兼容数据时由复制逻辑上抛。
    """

    # 三个核心对象分别复制，避免后续渲染或验证阶段反向污染事实层。
    dict_model = {
        "contract_version": "2.0",  # 当前结构化合同版本
        "sections": copy_json_value(list_sections),  # 章节事实副本
        "formula_registry": build_formula_registry(list_formulas),  # 公式事实及内容绑定值
        "evidence_map": copy_json_value(dict_evidence_map),  # 证据映射副本
    }  # 版本二结构化交底模型

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
