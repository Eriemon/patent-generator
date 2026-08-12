#!/usr/bin/env python3
"""以本地 HTML 或在线检索词为输入，输出结构化 CNIPA 命中。

stdout_protocol: json
本模块的 CLI stdout 是 machine-readable stdout protocol；调用方依赖完整 JSON 数组读取检索结果。
"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、JSON 编解码、路径和 URL 编码能力。
import argparse
import json
import sys
import urllib.parse
from pathlib import Path

# 引入同目录下的 HTML 抓取与结果解析能力，避免当前入口重复维护同一规则。
from cnipa_epub_crawler import fetch_html
from cnipa_epub_parse import parse_result_items

# 固定 CNIPA 检索结果页基础地址，供关键字检索时拼接查询 URL。
CNIPA_SEARCH_BASE_URL = "https://epub.cnipa.gov.cn/result"  # CNIPA 结果页基础地址

# 构造命令行参数解析器，统一声明本地 HTML 和关键字检索两种输入模式。
def parse_arguments() -> argparse.Namespace:
    """解析命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含本地 HTML、显式 query 与位置检索词的参数对象。

    异常：
    - 参数非法时由 `argparse` 自动结束进程。
    """

    # 初始化 CNIPA 检索入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description="Search CNIPA by local HTML or by a direct keyword query.")  # CNIPA 检索入口命令行解析器

    # 注册本地 HTML 参数，供已有快照或测试夹具直接解析。
    obj_parser.add_argument("--html-file", help="Local HTML file to parse directly.")  # 本地 HTML 输入参数

    # 注册显式 query 参数，供调用方直接传入完整关键字字符串。
    obj_parser.add_argument("--query", help="Keyword query for the CNIPA result page.")  # 显式 query 参数

    # 注册位置参数形式的检索词，兼容更简短的命令行调用方式。
    obj_parser.add_argument("terms", nargs="*", help="Optional positional query terms.")  # 位置检索词参数

    # 返回解析后的参数对象，供主流程判断输入模式。
    return obj_parser.parse_args()

# 合并显式 query 和位置参数检索词，生成最终用于远端检索的关键字文本。
def build_query_text(namespace_arguments: argparse.Namespace) -> str:
    """合并命令行中的检索词。

    参数：
    - `namespace_arguments`：包含 query 与位置检索词的参数对象。

    返回：
    - `str`：最终可用于 CNIPA 检索的关键字文本。

    异常：
    - 无。
    """

    # 在显式 query 已给出时优先使用该值，避免与位置参数混合带来歧义。
    if namespace_arguments.query:

        # 返回显式 query 去首尾空白后的文本，保持调用方原始检索意图。
        return namespace_arguments.query.strip()

    # 过滤掉空白位置参数并按空格拼接，形成最终关键字检索文本。
    str_query_text = " ".join(str_item.strip() for str_item in namespace_arguments.terms if str_item.strip())  # 由位置参数拼接得到的检索词文本

    # 返回位置参数拼接后的检索词文本，供远端 URL 构造逻辑使用。
    return str_query_text

# 执行 CNIPA 结构化检索入口，并以 JSON 协议输出命中结果列表。
def main() -> int:
    """执行 CNIPA 结构化检索入口。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 本地 HTML 缺失或缺少检索词时抛出相关异常。
    - 远端抓取失败时由底层异常上抛。
    """

    # 解析命令行参数，确定当前是本地 HTML 解析还是在线检索模式。
    namespace_arguments = parse_arguments()  # CNIPA 检索入口参数对象

    # 在给定本地 HTML 文件时直接走本地解析模式，避免不必要的网络访问。
    if namespace_arguments.html_file:

        # 解析本地 HTML 文件绝对路径，避免相对路径受调用目录影响。
        path_html_file = Path(namespace_arguments.html_file).resolve()  # 本地 HTML 文件路径

        # 在本地 HTML 文件不存在时立即报错，避免输出空数组掩盖真实问题。
        if not path_html_file.exists():

            # 抛出明确错误，提醒调用方检查本地 HTML 文件路径。
            raise FileNotFoundError("> ERR: [Python] 指定的本地 HTML 文件不存在。")

        # 读取本地 HTML 文本并解析成结构化命中数组。
        list_hits = parse_result_items(path_html_file.read_text(encoding="utf-8"))  # 本地 HTML 解析结果列表

        # 以单次 JSON dump 输出本地解析结果，供上游程序直接消费。
        json.dump(list_hits, sys.stdout, ensure_ascii=False, indent=2)

        # 返回成功状态码，表示本地 HTML 解析已经完成。
        return 0

    # 合并显式 query 和位置参数检索词，生成最终在线检索文本。
    str_query_text = build_query_text(namespace_arguments)  # 最终在线检索词文本

    # 在检索词为空时立即报错，避免构造无意义的空查询 URL。
    if not str_query_text:

        # 抛出明确错误，提醒调用方提供 HTML 文件或检索词。
        raise ValueError("> ERR: [Python] 请提供 --html-file 或检索词。")

    # 基于检索词构造 CNIPA 结果页 URL，供远端抓取逻辑复用。
    str_search_url = f"{CNIPA_SEARCH_BASE_URL}?keyword={urllib.parse.quote(str_query_text)}"  # CNIPA 结果页检索 URL

    # 抓取远端结果页 HTML 并解析成结构化命中数组。
    list_hits = parse_result_items(fetch_html(str_search_url))  # 在线检索解析结果列表

    # 以单次 JSON dump 输出在线检索结果，供上游程序直接消费。
    json.dump(list_hits, sys.stdout, ensure_ascii=False, indent=2)

    # 返回成功状态码，表示在线检索与结果解析已经完成。
    return 0

# 保留标准命令行入口，方便直接执行 CNIPA 结构化检索脚本。
if __name__ == "__main__":

    # 使用 main 的返回值作为进程退出码，保持 CLI 行为一致。
    raise SystemExit(main())
