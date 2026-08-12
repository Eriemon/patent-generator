"""校验或原子重建 SQLite 注册表。

stdout_protocol: json
当调用方使用 `--json` 时，stdout 只包含单个完整 JSON 对象。
"""

# 启用延迟注解，保持 CLI 类型标注在 Python 3.10 及以上版本稳定可用。
from __future__ import annotations

# 标准库
import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

# 同目录公共能力
from registry_common import (
    INT_EXIT_OK,
    RegistryError,
    inspect_database,
    load_registry,
    resolve_skill_root,
    write_database,
)

# 构造只暴露检查、显式写入和输出协议选项的参数解析器。
def build_argument_parser() -> argparse.ArgumentParser:
    """创建 registry.build 参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：配置完成的命令行解析器。

    异常：
    - 无。
    """

    # 描述明确默认只读，避免调用方误以为裸命令会刷新数据库。
    parser = argparse.ArgumentParser(description="默认只读检查注册表；仅 --write 原子重建 SQLite。")  # 控制检查与原子重建授权的解析器

    # 显式写入开关是唯一数据库变更授权。
    parser.add_argument("--write", action="store_true", help="校验 JSON 后原子重建 SQLite 派生索引")

    # JSON 模式供测试、发布门禁和其他程序稳定消费。
    parser.add_argument(
        "--json",  # 机器可读输出开关
        action="store_true",  # 出现参数时启用 JSON 协议
        dest="bool_json",  # 解析结果中的布尔字段名
        help="将完整结果作为 JSON 输出到 stdout",  # CLI 帮助文本
    )

    # 返回完成配置的解析器。
    return parser

# 按人类摘要或机器 JSON 协议输出成功结果。
def emit_result(dict_result: dict[str, object], bool_json: bool) -> None:
    """输出 registry.build 结果。

    参数：
    - `dict_result`：构建或检查结果载荷。
    - `bool_json`：是否启用机器可读 stdout 协议。

    返回：
    - 无。

    异常：
    - 无。
    """

    # 机器协议一次性输出完整 JSON，不混入人类日志前缀。
    if bool_json:

        # 排序键保持 CI 和发布证据稳定。
        print(json.dumps(dict_result, ensure_ascii=False, sort_keys=True))

        # JSON 分支已完成，不再输出第二行摘要。
        return

    # 提取状态字段，防止人类摘要直接格式化完整结构化对象。
    str_status = str(dict_result["status"])  # 注册表当前状态

    # 路径只用于简短定位，不输出注册表正文。
    str_database = str(dict_result["database"])  # 派生数据库路径

    # 记录数是允许输出的简短汇总计数。
    int_record_count = int(dict_result["record_count"])  # 注册表记录数量

    # 人类模式只报告状态、路径和记录数量。
    print(f"> INFO: [Python] registry {str_status}：{str_database}，记录 {int_record_count} 条")

# 解析参数并执行只读检查或显式原子重建。
def main(list_argv: Sequence[str] | None = None) -> int:
    """执行 registry.build CLI。

    参数：
    - `list_argv`：可选参数序列；`None` 时读取真实命令行。

    返回：
    - `int`：0 表示成功，3 表示注册表缺失、损坏、陈旧或不兼容。

    异常：
    - 无；预期注册表错误被转换为稳定退出码。
    """

    # 解析只读检查、显式写入与输出模式。
    parser = build_argument_parser()  # registry.build 参数解析器

    # argparse 负责请求语法错误的退出码 2。
    args = parser.parse_args(list_argv)  # 当前命令行参数

    # 从本入口位置定位源码、dist 或安装副本技能根。
    path_skill_root = resolve_skill_root(Path(__file__))  # 当前 registry.build 所属技能根

    # 加载完整 JSON 权威并执行入口、关系和文档哈希检查。
    try:

        # 所有构建和检查都先使用同一份严格模型。
        dict_registry = load_registry(path_skill_root)  # 通过完整校验的注册表模型

        # 只有显式 write 才进入数据库原子替换路径。
        if args.write:

            # 重建结果包含来源摘要与真实记录数。
            dict_result = write_database(path_skill_root, dict_registry)  # SQLite 原子构建结果

        # 默认路径只读检查既有数据库。
        else:

            # 缺失或陈旧数据库在此以退出码 3 fail closed。
            dict_result = inspect_database(path_skill_root, dict_registry)  # SQLite 新鲜度检查结果

    # 预期状态错误转为固定前缀和退出码，不输出 Python traceback。
    except RegistryError as exc:

        # JSON 调用方需要可定位的机器错误对象，同时保持 stdout 单对象协议。
        if args.bool_json:

            # 错误载荷只包含稳定状态和诊断正文，不暴露 traceback。
            dict_error = {  # registry.build 机器错误载荷
                "status": "error",  # 当前操作失败状态
                "error": str(exc),  # 注册表状态诊断正文
                "exit_code": exc.int_exit_code,  # 调用方应采用的稳定退出码
                "written": False,  # 失败路径未完成数据库替换
            }

            # 机器协议一次性输出错误对象。
            print(json.dumps(dict_error, ensure_ascii=False, sort_keys=True))

        # 人类模式只输出静态可验证的简短错误提示。
        else:

            # 具体状态可通过 JSON 模式获取，终端不打印动态结构化内容。
            print("> ERR: [Python] 注册表检查或构建失败；请使用 --json 查看状态", file=sys.stderr)

        # 返回异常携带的稳定注册表退出码。
        return exc.int_exit_code

    # 输出完整机器协议或简短人类摘要。
    emit_result(dict_result, args.bool_json)

    # 成功构建或检查统一返回 0。
    return INT_EXIT_OK

# 仅直接执行文件时启动 CLI，导入模块不会产生 IO 副作用。
if __name__ == "__main__":

    # 将业务退出码交给操作系统和上层自动化。
    raise SystemExit(main())
