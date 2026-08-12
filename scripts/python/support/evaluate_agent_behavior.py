#!/usr/bin/env python3
"""根据独立行为清单评估 Agent 响应是否遵守专利技能合同。"""

# 启用未来版本注解行为，保持类型标注在受支持解释器间一致。
from __future__ import annotations

# 引入参数解析、JSON 读写和路径处理能力，保持评测工具仅依赖标准库。
import argparse
import json
from pathlib import Path
from typing import Any

# 构造行为评测命令行参数，明确清单、响应和报告的三个输入输出边界。
def parse_arguments() -> argparse.Namespace:
    """解析 Agent 行为评测命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含行为清单、响应文件、报告文件和变体选择。

    异常：
    - 参数非法时由 `argparse` 自动结束进程。
    """

    # 初始化行为评测入口的参数解析器。
    argument_parser_obj_parser = argparse.ArgumentParser(  # 行为评测参数解析器
        description="Evaluate independent patent skill Agent behavior."  # CLI 用途说明
    )

    # 要求调用方显式提供行为清单，避免误用旧的产品结构评测清单。
    argument_parser_obj_parser.add_argument("--manifest", required=True)

    # 要求调用方提供真实 Agent 响应文件，缺失响应不得被当成通过。
    argument_parser_obj_parser.add_argument("--responses", required=True)

    # 把机器可读结果写入文件，避免在终端泄露完整响应内容。
    argument_parser_obj_parser.add_argument("--output", required=True)

    # 允许只评估带技能响应，也允许同时核对可选 baseline 响应。
    argument_parser_obj_parser.add_argument(
        "--variant",
        choices=("with_skill", "without_skill", "both"),
        default="with_skill",
    )

    # 返回解析后的参数对象，供主流程建立本轮评测边界。
    return argument_parser_obj_parser.parse_args()

# 读取一个 JSON 文档并确保顶层对象可供后续字段校验。
def load_json_document(path_document: Path) -> dict[str, Any]:
    """读取 JSON 文档并返回对象。

    参数：
    - `path_document`：待读取的 JSON 文件路径。

    返回：
    - `dict[str, Any]`：解析后的 JSON 对象。

    异常：
    - 文档不是对象时抛出带 Python 错误前缀的 `ValueError`。
    """

    # 读取 UTF-8 文本，确保中文行为清单和响应保持原样。
    str_document_text = path_document.read_text(encoding="utf-8")  # 当前 JSON 文档文本

    # 解析机器清单或响应集合，语法错误由调用方统一转换。
    obj_document = json.loads(str_document_text)  # 当前 JSON 文档对象

    # 顶层数组或字符串不能表达本工具需要的命名字段。
    if not isinstance(obj_document, dict):

        # 抛出不含本机路径的稳定配置错误。
        raise ValueError(
            "> ERR: [Python] AGENT_EVAL001 JSON 顶层必须是对象"
        )

    # 返回已确认结构的 JSON 对象。
    return obj_document

# 校验独立行为清单的结构，防止缺失合同字段被静默跳过。
def validate_manifest(dict_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """校验行为清单并返回用例列表。

    参数：
    - `dict_manifest`：独立行为清单对象。

    返回：
    - `list[dict[str, Any]]`：已经通过字段、类型和唯一 ID 校验的用例列表。

    异常：
    - 清单字段缺失或类型错误时抛出 `ValueError`。
    """

    # 声明清单顶层必须提供的合同字段。
    set_required_manifest_keys = {"version", "title", "cases"}  # 清单必需字段集合

    # 计算顶层缺失字段，保持错误信息不包含清单文件绝对路径。
    list_missing_manifest_keys = sorted(  # 清单顶层缺失字段
        set_required_manifest_keys - set(dict_manifest)  # 顶层字段差集
    )

    # 缺失顶层字段意味着该文件不能作为独立行为评测清单。
    if list_missing_manifest_keys:

        # 抛出带字段列表的稳定配置错误。
        raise ValueError(
            "> ERR: [Python] AGENT_EVAL002 清单缺少字段："
            + ",".join(list_missing_manifest_keys)
        )

    # 提取用例列表并校验其容器类型。
    list_cases = dict_manifest["cases"]  # 当前行为评测用例列表

    # 非列表值不能表达有序的独立行为场景集合。
    if not isinstance(list_cases, list):

        # 抛出稳定类型错误，阻止调用方继续评测。
        raise ValueError(
            "> ERR: [Python] AGENT_EVAL003 清单 cases 必须是数组"
        )

    # 声明每个行为用例都必须具备的解释和期望字段。
    set_required_case_keys = {
        "id",  # 用例标识字段
        "prompt",  # 行为提示字段
        "expected_behavior",  # 预期 Agent 行为字段
        "pass_criteria",  # 通过条件字段
        "without_skill_risk",  # 无技能风险字段
        "with_skill_expected_pass",  # 带技能期望状态字段
        "without_skill_expected_pass",  # baseline 期望状态字段
    }  # 行为用例必需字段集合

    # 记录已见用例 ID，阻止报告键覆盖造成假通过。
    set_case_ids: set[str] = set()  # 已登记的行为用例 ID 集合

    # 逐个校验行为用例的类型、约束和唯一标识。
    for dict_case in list_cases:

        # 用例对象必须是字典，才能表达独立行为合同。
        if not isinstance(dict_case, dict):

            # 抛出稳定结构错误，避免对非对象做隐式字段访问。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL004 行为用例必须是对象"
            )

        # 计算当前用例缺失的合同字段。
        list_missing_case_keys = sorted(  # 当前用例缺失字段
            set_required_case_keys - set(dict_case)  # 当前用例字段差集
        )

        # 缺字段用例不能参与行为判定。
        if list_missing_case_keys:

            # 把用例 ID 作为可定位标签，不回显响应内容。
            str_case_label = str(dict_case.get("id", "<missing-id>"))  # 错误报告用例标签

            # 抛出缺字段错误并保留稳定用例标签。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL005 用例 "
                + str_case_label
                + " 缺少字段："
                + ",".join(list_missing_case_keys)
            )

        # 读取并规范当前用例 ID，供响应索引和报告关联。
        str_case_id = str(dict_case["id"])  # 当前行为用例 ID

        # 空 ID 或重复 ID 会破坏响应绑定关系。
        if not str_case_id or str_case_id in set_case_ids:

            # 抛出稳定 ID 冲突错误。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL006 行为用例 ID 为空或重复："
                + str_case_id
            )

        # 记录当前合法用例 ID。
        set_case_ids.add(str_case_id)

        # 约束组和禁止项必须是字符串数组，便于确定性匹配。
        for str_constraint_key in (
            "required_terms",
            "forbidden_terms",
            "ordered_terms",
        ):

            # 缺失的可选约束按空列表处理，降低清单编写噪声。
            list_constraint = dict_case.get(str_constraint_key, [])  # 当前字符串约束列表

            # 非字符串数组无法形成稳定的文本合同。
            if not isinstance(list_constraint, list) or not all(
                isinstance(str_item, str) for str_item in list_constraint
            ):

                # 抛出包含用例和字段的稳定配置错误。
                raise ValueError(
                    "> ERR: [Python] AGENT_EVAL007 用例 "
                    + str_case_id
                    + " 的 "
                    + str_constraint_key
                    + " 必须是字符串数组"
                )

        # 约束组数组中的每个候选组也必须是非空字符串数组。
        list_required_groups = dict_case.get("required_any_groups", [])  # 当前候选术语组

        # 检查约束组容器和组内候选项的类型。
        if not isinstance(list_required_groups, list) or not all(
            isinstance(list_group, list)
            and list_group
            and all(isinstance(str_item, str) for str_item in list_group)
            for list_group in list_required_groups
        ):

            # 抛出包含用例的稳定配置错误。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL008 用例 "
                + str_case_id
                + " 的 required_any_groups 无效"
            )

    # 返回已通过结构检查的原始用例列表，保留声明顺序。
    return list_cases

# 将响应文件整理为唯一键索引，拒绝未知、重复或空响应。
def build_response_index(
    dict_responses: dict[str, Any], set_case_ids: set[str]
) -> dict[tuple[str, str], str]:
    """构造 `(case_id, variant)` 到响应文本的索引。

    参数：
    - `dict_responses`：响应 JSON 对象。
    - `set_case_ids`：清单已经确认的用例 ID 集合。

    返回：
    - `dict[tuple[str, str], str]`：可供逐例评测的响应索引。

    异常：
    - 响应结构、变体、用例 ID 或重复记录异常时抛出 `ValueError`。
    """

    # 读取响应行列表，要求显式使用 responses 数组。
    list_response_rows = dict_responses.get("responses")  # Agent 响应记录列表

    # 缺失响应数组意味着本轮没有可审计的 Agent 行为证据。
    if not isinstance(list_response_rows, list):

        # 抛出稳定配置错误，阻止空输入被计为通过。
        raise ValueError(
            "> ERR: [Python] AGENT_EVAL009 响应 JSON 必须包含 responses 数组"
        )

    # 准备响应索引，键包含用例和行为变体避免相互覆盖。
    dict_response_index: dict[tuple[str, str], str] = {}  # Agent 响应索引

    # 逐行校验并登记真实 Agent 响应。
    for dict_response in list_response_rows:

        # 每行必须是带命名字段的对象。
        if not isinstance(dict_response, dict):

            # 抛出稳定结构错误，避免隐式接受无名文本。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL010 响应记录必须是对象"
            )

        # 读取响应所属用例，保证逐例报告可以回指清单。
        str_case_id = str(dict_response.get("case_id", ""))  # 响应用例 ID

        # 读取响应行为变体，区分带技能证据与可选 baseline。
        str_variant = str(dict_response.get("variant", ""))  # 响应行为变体

        # 读取 Agent 原始响应文本，后续只保留判定摘要。
        str_response_text = dict_response.get("text")  # Agent 原始响应文本

        # 只允许清单中的用例和两种已声明变体。
        if str_case_id not in set_case_ids or str_variant not in {
            "with_skill",
            "without_skill",
        }:

            # 抛出不含响应正文的稳定绑定错误。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL011 响应引用未知用例或变体："
                + str_case_id
                + "/"
                + str_variant
            )

        # 响应文本必须是字符串，空文本也应按失败语义评估。
        if not isinstance(str_response_text, str):

            # 抛出稳定类型错误，避免把空值当作空响应通过。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL012 响应 text 必须是字符串："
                + str_case_id
            )

        # 组合唯一索引键，拒绝同一变体的重复响应。
        tuple_response_key = (str_case_id, str_variant)  # 响应唯一索引键

        # 重复记录会使评测结果依赖输入顺序，必须 fail-closed。
        if tuple_response_key in dict_response_index:

            # 抛出稳定重复记录错误。
            raise ValueError(
                "> ERR: [Python] AGENT_EVAL013 响应记录重复："
                + str_case_id
                + "/"
                + str_variant
            )

        # 保存原始响应文本，后续只输出机器判定摘要而不回显正文。
        dict_response_index[tuple_response_key] = str_response_text  # 当前响应索引内容

    # 返回完整响应索引，缺失的 with_skill 响应在逐例阶段单独阻断。
    return dict_response_index

# 收集响应中未出现的必需术语，比较过程不区分英文字母大小写。
def collect_missing_terms(
    str_response_text: str, list_required_terms: list[str]
) -> list[str]:
    """查找缺失的必需术语。

    参数：
    - `str_response_text`：待评估的 Agent 响应文本。
    - `list_required_terms`：必须出现的术语列表。

    返回：
    - `list[str]`：未命中的术语列表。

    异常：
    - 无。
    """

    # 统一大小写，保留中文和标点的原始匹配语义。
    str_search_text = str_response_text.casefold()  # 必需术语比较文本

    # 准备缺失术语列表，保持清单声明顺序。
    list_missing_terms: list[str] = []  # 当前响应缺失的必需术语

    # 逐项检查每个必需术语是否在响应中出现。
    for str_required_term in list_required_terms:

        # 未命中的术语进入报告，帮助定位行为缺口。
        if str_required_term.casefold() not in str_search_text:

            # 只记录清单术语，不记录响应正文。
            list_missing_terms.append(str_required_term)

    # 返回全部缺失术语。
    return list_missing_terms

# 检查每个候选组是否至少出现一个等价语义表达。
def collect_missing_groups(
    str_response_text: str, list_required_groups: list[list[str]]
) -> list[list[str]]:
    """查找未满足的候选术语组。

    参数：
    - `str_response_text`：待评估的 Agent 响应文本。
    - `list_required_groups`：每组至少命中一个的候选术语数组。

    返回：
    - `list[list[str]]`：未命中的候选组列表。

    异常：
    - 无。
    """

    # 将候选表达归一化，保证中英文替代项使用同一匹配规则。
    str_search_text = str_response_text.casefold()  # 候选组比较文本

    # 准备未满足的候选组清单。
    list_missing_groups: list[list[str]] = []  # 当前响应未满足的候选组

    # 逐组检查至少一个候选表达是否命中。
    for list_group in list_required_groups:

        # 计算当前组是否有任一候选术语出现在响应中。
        bool_group_matched = any(  # 当前候选组命中状态
            str_term.casefold() in str_search_text for str_term in list_group  # 候选词比较表达式
        )  # 以上候选词的命中布尔值

        # 整组未命中时保留候选项，便于报告具体合同缺口。
        if not bool_group_matched:

            # 复制候选组，避免报告对象与输入清单共享可变列表。
            list_missing_groups.append(list(list_group))

    # 返回全部未满足候选组。
    return list_missing_groups

# 收集响应中出现的禁止语义，防止正确术语被错误承诺抵消。
def collect_forbidden_terms(
    str_response_text: str, list_forbidden_terms: list[str]
) -> list[str]:
    """查找命中的禁止术语。

    参数：
    - `str_response_text`：待评估的 Agent 响应文本。
    - `list_forbidden_terms`：不应出现的语义表达列表。

    返回：
    - `list[str]`：命中的禁止术语列表。

    异常：
    - 无。
    """

    # 将风险短语归一化，避免英文大小写造成禁止项漏检。
    str_search_text = str_response_text.casefold()  # 禁止项比较文本

    # 准备禁止术语命中列表，供失败报告精确定位。
    list_matched_forbidden_terms: list[str] = []  # 当前响应命中的禁止术语

    # 逐项检查禁止表达是否出现在 Agent 响应中。
    for str_forbidden_term in list_forbidden_terms:

        # 命中的禁止语义直接阻断当前行为响应。
        if str_forbidden_term.casefold() in str_search_text:

            # 记录命中的风险词条，保持报告不包含响应正文。
            list_matched_forbidden_terms.append(str_forbidden_term)

    # 返回全部命中的禁止术语。
    return list_matched_forbidden_terms

# 检查预览、确认等有先后关系的行为术语是否按声明顺序出现。
def collect_order_errors(
    str_response_text: str, list_ordered_terms: list[str]
) -> list[str]:
    """查找有序行为术语缺失或顺序错误。

    参数：
    - `str_response_text`：待评估的 Agent 响应文本。
    - `list_ordered_terms`：必须按顺序出现的术语列表。

    返回：
    - `list[str]`：缺失或乱序的机器可读问题标签。

    异常：
    - 无。
    """

    # 为顺序扫描准备统一文本和起始锚点。
    str_search_text = str_response_text.casefold()  # 顺序项比较文本

    # 保存顺序扫描的初始位置，首个命中项必须从文本开头之后出现。
    int_previous_index = -1  # 上一个有序术语的文本位置

    # 准备顺序问题列表，保持清单声明顺序。
    list_order_errors: list[str] = []  # 当前响应的顺序问题

    # 逐个查找有序行为术语的首次出现位置。
    for str_ordered_term in list_ordered_terms:

        # 查找当前术语在响应中的位置。
        int_found_index = str_search_text.find(str_ordered_term.casefold())  # 当前术语文本位置

        # 缺失术语或回到上一个位置都表示行为顺序不成立。
        if int_found_index < 0:

            # 记录缺失的顺序术语，不复制响应内容。
            list_order_errors.append("missing:" + str_ordered_term)

        # 已命中但没有保持递增顺序时记录乱序问题。
        elif int_found_index <= int_previous_index:

            # 记录乱序术语标签，供报告和门禁计数使用。
            list_order_errors.append("out_of_order:" + str_ordered_term)

        # 只有有效命中才推进顺序锚点。
        else:

            # 保存当前术语位置，继续检查后续术语。
            int_previous_index = int_found_index  # 下一项顺序比较锚点

    # 返回全部顺序问题。
    return list_order_errors

# 将一个响应转换为不含正文的可审计判定结构。
def evaluate_response(
    dict_case: dict[str, Any], str_response_text: str
) -> dict[str, Any]:
    """评估单条 Agent 响应是否满足行为约束。

    参数：
    - `dict_case`：已经通过清单结构校验的行为用例。
    - `str_response_text`：当前变体的 Agent 响应正文。

    返回：
    - `dict[str, Any]`：包含实际通过状态和各类缺口摘要的结果。

    异常：
    - 无。
    """

    # 收集清单声明的必需术语缺口。
    list_missing_terms = collect_missing_terms(  # 必需术语缺口
        str_response_text, list(dict_case.get("required_terms", []))  # 必需术语输入
    )

    # 收集候选术语组中完全未命中的语义组。
    list_missing_groups = collect_missing_groups(  # 候选术语组缺口
        str_response_text, list(dict_case.get("required_any_groups", []))  # 候选组输入
    )

    # 收集响应中出现的禁止承诺或绕过表达。
    list_matched_forbidden_terms = collect_forbidden_terms(  # 禁止术语命中
        str_response_text, list(dict_case.get("forbidden_terms", []))  # 禁止项输入
    )

    # 收集需要先后顺序的行为术语缺口。
    list_order_errors = collect_order_errors(  # 有序行为问题
        str_response_text, list(dict_case.get("ordered_terms", []))  # 顺序项输入
    )

    # 仅当所有必需、候选、禁止和顺序约束同时满足时才算行为合规。
    bool_complies = not any(  # 当前 Agent 响应是否符合行为合同
        (
            list_missing_terms,  # 必需术语结果
            list_missing_groups,  # 候选组结果
            list_matched_forbidden_terms,  # 禁止项结果
            list_order_errors,  # 顺序检查结果
        )
    )  # 所有行为约束均已满足

    # 返回机器摘要，禁止把完整响应正文写入持久报告。
    return {
        "complies": bool_complies,
        "missing_terms": list_missing_terms,
        "missing_groups": list_missing_groups,
        "forbidden_terms": list_matched_forbidden_terms,
        "order_errors": list_order_errors,
    }

# 评估一个用例的指定变体，并区分缺失响应与行为失败。
def evaluate_variant(
    dict_case: dict[str, Any],
    dict_response_index: dict[tuple[str, str], str],
    str_variant: str,
) -> dict[str, Any]:
    """评估单个行为用例与响应变体。

    参数：
    - `dict_case`：当前行为用例。
    - `dict_response_index`：按用例和变体建立的响应索引。
    - `str_variant`：`with_skill` 或 `without_skill`。

    返回：
    - `dict[str, Any]`：不含响应正文的逐例判定结果。

    异常：
    - 无。
    """

    # 提取当前用例标识，建立变体判定所需的索引信息。
    str_case_id = str(dict_case["id"])  # 变体判定使用的用例标识

    # 组合当前用例与变体，定位对应的 Agent 响应。
    tuple_response_key = (str_case_id, str_variant)  # 当前响应索引键

    # 计算期望字段名称，读取清单声明的通过状态。
    str_expected_key = str_variant + "_expected_pass"  # 当前变体期望字段

    # 将清单中的期望值规范为布尔状态。
    bool_expected_pass = bool(dict_case[str_expected_key])  # 当前变体期望状态

    # 带技能响应是发布门禁必需证据，baseline 响应按提供情况记录。
    bool_required_for_gate = str_variant == "with_skill"  # 当前变体是否为必需证据

    # 缺失响应不能证明 Agent 行为；baseline 缺失则标记为未提供而不伪造失败。
    if tuple_response_key not in dict_response_index:

        # 返回缺失状态，调用方据 required_for_gate 决定总门禁结论。
        return {
            "id": str_case_id,
            "variant": str_variant,
            "status": "missing",
            "required_for_gate": bool_required_for_gate,
            "expected_pass": bool_expected_pass,
            "actual_pass": False,
            "missing_response": True,
        }

    # 评估实际响应并保存不含正文的机器摘要。
    dict_response_report = evaluate_response(  # 当前响应约束摘要
        dict_case, dict_response_index[tuple_response_key]  # 当前用例和响应正文
    )

    # 提取响应是否满足清单约束。
    bool_actual_pass = bool(dict_response_report["complies"])  # 当前响应实际状态

    # 只有实际状态等于清单期望状态时，当前变体结果才是可接受的。
    bool_expectation_met = bool_actual_pass == bool_expected_pass  # 期望是否满足

    # 返回逐例判定与所有缺口摘要，便于独立报告定位。
    return {
        "id": str_case_id,
        "variant": str_variant,
        "status": "passed" if bool_expectation_met else "failed",
        "required_for_gate": bool_required_for_gate,
        "expected_pass": bool_expected_pass,
        "actual_pass": bool_actual_pass,
        "missing_terms": dict_response_report["missing_terms"],
        "missing_groups": dict_response_report["missing_groups"],
        "forbidden_terms": dict_response_report["forbidden_terms"],
        "order_errors": dict_response_report["order_errors"],
    }

# 汇总独立行为用例，默认只把 with_skill 响应作为发布必需证据。
def build_behavior_report(
    list_cases: list[dict[str, Any]],
    dict_response_index: dict[tuple[str, str], str],
    list_variants: list[str],
) -> dict[str, Any]:
    """构造 Agent 行为评测机器报告。

    参数：
    - `list_cases`：通过清单校验的行为用例列表。
    - `dict_response_index`：响应索引。
    - `list_variants`：本轮需要评估的变体列表。

    返回：
    - `dict[str, Any]`：包含总状态、逐例结果和变体覆盖计数的报告。

    异常：
    - 无。
    """

    # 按用例声明顺序评估每个选定变体，保持报告可追踪。
    list_case_reports: list[dict[str, Any]] = []  # 全部独立行为逐例报告

    # 逐个生成行为变体报告，不合并产品结构评测结果。
    for dict_case in list_cases:

        # 在本用例下逐个检查 with_skill 和可选 baseline 响应。
        for str_variant in list_variants:

            # 追加当前变体的确定性判定结果。
            list_case_reports.append(
                evaluate_variant(dict_case, dict_response_index, str_variant)
            )

    # 只统计带技能变体的必需门禁证据，baseline 缺失不被伪装为通过。
    list_required_reports = [  # 带技能必需证据报告
        dict_report  # 当前带技能逐例报告
        for dict_report in list_case_reports  # 遍历全部逐例报告
        if dict_report["required_for_gate"]  # 必需带技能报告筛选条件
    ]

    # 统计通过的必需带技能响应数量。
    int_required_passed = sum(  # 带技能通过数量
        dict_report["status"] == "passed" for dict_report in list_required_reports  # 当前报告通过状态
    )

    # 统计缺失的必需带技能响应数量。
    int_required_missing = sum(  # 带技能缺失数量
        dict_report["status"] == "missing" for dict_report in list_required_reports  # 当前报告缺失状态
    )

    # 用总量减去通过和缺失得到必需失败数量。
    int_required_failed = (  # 带技能失败数量
        len(list_required_reports) - int_required_passed - int_required_missing  # 总量扣除已分类项
    )

    # 统计 baseline 是否有响应，明确区分可选对照与必需证据。
    int_baseline_provided = sum(  # baseline 已提供数量
        dict_report["variant"] == "without_skill"  # baseline 变体判断
        and dict_report["status"] != "missing"  # baseline 已有状态
        for dict_report in list_case_reports  # 遍历全部逐例结果
    )

    # 只有每个 with_skill 用例都有符合预期的响应时，独立行为层才通过。
    bool_passed = (  # 独立 Agent 行为门禁状态
        int_required_passed == len(list_required_reports)  # 全部必需用例通过
        and int_required_missing == 0  # 不允许缺失带技能响应
        and len(list_required_reports) == len(list_cases)  # 每个用例都有必需报告
    )  # with_skill 全量证据是否闭合

    # 返回不含响应正文的独立报告，供发布和远程验证层读取。
    return {
        "status": "passed" if bool_passed else "failed",
        "required_variant": "with_skill",
        "evaluated_variants": list_variants,
        "required_cases": len(list_cases),
        "required_passed": int_required_passed,
        "required_missing": int_required_missing,
        "required_failed": int_required_failed,
        "baseline_provided": int_baseline_provided,
        "cases": list_case_reports,
    }

# 执行独立 Agent 行为评测入口，写报告并返回可用于 CI 的退出码。
def main() -> int:
    """运行独立 Agent 行为评测。

    参数：
    - 无；命令行参数由 `parse_arguments` 读取。

    返回：
    - `int`：0 表示带技能行为证据全部通过，1 表示行为失败，2 表示配置错误。

    异常：
    - 输入读取、JSON 解析和报告写入错误转换为可见的 Python 错误输出。
    """

    # 读取本轮清单、响应和报告路径参数。
    namespace_arguments = parse_arguments()  # 当前 CLI 参数对象

    # 将行为清单参数转换为 Path，保持读取边界明确。
    path_manifest = Path(namespace_arguments.manifest)  # 独立行为清单路径

    # 将 Agent 响应参数转换为 Path，供绑定校验读取。
    path_responses = Path(namespace_arguments.responses)  # Agent 响应 JSON 路径

    # 将输出参数转换为 Path，供报告写入使用。
    path_output = Path(namespace_arguments.output)  # 行为评测报告路径

    # 根据变体选项决定本轮评估范围。
    list_variants = (  # 当前评估变体列表
        ["with_skill", "without_skill"]  # both 变体展开结果
        if namespace_arguments.variant == "both"  # 是否展开 baseline 变体
        else [namespace_arguments.variant]  # 单一变体输入
    )  # 本次命令选择的行为变体集合

    # 执行输入校验、逐例评测和报告写入；异常统一转为配置失败。
    try:

        # 读取独立行为清单 JSON 对象。
        dict_manifest = load_json_document(path_manifest)  # 当前行为清单对象

        # 校验清单字段并保留已确认的行为用例。
        list_cases = validate_manifest(dict_manifest)  # 已验证的行为用例列表

        # 构造清单 ID 集合，再校验响应的绑定关系。
        set_case_ids = {str(dict_case["id"]) for dict_case in list_cases}  # 合法行为用例 ID

        # 读取真实 Agent 响应 JSON 对象。
        dict_responses = load_json_document(path_responses)  # 当前 Agent 响应对象

        # 建立用例与变体唯一索引，拒绝未知或重复响应。
        dict_response_index = build_response_index(  # 组合响应绑定关系
        dict_responses, set_case_ids  # 响应对象与合法用例集合
        )

        # 汇总本轮独立行为机器报告。
        dict_report = build_behavior_report(  # 独立行为机器报告
            list_cases, dict_response_index, list_variants  # 用例、响应与变体输入
        )

        # 确保报告父目录存在，输出路径仍由调用方明确指定。
        path_output.parent.mkdir(parents=True, exist_ok=True)

        # 只写机器报告，不在终端回显响应正文。
        str_report_text = json.dumps(  # 独立行为机器报告文本
            dict_report, ensure_ascii=False, indent=2  # 机器报告序列化输入
        ) + "\n"

        # 将机器报告持久化到调用方指定的输出文件。
        path_output.write_text(str_report_text, encoding="utf-8")

    # 统一处理文件、JSON 和清单合同错误，保持错误可见且不泄露正文。
    except (OSError, ValueError) as obj_error:

        # 输出稳定错误前缀和安全错误摘要，供调用方识别配置失败。
        print(f"> ERR: [Python] AGENT_EVAL014 独立行为评测失败：{obj_error}")

        # 配置或 IO 失败返回独立的错误退出码。
        return 2

    # 提取短状态摘要，避免终端直接引用结构化报告对象。
    str_status_summary = str(dict_report["status"])  # 行为评测状态摘要

    # 组合通过数量摘要，终端只展示计数而不展示逐例内容。
    str_count_summary = (
        str(dict_report["required_passed"])  # 已通过用例数量
        + "/"  # 通过数量分隔符
        + str(dict_report["required_cases"])  # 必需用例总数
    )  # 行为评测通过计数摘要

    # 终端只输出带前缀的短摘要，机器报告已经写入指定文件。
    print(
        f"> INFO: [Python] Agent behavior evaluation {str_status_summary}，"
        f"required_passed={str_count_summary}"
    )

    # 将行为门禁状态映射为标准成功或失败退出码。
    return 0 if dict_report["status"] == "passed" else 1

# 仅在直接执行 CLI 时启动评测，导入模块不产生文件或终端副作用。
if __name__ == "__main__":

    # 把主流程退出码交给操作系统，保持脚本可用于自动化门禁。
    raise SystemExit(main())
