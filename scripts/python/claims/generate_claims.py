#!/usr/bin/env python3
"""根据正式交底书草稿生成本地权利要求草案。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、按路径加载模块、标准输出和路径能力，供权利要求入口稳定运行。
import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 引入正则能力，供正文标题、步骤和模块描述的结构化提取逻辑复用。
import re

# 固定共享运行时支持模块路径，避免通过修改 sys.path 导入公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 预编译发明名称标题匹配规则，供正文标题提取逻辑稳定复用。
RE_DISCLOSURE_TITLE = re.compile(r"## 一、发明名称\s+(.+)", re.S)  # 发明名称标题匹配规则

# 预编译方法步骤匹配规则，提取形如 S101 的方法步骤摘要。
RE_METHOD_STEP = re.compile(r"^(S\d{3,4})：(.+)$", re.M)  # 方法步骤匹配规则

# 预编译模块描述匹配规则，提取模块名称及其对应功能描述。
RE_SYSTEM_MODULE = re.compile(r"^\d+\.\s*([^，,]+模块)[，,]\s*用于\s*(.+)$", re.M)  # 系统模块匹配规则

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

    # 执行共享支持模块源码，把公共文本和文件工具装入模块对象。
    obj_spec.loader.exec_module(module_runtime_support)

    # 返回已完成加载的共享支持模块，供正文后链入口复用。
    return module_runtime_support

# 构造命令行参数解析器，统一声明案件目录和可选输入草稿参数。
def build_parser() -> argparse.ArgumentParser:
    """构造权利要求草案入口的命令行解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册参数的解析器对象。

    异常：
    - 无。
    """

    # 先准备解析器说明文本，避免初始化语句过长。
    str_description = "Generate governed claims draft from the disclosure markdown."  # 入口说明文本

    # 初始化当前权利要求入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 权利要求入口解析器

    # 注册案件目录参数，确保草案固定写回当前案件空间。
    obj_parser.add_argument("--case-dir", required=True)

    # 注册可选输入草稿参数，允许覆盖自动定位的 disclosure draft。
    obj_parser.add_argument("--input", help="Optional disclosure markdown path.")

    # 返回完成参数注册的解析器对象。
    return obj_parser

# 从交底书 Markdown 中提取发明名称，供后续权利要求标题统一复用。
def extract_title(str_markdown: str, module_runtime_support: Any) -> str:
    """提取发明名称。

    参数：
    - `str_markdown`：交底书草稿 Markdown 全文。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `str`：已清洗的发明名称；提取失败时返回兜底标题。

    异常：
    - 无。
    """

    # 在正文中搜索发明名称章节，定位规范标题下的首行内容。
    obj_match = RE_DISCLOSURE_TITLE.search(str_markdown)  # 发明名称章节匹配结果

    # 在未命中标题章节时回退到受控默认标题，避免生成空白权利要求。
    if not obj_match:

        # 返回待确认兜底标题，让后续草案仍然可以继续生成和审阅。
        return "一种待确认技术方案"

    # 提取命中的首行标题文本，避免多行内容混入权利要求名称。
    str_title_line = obj_match.group(1).splitlines()[0]  # 标题章节首行文本

    # 返回清洗后的发明名称，去除正文里的多余空白和噪声标记。
    return module_runtime_support.clean_text(str_title_line)

# 从交底书 Markdown 中提取方法步骤，为独立方法权利要求提供骨架。
def extract_method_steps(str_markdown: str, module_runtime_support: Any) -> list[dict[str, str]]:
    """提取方法步骤摘要。

    参数：
    - `str_markdown`：交底书草稿 Markdown 全文。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[dict[str, str]]`：步骤编号和摘要组成的列表。

    异常：
    - 无。
    """

    # 先准备步骤结果列表，后续逐项登记已命中的方法步骤。
    list_step_records: list[dict[str, str]] = []  # 方法步骤结果列表

    # 逐项遍历正文中命中的步骤编号与摘要文本。
    for str_step_id, str_summary in RE_METHOD_STEP.findall(str_markdown):

        # 组装当前步骤的结构化记录，供权利要求正文和映射说明共同复用。
        dict_step_record = {  # 单个方法步骤记录
            "id": str_step_id,  # 步骤编号
            "summary": module_runtime_support.clean_text(str_summary),  # 步骤摘要
        }

        # 把当前步骤记录追加到结果列表，保持正文原始顺序。
        list_step_records.append(dict_step_record)

    # 返回结构化方法步骤列表，供独立项和从属项生成逻辑复用。
    return list_step_records

# 从交底书 Markdown 中提取系统模块，用于生成系统权利要求中的模块描述。
def extract_system_modules(str_markdown: str, module_runtime_support: Any) -> list[dict[str, str]]:
    """提取系统模块描述。

    参数：
    - `str_markdown`：交底书草稿 Markdown 全文。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[dict[str, str]]`：模块名称与功能描述组成的列表。

    异常：
    - 无。
    """

    # 先准备模块结果列表，后续逐项登记命中的系统模块。
    list_module_records: list[dict[str, str]] = []  # 系统模块结果列表

    # 逐项遍历正文中命中的模块名称与功能描述。
    for str_name, str_function in RE_SYSTEM_MODULE.findall(str_markdown):

        # 组装当前模块记录，保留名称与功能的一一对应关系。
        dict_module_record = {  # 单个系统模块记录
            "name": module_runtime_support.clean_text(str_name),  # 模块名称
            "function": module_runtime_support.clean_text(str_function),  # 模块功能
        }

        # 把当前模块记录追加到结果列表，保持正文模块顺序。
        list_module_records.append(dict_module_record)

    # 返回结构化系统模块列表，供系统独立项生成逻辑复用。
    return list_module_records

# 读取正文草稿对应的证据映射，为权利要求与来源支持关系登记提供输入。
def load_support_map(path_case_dir: Path, module_runtime_support: Any) -> dict[str, Any]:
    """读取来源证据映射。

    参数：
    - `path_case_dir`：案件根目录路径。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：证据映射字典；缺失时返回空特征列表。

    异常：
    - 映射文件存在但 JSON 非法时由底层异常上抛。
    """

    # 固定正文阶段产出的证据映射路径，供权利要求映射说明复用。
    path_support_map = path_case_dir / "03_drafts" / "latest_evidence_map.json"  # 正文证据映射文件路径

    # 在映射文件缺失时返回空特征列表，允许最小样例继续生成草案。
    if not path_support_map.exists():

        # 返回空映射结果，保持本地 smoke 样例的最小闭环能力。
        return {"features": []}

    # 读取已有证据映射，供权利要求支持关系登记逻辑复用。
    return module_runtime_support.read_json_file(path_support_map)

# 基于方法步骤构造独立方法权利要求，保持最小可审阅的主权项骨架。
def build_method_claim(str_title: str, list_steps: list[dict[str, str]]) -> str:
    """生成独立方法权利要求。

    参数：
    - `str_title`：发明名称。
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `str`：独立方法权利要求文本。

    异常：
    - 无。
    """

    # 统一去掉标题中重复的“一种”前缀，避免权利要求开头重复用词。
    str_claim_subject = str_title.replace("一种", "")  # 独立方法权利要求主题

    # 在步骤缺失时回退到最小方法权利要求，避免当前流程完全中断。
    if not list_steps:

        # 返回待确认兜底独立项，提醒审阅者后续补齐真实步骤。
        return f"1. 一种{str_claim_subject}，其特征在于，包括执行待确认的技术处理流程。"

    # 先准备独立方法权利要求文本行列表，再逐步追加步骤描述。
    list_claim_lines = [  # 独立方法权利要求文本行列表
        f"1. 一种{str_claim_subject}，其特征在于，包括：",  # 独立方法项首行
    ]

    # 按正文步骤顺序逐项补入方法步骤，保持与正文草稿的一致性。
    for int_index, dict_step in enumerate(list_steps, start=1):

        # 对非最后一步使用分号，对最后一步使用句号结束整条权利要求。
        str_suffix = "；" if int_index < len(list_steps) else "。"  # 当前步骤尾部标点

        # 组装当前步骤文本，保留步骤编号与摘要的一一对应关系。
        str_step_line = f"   {dict_step['id']}，{dict_step['summary']}{str_suffix}"  # 当前方法步骤文本行

        # 把当前步骤文本追加到独立项内容中。
        list_claim_lines.append(str_step_line)

    # 返回独立方法权利要求全文，供最终 Markdown 渲染逻辑写入草案。
    return "\n".join(list_claim_lines)

# 生成固定的从属方法权利要求，用于补强多参数筛选与反馈更新两个保护方向。
def build_dependent_claims(list_steps: list[dict[str, str]], start_no: int) -> list[str]:
    """生成从属方法权利要求。

    参数：
    - `list_steps`：结构化方法步骤列表。
    - `start_no`：首条从属项的编号。

    返回：
    - `list[str]`：从属方法权利要求文本列表。

    异常：
    - 无。
    """

    # 在正文还没有可用步骤时不生成固定从属项，避免形成明显失配内容。
    if not list_steps:

        # 返回空列表，让后续系统项仍可继续按既定编号落位。
        return []

    # 先准备从属方法权利要求列表，后续按固定方向写入两条补强项。
    list_claims: list[str] = []  # 从属方法权利要求列表

    # 追加第一条从属项，补强多参数筛选方向的保护表述。
    list_claims.append(
        f"{start_no}. 根据权利要求1所述的方法，其特征在于，"
        "所述步骤至少基于多个状态参数的组合结果进行候选对象筛选。"
    )

    # 追加第二条从属项，补强异常反馈与下一轮处理更新方向。
    list_claims.append(
        f"{start_no + 1}. 根据权利要求1所述的方法，其特征在于，"
        "当执行结果出现异常或失败时，记录反馈信息并更新下一轮处理依据。"
    )

    # 返回固定从属项列表，供最终 Markdown 渲染逻辑复用。
    return list_claims

# 基于系统模块描述构造系统独立权利要求，保持与正文模块化方案的映射关系。
def build_system_claim(str_title: str, list_modules: list[dict[str, str]], claim_no: int) -> str:
    """生成系统独立权利要求。

    参数：
    - `str_title`：发明名称。
    - `list_modules`：结构化系统模块列表。
    - `claim_no`：系统独立项编号。

    返回：
    - `str`：系统独立权利要求文本。

    异常：
    - 无。
    """

    # 统一去掉标题中重复的“一种”前缀，避免系统项表述出现重复。
    str_claim_subject = str_title.replace("一种", "")  # 系统独立权利要求主题

    # 在模块描述缺失时回退到处理模块兜底表述，保证系统项仍可生成。
    if not list_modules:

        # 返回最小系统独立项，提醒后续审阅阶段补齐真实模块方案。
        return (
            f"{claim_no}. 一种{str_claim_subject}系统，其特征在于，"
            "包括用于执行权利要求1所述方法的处理模块。"
        )

    # 先把模块名称汇总成一条主句，供系统独立项首行复用。
    str_module_names = "、".join(dict_module["name"] for dict_module in list_modules)  # 模块名称串接文本

    # 先准备系统独立项文本行列表，再逐项追加模块功能说明。
    list_claim_lines = [  # 系统独立项文本行列表
        f"{claim_no}. 一种{str_claim_subject}系统，其特征在于，包括：{str_module_names}；",  # 系统独立项首行
    ]

    # 按正文模块顺序逐项追加功能说明，保持与正文结构一致。
    for dict_module in list_modules:

        # 组装当前模块说明文本，保留名称和功能的稳定对应关系。
        str_module_line = f"   其中，{dict_module['name']}用于 {dict_module['function']}。"  # 当前模块说明文本行

        # 把当前模块说明文本追加到系统独立项中。
        list_claim_lines.append(str_module_line)

    # 返回完整系统独立权利要求文本，供最终 Markdown 渲染逻辑写入草案。
    return "\n".join(list_claim_lines)

# 汇总方法步骤与证据映射关系，生成最小 claim-support 结构化产物。
def build_claim_support_map(
    list_steps: list[dict[str, str]],
    dict_support_map: dict[str, Any],
) -> dict[str, Any]:
    """生成权利要求与来源证据的轻量映射。

    参数：
    - `list_steps`：结构化方法步骤列表。
    - `dict_support_map`：正文阶段产出的证据映射字典。

    返回：
    - `dict[str, Any]`：claim-support 结构化映射字典。

    异常：
    - 无。
    """

    # 先准备步骤到支持证据的映射字典，供后续按步骤编号回填支持来源。
    dict_step_support: dict[str, list[str]] = {}  # 步骤到证据编号的映射字典

    # 逐项遍历正文阶段输出的特征列表，只保留声明了步骤编号的记录。
    for dict_feature in dict_support_map.get("features", []):

        # 读取当前特征对应的步骤编号，缺失时后续直接跳过。
        str_step_id = dict_feature.get("step", "")  # 当前特征关联的步骤编号

        # 在当前特征没有声明步骤编号时直接跳过，避免空键污染映射。
        if not str_step_id:

            # 跳过无法定位到步骤的特征记录，保持映射结构可读。
            continue

        # 读取当前特征对应的支持证据编号列表，缺失时回退为空列表。
        list_support_ids = dict_feature.get("support_ids", [])  # 当前特征对应的支持证据编号列表

        # 把当前步骤对应的证据编号列表登记到映射字典中。
        dict_step_support[str_step_id] = list_support_ids  # 当前步骤对应的支持证据编号列表

    # 提取正文步骤编号列表，供独立项映射说明和证据聚合共同复用。
    list_step_ids = [dict_step["id"] for dict_step in list_steps]  # 正文方法步骤编号列表

    # 先准备独立项聚合证据列表，后续按步骤顺序收集支持编号。
    list_all_support_ids: list[str] = []  # 独立方法权利要求聚合支持证据列表

    # 按正文步骤顺序汇总支持证据编号，保持映射与正文骨架同步。
    for str_step_id in list_step_ids:

        # 取回当前步骤要并入独立项映射的证据编号集合。
        list_step_support_ids = dict_step_support.get(str_step_id, [])  # 当前步骤待聚合的证据编号列表

        # 把当前步骤的支持证据编号扩展到聚合列表中。
        list_all_support_ids.extend(list_step_support_ids)

    # 利用字典去重特性保留首次出现顺序，得到独立项支持证据编号列表。
    list_unique_support_ids = list(dict.fromkeys(list_all_support_ids))  # 去重后的支持证据编号列表

    # 返回最小 claim-support 结构化映射，供 review 和 export 阶段继续复用。
    return {
        "claim_support": [
            {
                "claim_no": 1,
                "type": "independent_method",
                "mapped_steps": list_step_ids,
                "support_ids": list_unique_support_ids,
            }
        ]
    }

# 组装权利要求草案 Markdown 文本，统一输出权利要求书和说明书映射说明。
def render_claims_markdown(
    str_title: str,
    list_steps: list[dict[str, str]],
    list_modules: list[dict[str, str]],
) -> str:
    """渲染权利要求草案 Markdown 文本。

    参数：
    - `str_title`：发明名称。
    - `list_steps`：结构化方法步骤列表。
    - `list_modules`：结构化系统模块列表。

    返回：
    - `str`：完整权利要求草案 Markdown 文本。

    异常：
    - 无。
    """

    # 生成独立方法权利要求文本，作为权利要求书的核心主权项。
    str_method_claim = build_method_claim(str_title, list_steps)  # 独立方法权利要求文本

    # 生成两条固定补强项，供当前最小草案覆盖筛选与反馈两个保护方向。
    list_dependent_claims = build_dependent_claims(list_steps, start_no=2)  # 固定从属项文本列表

    # 生成系统独立权利要求文本，保持与正文模块化方案的映射。
    str_system_claim = build_system_claim(str_title, list_modules, claim_no=4)  # 系统独立权利要求文本

    # 先准备 Markdown 文本行列表，按固定章节顺序组装权利要求草案。
    list_markdown_lines = [  # 权利要求草案 Markdown 文本行列表
        "# 权利要求草案",  # 草案标题
        "",  # 标题后的空行
        "## 一、权利要求书",  # 权利要求书章节标题
        "",  # 章节标题后的空行
        str_method_claim,  # 独立方法权利要求正文
        "",  # 独立方法项后的空行
    ]

    # 逐条追加从属方法权利要求，保持与主权项之间的自然排版关系。
    for str_claim_text in list_dependent_claims:

        # 把当前从属项正文追加到 Markdown 文本行列表中。
        list_markdown_lines.append(str_claim_text)

    # 在从属项之后追加系统项、设备项、介质项和映射说明章节。
    list_markdown_lines.extend(
        [
            "",
            str_system_claim,
            "",
            "5. 一种电子设备，包括处理器和存储器，所述存储器中存储有程序指令，"
            "所述程序指令被所述处理器执行时实现权利要求1至3任一项所述的方法。",
            "",
            "6. 一种计算机可读存储介质，其上存储有计算机程序，所述计算机程序被处理器执行时实现权利要求1至3任一项所述的方法。",
            "",
            "## 二、说明书映射说明",
            "",
            "- 权利要求1对应正文 4.2.1 方法流程中的全部步骤。",
            "- 从属方法权利要求用于补强多参数筛选和反馈更新两个保护方向。",
            "- 系统权利要求对应正文 4.2.2 模块化方案。",
            "",
        ]
    )

    # 返回完整 Markdown 文本，供后续落盘到案件目录。
    return "\n".join(list_markdown_lines)

# 执行权利要求草案生成入口，读取正文草稿并落盘 Markdown 与映射 JSON。
def main() -> int:
    """执行权利要求草案生成入口。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 找不到正文草稿时抛出 `FileNotFoundError`。
    - 共享支持加载、文件读写或 JSON 序列化失败时由底层异常上抛。
    """

    # 加载共享运行时支持模块，复用正文后链的一致文件与文本处理逻辑。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 解析命令行参数，读取案件目录和可选输入草稿路径。
    namespace_arguments = build_parser().parse_args()  # 权利要求入口参数对象

    # 解析案件目录绝对路径，确保产物固定落在当前案件空间。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 当前案件根目录

    # 在调用方显式给出输入草稿时解析其绝对路径，否则保留空值供自动定位逻辑处理。
    path_input = Path(namespace_arguments.input).resolve() if namespace_arguments.input else None  # 显式指定的输入草稿路径

    # 定位当前案件可用的 disclosure draft，优先使用显式输入路径。
    path_markdown = module_runtime_support.find_disclosure_draft(path_case_dir, path_input)  # 当前案件正文草稿路径

    # 在找不到可用正文草稿时立即报错，避免生成与案件脱节的空壳权利要求。
    if path_markdown is None or not path_markdown.exists():

        # 抛出明确错误，提醒调用方先完成 disclosure draft 阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 disclosure draft markdown。")

    # 读取正文草稿全文，供标题、步骤和模块提取逻辑复用。
    str_markdown = path_markdown.read_text(encoding="utf-8")  # 正文草稿 Markdown 全文

    # 提取发明名称，供独立方法项、系统项和说明章节统一复用。
    str_title = extract_title(str_markdown, module_runtime_support)  # 发明名称

    # 提取结构化方法步骤，供方法权利要求和 support map 复用。
    list_steps = extract_method_steps(str_markdown, module_runtime_support)  # 结构化方法步骤列表

    # 提取系统模块清单，供系统独立项主句与模块功能说明共同复用。
    list_modules = extract_system_modules(str_markdown, module_runtime_support)  # 结构化系统模块列表

    # 读取正文阶段产出的证据映射，为 claim-support JSON 提供输入。
    dict_support_map = load_support_map(path_case_dir, module_runtime_support)  # 正文证据映射字典

    # 渲染完整权利要求草案 Markdown 文本，供案件目录落盘。
    str_claims_markdown = render_claims_markdown(str_title, list_steps, list_modules)  # 完整权利要求草案 Markdown 文本

    # 生成 claim-support 结构化映射，供 review 和 export 阶段复用。
    dict_claim_support_map = build_claim_support_map(list_steps, dict_support_map)  # claim-support 结构化映射字典

    # 固定权利要求草案 Markdown 输出路径，保持案件目录产物位置稳定。
    path_claims_markdown = path_case_dir / "03_drafts" / "claims_draft.md"  # 权利要求草案 Markdown 输出路径

    # 固定 claim-support JSON 输出路径，供后链工具按约定读取。
    path_claims_map = path_case_dir / "03_drafts" / "claims_map.json"  # claim-support JSON 输出路径

    # 把权利要求草案 Markdown 写入案件目录，供审阅和后链工具继续复用。
    module_runtime_support.write_text_file(path_claims_markdown, str_claims_markdown)

    # 把 claim-support JSON 写入案件目录，供 review 与 export 阶段复用。
    module_runtime_support.write_json_file(path_claims_map, dict_claim_support_map)

    # 把权利要求草案绝对路径作为机器可读输出写回上游流程。
    sys.stdout.write(str(path_claims_markdown.resolve()) + "\n")

    # 返回成功状态码，表示 Markdown 与 claim-support 都已落盘。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
