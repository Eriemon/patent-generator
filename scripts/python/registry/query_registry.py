"""只读查询注册表且永不执行命中命令。

stdout_protocol: json
当调用方使用 `--json` 时，stdout 只包含单个完整 JSON 对象。
"""

# 启用延迟注解，保持查询类型标注在 Python 3.10 及以上版本稳定可用。
from __future__ import annotations

# 标准库
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Sequence

# 同目录退出码与错误协议
from registry_common import (
    INT_EXIT_NO_HIT,
    INT_EXIT_OK,
    INT_EXIT_REQUEST,
    RegistryError,
)

# 同目录加载、检查与路径能力
from registry_common import (
    inspect_database,
    load_registry,
    registry_root,
    resolve_skill_root,
)

# 查询种类与数据库 kind 字段保持完全一致。
TUPLE_QUERY_KINDS = ("command", "workflow", "document", "knowledge")  # 允许的实体类型

# 构造只读查询参数解析器。
def build_argument_parser() -> argparse.ArgumentParser:
    """创建 registry.ask 参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：配置完成的查询解析器。

    异常：
    - 无。
    """

    # 描述强调查询不会执行任何注册命令。
    parser = argparse.ArgumentParser(description="只读查询命令、工作流、文档或知识；不会执行命中命令。")  # 控制只读查询过滤器的解析器

    # 查询正文是唯一位置参数。
    parser.add_argument("query", help="中英文查询文本")

    # kind 限制在四类统一检索实体中。
    parser.add_argument("--kind", choices=TUPLE_QUERY_KINDS, help="限制命令、工作流、文档或知识类型")

    # category 仅对命令查询开放，避免其他实体产生模糊过滤语义。
    parser.add_argument("--category", help="仅对 command 类型生效的命令分类")

    # limit 解析后由 main 检查 1 到 10 的闭区间。
    parser.add_argument("--limit", type=int, default=5, help="返回 1 到 10 条命中，默认 5")

    # JSON 模式供自动化稳定消费完整结果。
    parser.add_argument(
        "--json",  # 机器可读输出开关
        action="store_true",  # 出现参数时启用 JSON 协议
        dest="bool_json",  # 解析结果中的布尔字段名
        help="将完整结果作为 JSON 输出到 stdout",  # CLI 帮助文本
    )

    # 返回完成配置的查询解析器。
    return parser

# 将用户查询转换为无 FTS5 运算符注入的短语表达式。
def build_fts_expression(str_query: str) -> str:
    """构造 FTS5 安全短语表达式。

    参数：
    - `str_query`：用户提供的原始查询文本。

    返回：
    - `str`：双引号转义后的 FTS5 短语。

    异常：
    - 无。
    """

    # FTS5 双引号通过重复字符转义，其他运算符留在短语内部失去控制语义。
    str_escaped = str_query.replace('"', '""')  # FTS5 短语安全文本

    # 整体加引号，使查询仅表达文本匹配而不是任意 FTS5 语法。
    return f'"{str_escaped}"'

# 规范化文本供 FTS 无命中时执行确定性的空白无关 LIKE 回退。
def normalize_search_text(str_text: str) -> str:
    """移除检索文本中的空白和常见标点。

    参数：
    - `str_text`：查询或索引文本。

    返回：
    - `str`：小写且只保留字母、数字和中日韩字符的文本。

    异常：
    - 无。
    """

    # 保留中英文与数字，去除空白和标点造成的短语断裂。
    str_normalized = re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "", str_text).lower()  # 回退检索规范文本

    # 返回供 Python 侧确定性包含判断使用的文本。
    return str_normalized

# 从新鲜 SQLite 中执行 FTS5 查询，并在必要时使用规范文本回退。
def query_database(
    path_database: Path,
    str_query: str,
    str_kind: str | None,
    str_category: str | None,
    int_limit: int,
) -> list[dict[str, str]]:
    """执行只读注册表查询。

    参数：
    - `path_database`：已通过新鲜度检查的 SQLite 路径。
    - `str_query`：用户查询文本。
    - `str_kind`：可选实体类型过滤器。
    - `str_category`：可选命令分类过滤器。
    - `int_limit`：最大返回数量。

    返回：
    - `list[dict[str, str]]`：按相关度与标识稳定排序的命中。

    异常：
    - `RegistryError`：SQLite 查询失败时抛出。
    """

    # 只读 URI 防止 ask 创建 journal 或改变派生数据库。
    str_uri = path_database.resolve().as_uri() + "?mode=ro"  # SQLite 只读查询 URI

    # WHERE 子句和参数分别构造，所有用户输入只进入绑定参数。
    list_conditions = ["registry_fts MATCH ?"]  # FTS5 基础过滤条件

    # 第一个参数是安全短语表达式。
    list_parameters: list[object] = [build_fts_expression(str_query)]  # FTS5 绑定参数

    # kind 过滤器限制统一实体类型。
    if str_kind:

        # kind 字段是 UNINDEXED 结构列，仍使用参数绑定比较。
        list_conditions.append("items.kind = ?")

        # 保存实体类型过滤值。
        list_parameters.append(str_kind)

    # category 过滤器仅由 main 在 command 语义下放行。
    if str_category:

        # 分类字段来自命令 JSON 权威。
        list_conditions.append("items.category = ?")

        # 保存命令分类过滤值。
        list_parameters.append(str_category)

    # limit 同样使用绑定参数，避免拼接非文本输入。
    list_parameters.append(int_limit)

    # 构造只包含固定 SQL 片段的 FTS5 查询语句。
    str_sql = (  # FTS5 相关度查询
        "SELECT items.id, items.kind, items.category, items.title, items.summary, items.aliases, items.source "
        "FROM registry_fts JOIN items ON items.id = registry_fts.id "
        f"WHERE {' AND '.join(list_conditions)} "
        "ORDER BY bm25(registry_fts), items.id LIMIT ?"
    )

    # 打开数据库并读取 FTS5 结果。
    try:

        # SQLite 连接严格限制在只读 URI。
        with sqlite3.connect(str_uri, uri=True) as connection:

            # 执行参数化查询并一次性读取有限结果。
            list_rows = connection.execute(str_sql, list_parameters).fetchall()  # FTS5 原始命中行

            # FTS5 短语未命中时读取有限候选并执行规范文本包含回退。
            if not list_rows:

                # 绑定两组可空过滤条件，保持回退查询与 FTS 分支使用相同范围。
                tuple_candidate_filters = (  # 主表候选过滤参数
                    str_kind,  # 实体类型过滤器的空值守卫
                    str_kind,  # 与主表 kind 列比较的实参
                    str_category,  # 命令分类过滤器的空值守卫
                    str_category,  # 限定命令所属能力域的分类值
                )

                # 回退仍在 SQLite 主表读取，不绕过已验证派生索引。
                list_candidate_rows = connection.execute(  # 受类型和分类过滤的候选记录
                    "SELECT id, kind, category, title, summary, aliases, source, search_text "
                    "FROM items "
                    "WHERE (? IS NULL OR kind = ?) AND (? IS NULL OR category = ?) "
                    "ORDER BY id",
                    tuple_candidate_filters,  # 与两组可空条件对应的绑定参数
                ).fetchall()

                # 查询规范文本允许关键词之间仅有空白或标点差异。
                str_normalized_query = normalize_search_text(str_query)  # 当前回退查询文本

                # 逐项保留包含完整规范查询的候选，最多返回 limit 条。
                list_rows = [  # 回退命中行
                    tuple_row[:7]  # 统一裁剪为结构化返回字段
                    for tuple_row in list_candidate_rows  # 遍历受过滤候选
                    if str_normalized_query in normalize_search_text(str(tuple_row[7]))  # 规范文本包含判断
                ][:int_limit]

    # SQLite 结构或查询失败属于注册表状态错误。
    except sqlite3.Error as exc:

        # 不把查询引擎错误误报为普通无命中。
        raise RegistryError(f"> ERR: [Python] SQLite 注册表查询失败：{exc}") from exc

    # 将元组结果转换为稳定 JSON 对象。
    list_hits = [  # 结构化查询命中
        {
            "id": str(tuple_row[0]),  # 命中稳定标识
            "kind": str(tuple_row[1]),  # 命中实体类型
            "category": str(tuple_row[2]),  # 命中分类
            "title": str(tuple_row[3]),  # 命中标题
            "summary": str(tuple_row[4]),  # 命中摘要
            "aliases": str(tuple_row[5]),  # 命中别名或关键词
            "source": str(tuple_row[6]),  # 入口、步骤、路径或文档来源
        }
        for tuple_row in list_rows  # 遍历有限查询结果
    ]

    # 返回结构化命中，调用方只展示而不执行 source。
    return list_hits

# 输出查询结果并明确 executed 永远为 false。
def emit_result(dict_result: dict[str, object], bool_json: bool) -> None:
    """输出 registry.ask 结果。

    参数：
    - `dict_result`：查询条件、命中与只读声明。
    - `bool_json`：是否启用机器可读 stdout 协议。

    返回：
    - 无。

    异常：
    - 无。
    """

    # JSON 协议一次性输出完整结果。
    if bool_json:

        # 稳定键序便于测试与上层程序比较。
        print(json.dumps(dict_result, ensure_ascii=False, sort_keys=True))

        # 机器协议不得混入额外人类摘要。
        return

    # 人类模式只打印命中数量和标识，不输出完整结构化记录。
    str_ids = ", ".join(str(dict_hit["id"]) for dict_hit in dict_result["hits"])  # 命中标识摘要

    # 无命中时用固定文本保持消息正文非空。
    str_summary = str_ids if str_ids else "无命中"  # 人类可读查询摘要

    # 输出简短 INFO，不暗示执行任何命令。
    print(f"> INFO: [Python] registry ask：{str_summary}")

# 校验请求、检查数据库并执行只读查询。
def main(list_argv: Sequence[str] | None = None) -> int:
    """执行 registry.ask CLI。

    参数：
    - `list_argv`：可选参数序列；`None` 时读取真实命令行。

    返回：
    - `int`：0 命中，1 无命中，2 请求错误，3 注册表状态错误。

    异常：
    - 无；预期错误转换为稳定退出码。
    """

    # 解析查询文本和过滤条件。
    parser = build_argument_parser()  # registry.ask 参数解析器

    # argparse 负责基础语法与 choice 错误的退出码 2。
    args = parser.parse_args(list_argv)  # 当前查询参数

    # 查询必须包含可见字符，空白文本不进入 FTS5。
    str_query = args.query.strip()  # 去除首尾空白的查询文本

    # 空查询和非法 limit 都是调用请求错误。
    if not str_query or not 1 <= args.limit <= 10:

        # 错误写 stderr，成功 JSON stdout 保持纯净。
        print("> ERR: [Python] query 不能为空且 limit 必须位于 1 到 10", file=sys.stderr)

        # 请求错误使用稳定退出码 2。
        return INT_EXIT_REQUEST

    # category 只允许与 command kind 组合，避免未定义过滤语义。
    if args.category and args.kind != "command":

        # 明确指出调用方需要补充 command kind。
        print("> ERR: [Python] category 仅允许与 --kind command 一起使用", file=sys.stderr)

        # 返回请求错误而不是无命中。
        return INT_EXIT_REQUEST

    # 从入口路径定位当前技能副本根。
    path_skill_root = resolve_skill_root(Path(__file__))  # 当前 registry.ask 所属技能根

    # 加载 JSON 权威并检查 SQLite 新鲜度。
    try:

        # 完整模型检查入口、关系与文档哈希。
        dict_registry = load_registry(path_skill_root)  # 通过完整校验的注册表模型

        # 查询前 fail closed 检查数据库完整性与来源摘要。
        dict_status = inspect_database(path_skill_root, dict_registry)  # SQLite 新鲜度状态

        # manifest 固定数据库路径，ask 不接受任意外部数据库参数。
        path_database = registry_root(path_skill_root) / str(dict_registry["manifest"]["generated_database"])  # 当前派生数据库路径

        # ask 在已验证数据库上解析自然语言，仅公开候选能力说明。
        list_hits = query_database(path_database, str_query, args.kind, args.category, args.limit)  # 未触发入口的候选元数据

    # 注册表状态错误写 stderr 并返回异常协议码。
    except RegistryError as exc:

        # JSON 调用方需要可定位的机器错误对象，同时保持 stdout 单对象协议。
        if args.bool_json:

            # 错误载荷记录状态、诊断和永不执行声明。
            dict_error = {  # registry.ask 机器错误载荷
                "status": "error",  # 当前查询失败状态
                "error": str(exc),  # 注册表状态诊断正文
                "exit_code": exc.int_exit_code,  # 调用方应采用的稳定退出码
                "executed": False,  # 失败路径同样没有执行命中命令
            }

            # 机器协议一次性输出错误对象。
            print(json.dumps(dict_error, ensure_ascii=False, sort_keys=True))

        # 人类模式只输出静态可验证的简短错误提示。
        else:

            # 具体状态可通过 JSON 模式获取，终端不打印动态结构化内容。
            print("> ERR: [Python] 注册表查询失败；请使用 --json 查看状态", file=sys.stderr)

        # 返回缺失、损坏、陈旧或不兼容状态码 3。
        return exc.int_exit_code

    # 组装明确只读的查询结果。
    dict_result = {  # registry.ask 结果载荷
        "query": str_query,  # 规范化查询文本
        "kind": args.kind,  # 可选实体类型过滤器
        "category": args.category,  # 可选命令分类过滤器
        "limit": args.limit,  # 调用方请求的最大命中数
        "hits": list_hits,  # 结构化命中列表
        "hit_count": len(list_hits),  # 实际命中数量
        "executed": False,  # 查询永不执行命中命令
        "source_digest": dict_status["source_digest"],  # 查询所用权威来源摘要
    }

    # 输出机器协议或人类摘要。
    emit_result(dict_result, args.bool_json)

    # 根据命中数量区分成功和普通无命中。
    if list_hits:

        # 至少一条命中返回成功。
        return INT_EXIT_OK

    # 无命中不是注册表损坏，使用稳定退出码 1。
    return INT_EXIT_NO_HIT

# 仅直接执行文件时启动 CLI，导入模块保持无副作用。
if __name__ == "__main__":

    # 将查询业务退出码交给操作系统。
    raise SystemExit(main())
