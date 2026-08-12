"""提供结构化专利交底书的基础合同校验与稳定哈希。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 标准库负责规范化 JSON 序列化和内容摘要计算。
import hashlib
import json
from collections.abc import Mapping
from typing import Any

# 固定正式交付模型必须具备的顶层对象，防止正文绕过结构化合同。
TUPLE_REQUIRED_MODEL_KEYS = ("sections", "formula_registry", "evidence_map")  # 模型必填顶层键

# 章节条目必须同时描述写作目标、正向要求和禁止边界。
TUPLE_REQUIRED_SECTION_KEYS = ("id", "title", "purpose", "required_content", "forbidden_content", "evidence_required")  # 章节合同必填键

# 将 JSON 语义规范化为可重复摘要，供证据和公式记录追踪。
def calculate_json_hash(obj_payload: Any) -> str:
    """计算不受映射键顺序影响的 JSON SHA-256。

    参数：
    - `obj_payload`：可由标准 JSON 编码器序列化的对象。

    返回：
    - `str`：小写十六进制 SHA-256 摘要。

    异常：
    - `TypeError`：输入包含不可序列化对象时由 JSON 编码器上抛。
    """

    # 紧凑且排序后的 UTF-8 表示是跨运行可重复摘要的输入边界。
    bytes_canonical = json.dumps(obj_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")  # 规范化 JSON 字节

    # 摘要只证明记录内容一致，不替代材料真实性审查。
    return hashlib.sha256(bytes_canonical).hexdigest()

# 检查章节合同是否完整表达版本、章节数量和逐章写作边界。
def validate_section_contract(dict_contract: Mapping[str, Any]) -> list[dict[str, str]]:
    """检查章节合同自身是否满足版本二的最小结构要求。

    参数：
    - `dict_contract`：从正式章节合同资产读取的映射。

    返回：
    - `list[dict[str, str]]`：按输入顺序生成的稳定校验发现。

    异常：
    - 无。
    """

    # 所有发现使用稳定代码，便于 CLI 和验证报告共同消费。
    list_findings: list[dict[str, str]] = []  # 合同自检发现

    # 非版本二合同不能支撑本轮结构化正式交付。
    if dict_contract.get("contract_version") != "2.0":

        # 记录版本偏差，但继续收集其余结构问题。
        list_findings.append({"code": "SEC001", "message": "章节合同版本必须为2.0"})

    # 原始章节值需先保留类型信息，避免把错误对象静默转换成列表。
    obj_sections = dict_contract.get("sections")  # 原始章节合同值

    # 非数组章节无法继续逐项验证，返回已收集问题和类型问题。
    if not isinstance(obj_sections, list):

        # 返回类型发现并终止无法可靠执行的逐项检查。
        return list_findings + [{"code": "SEC001", "message": "sections必须为数组"}]

    # 逐项收集非对象、缺字段和无效标识问题，同时保持输入顺序。
    for int_index, obj_section in enumerate(obj_sections):

        # 非映射章节无法读取合同字段，只记录定位明确的问题。
        if not isinstance(obj_section, Mapping):

            # 使用数组下标定位损坏条目，便于维护者直接修复资产。
            list_findings.append({"code": "SEC001", "message": f"章节{int_index}必须为对象"})

            # 跳过当前损坏条目，避免后续字段访问制造次生异常。
            continue

        # 缺失字段集中报告，减少同一章节产生的重复发现。
        list_missing = [str_key for str_key in TUPLE_REQUIRED_SECTION_KEYS if str_key not in obj_section]  # 当前章节缺失字段

        # 任一合同维度缺失都会削弱章节约束，必须作为阻断发现记录。
        if list_missing:

            # 拼接稳定字段名，便于报告和测试直接比较。
            list_findings.append({"code": "SEC001", "message": f"章节{int_index}缺少字段:{','.join(list_missing)}"})

    # 正式模板固定为十一项叶子章节，数量漂移说明合同与模板失配。
    if len(obj_sections) != 11:

        # 单独报告数量问题，避免它被某个具体章节字段问题掩盖。
        list_findings.append({"code": "SEC001", "message": "章节合同必须包含11项叶子章节"})

    # 返回完整发现集合；空列表表示合同结构通过当前版本检查。
    return list_findings

# 检查正式交底模型是否包含章节、公式和证据三类核心对象。
def validate_disclosure_model_shape(dict_model: Mapping[str, Any]) -> list[dict[str, str]]:
    """检查正式结构化交底模型的顶层形状。

    参数：
    - `dict_model`：待进入起草或验证阶段的结构化模型。

    返回：
    - `list[dict[str, str]]`：缺失核心对象或版本错误的发现。

    异常：
    - 无。
    """

    # 先确定缺失对象，使每个发现都能直接指出待补齐的模型部分。
    list_missing = [str_key for str_key in TUPLE_REQUIRED_MODEL_KEYS if str_key not in dict_model]  # 缺失核心对象

    # 缺失对象逐项形成稳定发现，避免一个笼统错误掩盖修复范围。
    list_findings = [{"code": "SEC001", "message": f"结构化交底模型缺少顶层对象:{str_key}"} for str_key in list_missing]  # 模型形状发现

    # 版本错误会使字段语义不确定，即使顶层对象齐全也必须阻断。
    if dict_model.get("contract_version") != "2.0":

        # 将版本偏差加入同一发现集合，供上层一次性展示。
        list_findings.append({"code": "SEC001", "message": "结构化交底模型版本必须为2.0"})

    # 返回形状发现；更深层章节和公式语义由专用验证器负责。
    return list_findings
