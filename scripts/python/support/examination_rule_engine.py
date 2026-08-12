"""执行审查合同的 Schema、注册和证据闭包。"""

# 延迟解析类型注解，保持模块可由文件路径隔离加载。
from __future__ import annotations

# 标准库负责 JSON 读取和受管路径解析。
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

# 正式 JSON Schema 验证器避免运行时复制弱化合同。
from jsonschema import Draft202012Validator

# 合同和 Schema 共同构成 Contract 2.0 的机器可读事实源。
PATH_ASSETS = Path(__file__).resolve().parents[3] / "assets"  # 正式资产目录

# 默认合同只从正式资产读取。
PATH_EXAMINATION_CONTRACT = PATH_ASSETS / "examination_quality_contract.json"  # 正式合同路径

# 运行时结构边界直接绑定发布包中的正式 Schema。
PATH_EXAMINATION_SCHEMA = PATH_ASSETS / "schemas" / "examination_quality_contract.schema.json"  # 正式 Schema 路径

# 读取 UTF-8 JSON 对象并拒绝非对象根值。
def load_json_object(path_json: Path) -> dict[str, Any]:
    """读取受管 JSON 对象。

    参数：
    - `path_json`：待读取的 JSON 文件。

    返回：
    - `dict[str, Any]`：解析后的对象根值。

    异常：
    - `FileNotFoundError`：目标文件不存在时抛出。
    - `ValueError`：JSON 根值不是对象时抛出。
    """

    # 缺少正式资产时不得回退到 Python 内置副本。
    if not path_json.exists():

        # 保留真实路径供安装包完整性检查定位。
        raise FileNotFoundError(f"> ERR: [Python] 缺少审查合同资产：{path_json}")

    # UTF-8 是合同中文来源摘要的固定编码。
    obj_document = json.loads(path_json.read_text(encoding="utf-8"))  # 当前 JSON 根值

    # 数组或标量根值不能形成命名字段合同。
    if not isinstance(obj_document, dict):

        # Schema 本身和合同实例都要求对象根值。
        raise ValueError(f"> ERR: [Python] 审查合同资产根值必须为对象：{path_json}")

    # 调用方只接收可按字段验证的对象。
    return obj_document

# 把 Schema 错误压缩为稳定的合同加载异常。
def validate_schema_instance(
    dict_instance: Mapping[str, Any],
    dict_schema: Mapping[str, Any],
    str_subject: str,
) -> None:
    """使用 Draft 2020-12 验证一个合同实例。

    参数：
    - `dict_instance`：待验证实例。
    - `dict_schema`：正式 JSON Schema 或其子 Schema。
    - `str_subject`：错误消息中的对象名称。

    返回：
    - `None`：实例完全通过时结束。

    异常：
    - `ValueError`：存在任一 Schema 错误时抛出。
    """

    # Schema 自身先通过元验证，损坏发布资产不能用于出具结论。
    Draft202012Validator.check_schema(dict(dict_schema))

    # 错误按实例路径排序，保证同一损坏合同产生稳定首错。
    obj_validator = Draft202012Validator(dict(dict_schema))  # 当前 Draft 2020-12 验证器

    # 空路径错误排在字段级错误之前，便于优先报告结构根因。
    list_errors = sorted(  # 按字段路径稳定排序的全部实例错误
        obj_validator.iter_errors(dict(dict_instance)),  # 当前实例的原始验证错误
        key=lambda obj_error: tuple(str(obj_part) for obj_part in obj_error.absolute_path),  # 字段路径排序键
    )

    # 任一错误都表示运行时不能完整解释当前元数据。
    if list_errors:

        # 首错路径和消息足以定位损坏字段，完整列表仍可由测试直接复现。
        obj_first_error = list_errors[0]  # 稳定排序后的首个 Schema 错误

        # 使用点分路径避免在异常文本中输出整份合同。
        str_error_path = ".".join(str(obj_part) for obj_part in obj_first_error.absolute_path) or "<root>"  # 首错字段路径

        # 统一 ValueError 供 CLI 和注册测试 fail closed。
        raise ValueError(f"> ERR: [Python] 审查合同无效：{str_subject} {str_error_path}: {obj_first_error.message}")

# 单条 applicability 与完整合同使用同一个 Schema 定义。
def validate_rule_applicability(dict_applicability: Any) -> None:
    """验证模式专属适用字段组合。

    参数：
    - `dict_applicability`：规则声明的适用条件。

    返回：
    - `None`：条件结构合法时结束。

    异常：
    - `ValueError`：对象类型或字段组合损坏时抛出。
    """

    # 非对象输入无法传给受管子 Schema。
    if not isinstance(dict_applicability, Mapping):

        # 字符串和数组条件禁止隐式解释。
        raise ValueError("> ERR: [Python] 规则 applicability 必须为对象。")

    # 子 Schema 从正式文件提取，避免手工维护第二套模式枚举。
    dict_schema = load_json_object(PATH_EXAMINATION_SCHEMA)  # 单条适用条件使用的正式 Schema

    # `$defs.applicability` 是完整合同的唯一适用条件定义。
    dict_applicability_schema = dict_schema["$defs"]["applicability"]  # 模式专属字段组合子 Schema

    # 子对象使用与完整合同相同的 additionalProperties 和条件分支。
    validate_schema_instance(dict_applicability, dict_applicability_schema, "规则 applicability")

# 验证规则和 handler 身份分别保持唯一。
def validate_rule_identities(list_rules: list[dict[str, Any]]) -> list[str]:
    """验证规则身份并返回 handler 顺序。

    参数：
    - `list_rules`：已通过 Schema 的规则数组。

    返回：
    - `list[str]`：按合同顺序排列的 handler 身份。

    异常：
    - `ValueError`：规则或 handler 身份重复时抛出。
    """

    # Schema 已保证字段存在和字符串类型。
    list_rule_ids = [str(dict_rule["id"]) for dict_rule in list_rules]  # 合同规则身份

    # 报告定位要求规则编号全局唯一。
    if len(list_rule_ids) != len(set(list_rule_ids)):

        # 重复编号会让 finding 无法稳定回溯。
        raise ValueError("> ERR: [Python] Contract 2.0 包含重复规则 ID。")

    # handler 身份决定 JSON 与 Python 的唯一连接。
    list_handler_ids = [str(dict_rule["handler_id"]) for dict_rule in list_rules]  # 合同 handler 身份

    # 一条实现只承担一条 JSON 规则，元数据不会藏回 Python。
    if len(list_handler_ids) != len(set(list_handler_ids)):

        # 共享 handler 会破坏规则级别和适用条件所有权。
        raise ValueError("> ERR: [Python] Contract 2.0 包含重复 handler_id。")

    # 注册闭包按这组声明身份继续核对。
    return list_handler_ids

# 验证 JSON 声明和 Python 实现形成双向闭包。
def validate_handler_closure(
    list_handler_ids: list[str],
    dict_handlers: Mapping[str, Callable[[dict[str, Any]], list[dict[str, Any]]]],
) -> None:
    """验证合同 handler 与实现注册表完全相等。

    参数：
    - `list_handler_ids`：合同声明的唯一 handler 身份。
    - `dict_handlers`：Python 领域检查注册表。

    返回：
    - `None`：双方集合相等时结束。

    异常：
    - `ValueError`：存在缺失或 orphan handler 时抛出。
    """

    # 合同声明集合不接受运行时补全。
    set_declared_handlers = set(list_handler_ids)  # JSON 声明的 handler 集合

    # 声明但未实现的规则会造成静默漏检。
    set_missing_handlers = set_declared_handlers - set(dict_handlers)  # 当前缺失 handler

    # 缺失实现必须在执行任何领域规则前阻断。
    if set_missing_handlers:

        # 稳定排序便于一次修复全部缺口。
        raise ValueError(f"> ERR: [Python] 合同 handler 未注册：{sorted(set_missing_handlers)}")

    # Python 多出的实现表示行为可能绕过 JSON 元数据。
    set_orphan_handlers = set(dict_handlers) - set_declared_handlers  # 合同外 Python 实现集合

    # 未声明实现同样破坏单一事实源。
    if set_orphan_handlers:

        # 稳定排序便于删除合同外实现。
        raise ValueError(f"> ERR: [Python] 存在 orphan 规则 handler：{sorted(set_orphan_handlers)}")

# 完整合同先过 Schema，再过身份和注册闭包。
def validate_rule_registry(
    dict_contract: Mapping[str, Any],
    dict_handlers: Mapping[str, Callable[[dict[str, Any]], list[dict[str, Any]]]],
) -> None:
    """验证 Contract 2.0 与 Python handler 闭包。

    参数：
    - `dict_contract`：待执行的机器可读合同。
    - `dict_handlers`：当前领域检查注册表。

    返回：
    - `None`：结构和注册均闭合时结束。

    异常：
    - `ValueError`：Schema、身份或注册关系损坏时抛出。
    """

    # 合同总门直接读取发布包 Schema，不复制子规则。
    dict_schema = load_json_object(PATH_EXAMINATION_SCHEMA)  # 完整合同实例验证 Schema

    # additionalProperties、完整词表和模式专属字段均由 Schema 执行。
    validate_schema_instance(dict_contract, dict_schema, "统一审查合同")

    # Schema 通过后 rules 必然是对象数组。
    list_rules = [dict(dict_rule) for dict_rule in dict_contract["rules"]]  # 已验证规则数组

    # 身份唯一性是 JSON Schema 之外的跨记录闭包。
    list_handler_ids = validate_rule_identities(list_rules)  # 合同唯一 handler 顺序

    # Python 注册表必须与合同声明双向完全相等。
    validate_handler_closure(list_handler_ids, dict_handlers)

# 读取合同并在返回前完成全部闭包。
def load_examination_contract(
    path_contract: Path | None,
    dict_handlers: Mapping[str, Callable[[dict[str, Any]], list[dict[str, Any]]]],
) -> dict[str, Any]:
    """加载可安全执行的 Contract 2.0。

    参数：
    - `path_contract`：可选合同路径，空值使用正式资产。
    - `dict_handlers`：当前正式 handler 注册表。

    返回：
    - `dict[str, Any]`：已完成 Schema 和注册校验的合同。

    异常：
    - `FileNotFoundError`：合同或 Schema 不存在时抛出。
    - `ValueError`：合同或注册闭包损坏时抛出。
    """

    # 显式路径用于隔离测试，生产默认值始终绑定正式资产。
    path_selected = path_contract if path_contract is not None else PATH_EXAMINATION_CONTRACT  # 本轮合同路径

    # 只从当前目标解析合同，不提供内置回退。
    dict_contract = load_json_object(path_selected)  # 当前合同对象

    # 返回前阻断结构漂移和实现漂移。
    validate_rule_registry(dict_contract, dict_handlers)

    # 调用方只接收可按声明顺序执行的合同。
    return dict_contract

# 根据合同适用条件选择当前规则。
def is_rule_applicable(dict_rule: Mapping[str, Any], dict_context: Mapping[str, Any]) -> bool:
    """判断规则是否适用于当前案件。

    参数：
    - `dict_rule`：已通过合同验证的规则。
    - `dict_context`：案件事实和 AI 状态。

    返回：
    - `bool`：当前规则需要执行时为真。

    异常：
    - 无；合同结构已由注册门验证。
    """

    # 适用模式不读取写作 profile。
    dict_applicability = dict_rule["applicability"]  # 当前规则适用条件

    # 核心审查规则始终执行。
    if dict_applicability["mode"] == "always":

        # AI 状态不能关闭通用实体规则。
        return True

    # 信号控制规则只读取系统可观察分级。
    if dict_applicability["mode"] == "signal":

        # 当前分级必须命中合同声明集合。
        return dict_context["ai_applicability"]["signal_level"] in dict_applicability["signal_levels"]

    # AI 实体规则需要 hard 或有效人工 applicable 决定。
    if not dict_context["ai_applicability"]["ai_rules_apply"]:

        # 未适用时不调用任何 AI 实体 handler。
        return False

    # 未声明范围的 AI 规则对全部合法范围生效。
    if "ai_scopes" not in dict_applicability:

        # 公共范围规则无需二次筛选。
        return True

    # 范围化规则只消费案件显式 ai_scope。
    return dict_context["case_config"].get("ai_scope") in dict_applicability["ai_scopes"]

# 把 JSON 元数据与领域 finding 合并。
def build_engine_finding(
    dict_rule: Mapping[str, Any],
    dict_handler_finding: Mapping[str, Any],
) -> dict[str, Any]:
    """构造统一审查 finding。

    参数：
    - `dict_rule`：当前 Contract 2.0 规则。
    - `dict_handler_finding`：handler 返回的领域问题。

    返回：
    - `dict[str, Any]`：报告可直接消费的 finding。

    异常：
    - `KeyError`：handler 缺少领域必填字段时抛出。
    """

    # 级别、规则身份和证据要求始终由 JSON 拥有。
    return {
        "level": str(dict_rule["default_level"]),
        "code": str(dict_handler_finding["code"]),
        "message": str(dict_handler_finding["message"]),
        "action": str(dict_handler_finding["action"]),
        "rule_id": str(dict_rule["id"]),
        "topic": str(dict_rule["topic"]),
        "rule_sets": list(dict_rule["rule_sets"]),
        "evidence_required": bool(dict_rule["evidence_required"]),
        "evidence_bindings": list(dict_handler_finding.get("evidence_bindings", [])),
    }

# 证据坐标必须可逐项定位。
def has_verifiable_evidence_bindings(dict_handler_finding: Mapping[str, Any]) -> bool:
    """检查 finding 是否提供非空字符串证据坐标。

    参数：
    - `dict_handler_finding`：待检查的领域 finding。

    返回：
    - `bool`：至少包含一个可定位坐标时为真。

    异常：
    - 无。
    """

    # 字符串本身不能冒充证据数组。
    obj_bindings = dict_handler_finding.get("evidence_bindings")  # 当前证据绑定原始值

    # 每项坐标都必须具有可见内容。
    return bool(
        isinstance(obj_bindings, list)
        and obj_bindings
        and all(isinstance(obj_item, str) and bool(obj_item.strip()) for obj_item in obj_bindings)
    )

# 缺少强制证据时生成稳定 blocker。
def build_evidence_missing_finding(dict_rule: Mapping[str, Any]) -> dict[str, Any]:
    """构造规则证据合同错误。

    参数：
    - `dict_rule`：要求证据的当前规则。

    返回：
    - `dict[str, Any]`：可进入正式报告的 blocker。

    异常：
    - 无；规则已经通过 Schema 验证。
    """

    # 证据合同错误保留原规则身份和分组。
    return {
        "level": "blocker",
        "code": "rule_evidence_missing",
        "message": f"规则 finding 缺少可核验证据绑定：{dict_rule['id']}",
        "action": "由领域 handler 返回非空 evidence_bindings 后重新评估。",
        "rule_id": str(dict_rule["id"]),
        "topic": str(dict_rule["topic"]),
        "rule_sets": list(dict_rule["rule_sets"]),
        "evidence_required": True,
        "evidence_bindings": [],
    }

# 单条 handler 输出由统一证据策略转换。
def normalize_handler_finding(
    dict_rule: Mapping[str, Any],
    dict_handler_finding: Mapping[str, Any],
) -> dict[str, Any]:
    """按 evidence_required 规范化领域 finding。

    参数：
    - `dict_rule`：当前规则。
    - `dict_handler_finding`：当前领域 finding。

    返回：
    - `dict[str, Any]`：证据合同错误或正常统一 finding。

    异常：
    - `KeyError`：正常 finding 缺少领域必填字段时抛出。
    """

    # required 规则只有可核验证据存在时才保留原问题。
    if dict_rule["evidence_required"] and not has_verifiable_evidence_bindings(dict_handler_finding):

        # 缺证据时不伪装原问题已经得到支撑。
        return build_evidence_missing_finding(dict_rule)

    # 非 required 或证据齐全时合并正式元数据。
    return build_engine_finding(dict_rule, dict_handler_finding)

# 合同数组是唯一执行清单。
def run_rule_engine(
    dict_contract: Mapping[str, Any],
    dict_context: dict[str, Any],
    dict_handlers: Mapping[str, Callable[[dict[str, Any]], list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    """执行数据驱动审查规则。

    参数：
    - `dict_contract`：待执行的 Contract 2.0。
    - `dict_context`：本次案件事实和 AI 状态。
    - `dict_handlers`：调用方明确提供的 handler 注册表。

    返回：
    - `list[dict[str, Any]]`：按合同顺序生成的 findings。

    异常：
    - `ValueError`：合同或注册闭包损坏时抛出。
    """

    # 显式空表仍应报告全部缺失实现。
    validate_rule_registry(dict_contract, dict_handlers)

    # 先保留适用规则，避免执行阶段再次解释 profile。
    list_applicable_rules = [  # 保持合同顺序的适用规则
        dict_rule  # 保留原始规则元数据
        for dict_rule in dict_contract["rules"]  # 遍历正式合同规则
        if is_rule_applicable(dict_rule, dict_context)  # 过滤当前案件不适用规则
    ]

    # 合同顺序和 handler 输出顺序共同决定稳定报告顺序。
    return [
        normalize_handler_finding(dict_rule, dict_handler_finding)
        for dict_rule in list_applicable_rules
        for dict_handler_finding in dict_handlers[str(dict_rule["handler_id"])](dict_context)
    ]
