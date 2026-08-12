#!/usr/bin/env python3
"""基于主案结果生成查新问题规划。"""
from __future__ import annotations

# 这里引入标准库参数、序列化和路径工具，供查新规划入口完成本地读写与规则整理。
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 这里解析命令行参数，锁定本次查新规划要处理的案件目录。
def parse_arguments() -> argparse.Namespace:
    """
    解析查新规划入口参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含案件目录的参数对象。

    异常：
    - 参数缺失时由 `argparse` 自动结束进程。
    """

    # 这里先准备命令行说明文本，便于解析器清楚表达本脚本职责。
    str_description = "Plan governed prior-art queries from the selected invention point."  # 查新规划说明文本

    # 这里构造命令行解析器，说明本脚本负责根据主案结果生成查新规划。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 查新规划命令行解析器

    # 这里要求调用方提供案件目录，保证输入输出都落在同一案件空间。
    obj_parser.add_argument(  # 案件目录参数
        "--case-dir",
        required=True,
        help="Case directory containing selected invention outputs.",
    )

    # 这里返回解析后的参数对象，供主流程继续定位主案文件和输出文件。
    return obj_parser.parse_args()

# 这里确保结果目录存在，供查新规划 Markdown 稳定落盘。
def ensure_dir(path_dir: Path) -> Path:
    """
    创建目录并返回目录路径。

    参数：
    - `path_dir`：需要确保存在的目录路径。

    返回：
    - `Path`：已经确认存在的目录路径。

    异常：
    - 底层目录创建失败时由文件系统异常上抛。
    """

    # 这里递归创建目标目录，允许调用方直接传入多级路径。
    path_dir.mkdir(parents=True, exist_ok=True)  # 已确保存在的目录路径

    # 这里返回目录对象，方便主流程继续拼接结果文件路径。
    return path_dir

# 这里统一读取 UTF-8 JSON 文件，减少查新规划入口的重复文件处理逻辑。
def read_json_file(path_file: Path) -> Any:
    """
    读取 UTF-8 JSON 文件。

    参数：
    - `path_file`：待读取的 JSON 文件路径。

    返回：
    - `Any`：反序列化后的 Python 数据结构。

    异常：
    - 文件不存在、编码错误或 JSON 语法错误时由底层异常上抛。
    """

    # 这里读取原始 JSON 文本，供统一反序列化处理。
    str_json_text = path_file.read_text(encoding="utf-8")  # JSON 原始文本

    # 这里返回解析结果，供主流程继续读取主案和保护焦点字段。
    return json.loads(str_json_text)

# 这里统一写入 UTF-8 文本文件，保证 Markdown 报告落盘前自动创建父目录。
def write_text_file(path_file: Path, str_text: str) -> None:
    """
    写入 UTF-8 文本文件。

    参数：
    - `path_file`：目标文本文件路径。
    - `str_text`：待写入的文本内容。

    返回：
    - `None`。

    异常：
    - 底层目录创建或文件写入失败时由文件系统异常上抛。
    """

    # 这里先确保父目录存在，避免调用方在写报告前手动建目录。
    path_parent_dir = ensure_dir(path_file.parent)  # 目标文件父目录

    # 这里把文本内容按 UTF-8 写入目标文件，保证中文审阅材料直接可读。
    (path_parent_dir / path_file.name).write_text(str_text, encoding="utf-8")  # 已写入的目标文本文件

# 这里去重并保留首次出现顺序，避免检索词草案中重复堆叠同类短语。
def unique_items(list_values: list[str]) -> list[str]:
    """
    对字符串列表去重并保持首次出现顺序。

    参数：
    - `list_values`：待去重的字符串列表。

    返回：
    - `list[str]`：去重后的字符串列表。

    异常：
    - 无。
    """

    # 这里初始化去重后的字符串列表，按首次出现顺序保留结果。
    list_unique_values: list[str] = []  # 去重后的字符串列表

    # 这里初始化已见集合，避免重复短语反复写入规划结果。
    set_seen_values: set[str] = set()  # 已见字符串集合

    # 这里逐个处理输入字符串，保证查新短语列表简洁可读。
    for str_value in list_values:

        # 这里先清理当前字符串两端空白，避免空项和格式噪声混入结果。
        str_clean_value = str(str_value).strip()  # 清理后的当前字符串

        # 这里跳过空字符串或已出现项，避免输出冗余内容。
        if not str_clean_value or str_clean_value in set_seen_values:

            # 这里直接进入下一项，保持结果列表只留下真正有用的短语。
            continue

        # 这里登记当前字符串，标记该短语已经进入结果集。
        set_seen_values.add(str_clean_value)

        # 这里保留当前短语，供后续查新问题规划直接展示。
        list_unique_values.append(str_clean_value)

    # 这里返回去重后的短语列表，供 Markdown 渲染继续使用。
    return list_unique_values

# 这里根据主案摘要和保护焦点整理检索词草案，供人工快速形成查新起点。
def build_query_phrases(dict_selected: dict[str, Any]) -> list[str]:
    """
    生成查新检索词草案。

    参数：
    - `dict_selected`：当前选中的主案记录。

    返回：
    - `list[str]`：去重后的查新检索词草案列表。

    异常：
    - 无。
    """

    # 这里读取主案保护焦点摘要，供检索式拼接时优先引用关键特征。
    dict_strategy = dict_selected.get("protection_strategy", {})  # 主案保护焦点摘要

    # 这里读取必要技术特征列表，供检索式优先覆盖独立项关键边界。
    list_focus_features = list(dict_strategy.get("independent_claim_focus", []))  # 必要技术特征列表

    # 这里读取可选技术特征列表，供检索式补充从属方向和实现变体。
    list_optional_features = list(dict_strategy.get("optional_features", []))  # 可选技术特征列表

    # 这里读取技术术语列表，供检索式补充领域同义线索。
    list_terms = list(dict_selected.get("technical_terms", []))  # 技术术语列表

    # 这里读取主案名称，供检索式保留发明主题识别词。
    str_name = str(dict_selected.get("name") or "[待确认：主专利点]")  # 主案名称

    # 这里读取技术问题摘要，供检索式覆盖现有技术痛点和限制条件。
    str_problem = str(dict_selected.get("problem") or "[待确认：技术问题]")  # 技术问题摘要

    # 这里读取技术方案摘要，供检索式覆盖核心实现路径。
    str_solution = str(dict_selected.get("solution") or "[待确认：技术方案]")  # 技术方案摘要

    # 这里拼接必要特征检索短语，优先覆盖独立项最核心的边界特征。
    str_focus_query = " ".join(list_focus_features[:3])  # 必要特征检索短语

    # 这里拼接扩展特征检索短语，补充从属项和实现变体的组合线索。
    str_extended_query = " ".join(list_focus_features[:2] + list_optional_features[:2])  # 扩展特征检索短语

    # 这里拼接术语检索短语，补充领域常用术语和同义表达。
    str_terms_query = " ".join(list_terms[:6])  # 术语检索短语

    # 这里组装首批查新短语，优先覆盖主题、问题、核心特征和术语变体。
    list_query_phrases = [str_name, str_problem, str_solution, str_focus_query, str_extended_query, str_terms_query]  # 原始查新短语列表

    # 这里返回去重后的查新短语列表，保证输出简洁且不重复。
    return unique_items(list_query_phrases)

# 这里把主案与检索重点渲染成 Markdown 报告，方便人工快速审阅查新起点。
def render_markdown(dict_bundle: dict[str, Any]) -> str:
    """
    生成查新问题规划 Markdown 报告文本。

    参数：
    - `dict_bundle`：主案选择结果包。

    返回：
    - `str`：最终写入文件的 Markdown 报告文本。

    异常：
    - 无。
    """

    # 这里读取当前主案记录，供报告各小节统一引用主案内容。
    dict_selected = dict_bundle["selected"]  # 当前主案记录

    # 这里读取主案保护焦点摘要，供检索重点小节直接复用关键特征。
    dict_strategy = dict_selected["protection_strategy"]  # 当前主案保护焦点摘要

    # 这里生成查新检索词草案，供报告列出第一轮检索起点。
    list_query_phrases = build_query_phrases(dict_selected)  # 查新检索词草案列表

    # 这里初始化 Markdown 行列表，先写主案摘要和检索重点概览。
    list_lines = [
        "# Prior Art Query Plan",  # 报告标题
        "",  # 标题与主案摘要之间留空
        "## 主案摘要",  # 主案摘要章节标题
        "",  # 章节标题后留空
        f"- 名称：{dict_selected['name']}",  # 供人工确认的主案标题
        f"- 技术问题：{dict_selected['problem']}",  # 主案问题摘要
        f"- 核心方案：{dict_selected['solution']}",  # 主案方案摘要
        "- 必要技术特征：" + "、".join(dict_strategy["independent_claim_focus"]),  # 独立项关键特征
        "- 可选技术特征：" + "、".join(dict_strategy["optional_features"]),  # 从属项补充特征
        "",  # 主案摘要与检索重点之间留空
        "## 检索重点",  # 检索重点章节标题
        "",  # 检索重点标题后留空一行
        "- 先围绕技术问题、核心方案和必要特征组合检索。",  # 第一轮检索策略
        "- 再围绕术语变体、实现约束和可选特征补充扩展检索。",  # 第二轮检索策略
        "",  # 检索重点与检索词草案之间留空
        "## 检索词草案",  # 检索词草案章节标题
    ]  # Markdown 开场内容

    # 这里逐条写入检索词草案，供人工快速复制或继续细化。
    for int_index, str_query_phrase in enumerate(list_query_phrases, start=1):

        # 这里把当前检索短语写成编号条目，保持报告结构清晰可读。
        list_lines.append(f"{int_index}. {str_query_phrase}")

    # 这里进入人工确认小节，提醒调用方不要把检索草案直接当成最终策略。
    list_lines.extend(
        [
            "",  # 检索词草案与人工确认之间留空
            "## 人工确认",  # 人工确认章节标题
            "",  # 人工确认标题后留空一行
            "- 请确认问题边界、关键特征和术语同义表达是否需要补充。",  # 需要人工确认的问题边界
            "- 请在正式检索前补上最接近的 baseline、论文和公开专利线索。",  # 需要人工补齐的现有技术线索
        ]
    )

    # 这里返回最终 Markdown 文本，供主流程统一写入案件目录。
    return "\n".join(list_lines)

# 这里执行查新问题规划主流程，并把 Markdown 路径写到标准输出末尾。
def main() -> int:
    """
    执行查新问题规划主流程。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 缺少主案输入文件或结果写入失败时由底层异常上抛。
    """

    # 这里解析命令行参数，锁定当前查新规划要处理的案件目录。
    namespace_arguments = parse_arguments()  # 查新规划入口参数

    # 这里解析案件目录绝对路径，保证输入读取和结果落盘都指向同一案件空间。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 案件根目录

    # 这里固定主案 JSON 路径，作为查新规划唯一接受的结构化输入。
    path_selected_json = path_case_dir / "02_facts" / "selected_invention_point.json"  # 主案选择 JSON 路径

    # 这里在缺少主案输入时立即报错，避免查新规划在无主案场景下伪造成功。
    if not path_selected_json.exists():

        # 这里抛出明确错误，提醒调用方先完成主案选择步骤。
        raise FileNotFoundError("> ERR: [Python] 缺少 selected_invention_point.json，请先完成主案选择")

    # 这里读取主案结果包，作为查新问题规划和 Markdown 渲染的唯一输入。
    dict_bundle = read_json_file(path_selected_json)  # 主案结果包

    # 这里渲染查新规划 Markdown 文本，供人工快速审阅检索起点。
    str_markdown = render_markdown(dict_bundle)  # 查新问题规划 Markdown 文本

    # 这里固定查新规划 Markdown 路径，保持正式中间产物落在 facts 阶段目录中。
    path_output_markdown = path_case_dir / "02_facts" / "prior_art_query_plan.md"  # 查新问题规划 Markdown 路径

    # 这里把查新规划 Markdown 报告写入案件目录，供预览和人工审阅继续使用。
    write_text_file(path_output_markdown, str_markdown)

    # 这里把 Markdown 报告路径作为机器可读输出写给上游流程。
    sys.stdout.write(str(path_output_markdown.resolve()) + "\n")

    # 这里返回成功状态码，表示查新问题规划已经完成并写入案件目录。
    return 0

# 这里保留标准脚本入口，方便命令行和流水线子进程统一调用查新规划入口。
if __name__ == "__main__":

    # 这里通过标准退出路径返回状态码，保持命令行调用行为一致。
    raise SystemExit(main())
