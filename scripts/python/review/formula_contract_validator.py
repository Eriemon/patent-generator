"""校验专利交底书公式登记表的语义完整性与符号闭包。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 抽象容器类型用于约束输入边界，不引入第三方依赖。
from collections.abc import Mapping, Sequence
from typing import Any

# 固定单个符号必须具备的解释维度，禁止只有变量名的空壳登记。
TUPLE_REQUIRED_SYMBOL_KEYS = ("name", "meaning", "unit", "domain")  # 符号语义必填键

# 判断单个符号是否同时具备名称、含义、单位和定义域。
def is_symbol_incomplete(obj_symbol: Any) -> bool:
    """判断一个公式符号是否缺少必要语义。

    参数：
    - `obj_symbol`：待检查的符号记录。

    返回：
    - `bool`：不是映射或存在空字段时为 `True`。

    异常：
    - 无。
    """

    # 非对象符号没有可定位的语义字段，直接判定为不完整。
    if not isinstance(obj_symbol, Mapping):

        # 返回不完整状态，避免调用方继续访问错误类型。
        return True

    # 任一必填维度为空都意味着代理人无法理解该变量。
    return any(not str(obj_symbol.get(str_key, "")).strip() for str_key in TUPLE_REQUIRED_SYMBOL_KEYS)

# 判断符号列表容器和其中每条定义是否满足完整性要求。
def is_symbol_list_incomplete(obj_symbols: Any) -> bool:
    """判断公式符号列表是否为空、类型错误或含不完整记录。

    参数：
    - `obj_symbols`：公式记录中的原始符号值。

    返回：
    - `bool`：符号列表不可用于正式交付时为 `True`。

    异常：
    - 无。
    """

    # 非列表或空列表都不能建立公式变量的完整解释集合。
    if not isinstance(obj_symbols, list) or not obj_symbols:

        # 返回不完整状态，避免调用方迭代错误容器。
        return True

    # 任一符号不完整都会破坏整条公式的符号闭包。
    return any(is_symbol_incomplete(obj_symbol) for obj_symbol in obj_symbols)

# 提取字段结构正确的符号名称，供正文使用集合执行差集检查。
def extract_defined_symbols(obj_symbols: Any) -> set[str]:
    """提取公式记录中已登记的符号名称。

    参数：
    - `obj_symbols`：公式记录中的原始符号值。

    返回：
    - `set[str]`：可安全读取的符号名称集合。

    异常：
    - 无。
    """

    # 错误容器不含可信符号定义，交由完整性规则另行报告。
    if not isinstance(obj_symbols, list):

        # 返回空集合，使正文中任何实际符号都能被闭包检查发现。
        return set()

    # 仅从映射记录读取名称，跳过已由 FOR005 报告的损坏条目。
    return {str(obj_symbol.get("name", "")) for obj_symbol in obj_symbols if isinstance(obj_symbol, Mapping)}

# 检查单条公式的用途、证据、引用和逐符号解释是否齐全。
def validate_formula_record(dict_formula: Mapping[str, Any]) -> list[dict[str, str]]:
    """校验单条公式记录的可审查语义。

    参数：
    - `dict_formula`：待校验公式记录。

    返回：
    - `list[dict[str, str]]`：当前公式产生的稳定发现。

    异常：
    - 无。
    """

    # 公式标识进入每条消息，便于代理人定位具体记录。
    str_formula_id = str(dict_formula.get("formula_id", ""))  # 当前公式标识

    # 发现按合同维度排列，保证多次运行输出顺序稳定。
    list_findings: list[dict[str, str]] = []  # 当前公式发现

    # 标识或表达式缺失意味着记录不能代表一条可追踪公式。
    if not str_formula_id or not str(dict_formula.get("latex", "")).strip():

        # 使用基础结构代码报告无法继续解释的公式记录。
        list_findings.append({"code": "FOR001", "message": f"公式基础字段缺失:{str_formula_id}"})

    # 用途必须说明公式在技术方案中计算或判定什么。
    if not str(dict_formula.get("purpose", "")).strip():

        # 不推断公式用途，要求上游从材料或发明人说明中补齐。
        list_findings.append({"code": "FOR002", "message": f"公式缺少用途:{str_formula_id}"})

    # 至少一个来源编号用于建立公式与本地材料之间的可追踪关系。
    if not dict_formula.get("sources"):

        # 无来源公式不得进入正式交底书，即使表达式语法正确。
        list_findings.append({"code": "FOR003", "message": f"公式缺少来源:{str_formula_id}"})

    # 至少一个章节或步骤引用用于证明公式确实服务于正文方案。
    if not dict_formula.get("references"):

        # 孤立公式不能仅作为装饰内容保留在登记表中。
        list_findings.append({"code": "FOR004", "message": f"公式缺少正文引用:{str_formula_id}"})

    # 原始符号对象必须保留类型信息，避免错误值被静默转换。
    obj_symbols = dict_formula.get("symbols")  # 当前公式符号登记值

    # 委托单一辅助函数联合检查容器和逐符号字段完整性。
    bool_symbols_incomplete = is_symbol_list_incomplete(obj_symbols)  # 符号语义状态

    # 符号解释不完整时不能依靠公式表面文本猜测含义、单位或定义域。
    if bool_symbols_incomplete:

        # 使用独立代码区分符号问题与公式来源、用途问题。
        list_findings.append({"code": "FOR005", "message": f"公式符号定义不完整:{str_formula_id}"})

    # 返回当前记录的全部问题，供登记表级校验继续汇总。
    return list_findings

# 汇总公式级发现，并检查重复标识和正文实际符号是否闭合。
def validate_formula_registry(
    list_registry: Sequence[Any],
    dict_used_symbols: Mapping[str, Sequence[str]] | None = None,
) -> list[dict[str, str]]:
    """校验公式登记表及正文符号引用闭包。

    参数：
    - `list_registry`：公式记录序列。
    - `dict_used_symbols`：按公式标识归集的正文实际符号，可省略。

    返回：
    - `list[dict[str, str]]`：按公式顺序生成的稳定发现。

    异常：
    - 无。
    """

    # 缺省符号引用映射表示上层暂不提供正文符号扫描结果。
    dict_symbol_usage = dict_used_symbols or {}  # 正文符号引用映射

    # 登记已见标识用于识别追踪键冲突，不能用后记录覆盖前记录。
    set_seen_ids: set[str] = set()  # 已见公式标识

    # 汇总所有公式问题，保持输入顺序以提高报告可读性。
    list_findings: list[dict[str, str]] = []  # 公式登记表发现

    # 每条公式独立验证，使一个损坏记录不会阻断其余问题收集。
    for obj_formula in list_registry:

        # 非对象记录没有可解释字段，直接登记基础结构问题。
        if not isinstance(obj_formula, Mapping):

            # 报告非对象条目并跳过无法安全执行的字段访问。
            list_findings.append({"code": "FOR001", "message": "公式记录必须为对象"})

            # 继续检查后续记录，向用户一次提供完整修复清单。
            continue

        # 获取稳定公式标识，供登记表级重复检查和正文映射使用。
        str_formula_id = str(obj_formula.get("formula_id", ""))  # 登记表当前公式标识

        # 追加当前公式的字段级语义发现。
        list_findings.extend(validate_formula_record(obj_formula))

        # 重复标识会破坏证据、图片和正文引用的一一对应关系。
        if str_formula_id and str_formula_id in set_seen_ids:

            # 使用独立错误码标记追踪键冲突。
            list_findings.append({"code": "FOR007", "message": f"公式标识重复:{str_formula_id}"})

        # 无论是否重复都登记标识，使第三次出现仍能被识别。
        set_seen_ids.add(str_formula_id)

        # 从公式记录提取已定义名称，损坏对象由 FOR005 负责报告。
        set_defined_symbols = extract_defined_symbols(obj_formula.get("symbols"))  # 已定义符号集合

        # 正文实际使用但未登记的符号必须逐公式形成闭包问题。
        list_unknown_symbols = sorted(set(dict_symbol_usage.get(str_formula_id, [])) - set_defined_symbols)  # 未定义正文符号

        # 未知符号存在时阻断正式交付，禁止根据字符名称自动补义。
        if list_unknown_symbols:

            # 排序后的符号列表保证发现消息跨运行稳定。
            str_unknown = ",".join(list_unknown_symbols)  # 稳定排序后的未知符号文本

            # 将公式标识与未知符号共同写入发现，便于代理人定位。
            list_findings.append({"code": "FOR006", "message": f"公式使用未定义符号:{str_formula_id}:{str_unknown}"})

    # 返回完整公式发现；空列表表示当前语义和符号闭包均通过。
    return list_findings
