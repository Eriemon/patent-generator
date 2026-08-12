"""提供统一审查引擎复用的创造性链和结构字段检查。"""

# 延迟解析类型注解，保持按路径加载时的运行时兼容性。
from __future__ import annotations

# 标准类型用于表达受管审查记录。
from typing import Any

# 判断最接近现有技术记录是否形成完整创造性推理链。
def has_complete_inventiveness_chain(dict_record: dict[str, Any]) -> bool:
    """检查单条先前技术记录的创造性推理字段。

    参数：
    - `dict_record`：已核验的最接近现有技术记录。

    返回：
    - `bool`：区别特征、效果、实际问题和技术启示均存在时为真。

    异常：
    - 无；缺失字段按不完整处理。
    """

    # 规范化区别特征文本，空白条目不能计入完整推理链。
    list_different_features = [  # 有效区别特征列表
        str(obj_feature).strip()  # 可用于效果映射的特征文本
        for obj_feature in dict_record.get("different_features", [])  # 原始区别特征条目
        if str(obj_feature).strip()  # 过滤空白区别特征
    ]

    # 逐特征效果必须使用对象映射，禁止单一效果文本掩盖局部缺口。
    obj_difference_effects = dict_record.get("difference_effects")  # 原始区别效果映射

    # 每项区别特征都要有非空效果说明。
    bool_has_difference_effects = isinstance(obj_difference_effects, dict) and all(  # 区别效果是否逐项闭合
        bool(str(obj_difference_effects.get(str_feature, "")).strip())  # 当前特征的效果说明
        for str_feature in list_different_features  # 遍历全部有效区别特征
    )

    # 技术启示必须结构化记录结论和依据。
    obj_technical_motivation = dict_record.get("technical_motivation")  # 原始技术启示对象

    # 非对象载荷不能提供可信结论或证据。
    dict_technical_motivation = (  # 可检查技术启示对象
        obj_technical_motivation  # 保留结构化技术启示字段
        if isinstance(obj_technical_motivation, dict)  # 只接受对象合同
        else {}  # 旧载荷按不完整处理
    )

    # 读取证据载荷，兼容单条文本和证据列表。
    obj_motivation_evidence = dict_technical_motivation.get("evidence")  # 技术启示证据

    # 列表或文本证据至少包含一项可见内容。
    bool_has_motivation_evidence = (  # 技术启示是否包含可回查证据
        any(bool(str(obj_item).strip()) for obj_item in obj_motivation_evidence)  # 列表中存在有效证据
        if isinstance(obj_motivation_evidence, list)  # 列表证据分支
        else bool(str(obj_motivation_evidence or "").strip())  # 单条证据文本分支
    )

    # 四段推理链全部存在时才具备创造性人工审阅条件。
    return (
        bool(list_different_features)
        and bool_has_difference_effects
        and bool(str(dict_record.get("actual_technical_problem", "")).strip())
        and bool(str(dict_technical_motivation.get("conclusion", "")).strip())
        and bool_has_motivation_evidence
    )

# 检查查新记录是否足以支持创造性审阅。
def append_inventiveness_findings(
    list_prior_art_records: list[dict[str, Any]],
    list_findings: list[dict[str, str]],
) -> None:
    """把创造性推理缺项追加到统一finding列表。

    参数：
    - `list_prior_art_records`：已核验的先前技术记录。
    - `list_findings`：待扩展的统一审查问题列表。

    返回：
    - `None`：函数原地扩展问题列表。

    异常：
    - 无；空记录由既有先前技术硬门处理。
    """

    # 空记录由现有技术来源门报告，避免同一根因重复finding。
    if not list_prior_art_records:

        # 本检查没有可评估记录时直接结束。
        return

    # 任一记录形成完整链即可进入人工创造性审阅。
    if any(has_complete_inventiveness_chain(dict_record) for dict_record in list_prior_art_records):

        # 已有完整推理链时无需追加补正项。
        return

    # 所有记录都不完整时登记稳定major领域事实。
    list_findings.append(
        {
            "level": "major",  # 既有兼容接口的严重级别
            "code": "inventiveness_chain_incomplete",  # 创造性链缺口编号
            "message": "现有技术记录尚未形成区别特征、技术效果、实际技术问题和技术启示的完整推理链。",  # 问题说明
            "action": "补齐区别特征对应效果、重新确定的实际技术问题，以及技术启示及其证据。",  # 补正动作
        }
    )

# 判断结构化披露对象是否包含指定非空字段。
def has_required_fields(dict_section: dict[str, Any], tuple_fields: tuple[str, ...]) -> bool:
    """检查专项披露对象的必要字段。

    参数：
    - `dict_section`：待检查的结构化披露对象。
    - `tuple_fields`：当前规则要求的字段名集合。

    返回：
    - `bool`：全部字段均为非空值时为真。

    异常：
    - 无；缺失或空值按不完整处理。
    """

    # 字符串要求可见内容，其他容器沿用非空语义。
    return all(
        bool(obj_value.strip()) if isinstance(obj_value, str) else bool(obj_value)
        for obj_value in (dict_section.get(str_field) for str_field in tuple_fields)
    )
