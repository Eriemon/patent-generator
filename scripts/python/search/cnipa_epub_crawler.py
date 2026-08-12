#!/usr/bin/env python3
"""保存本地或在线 CNIPA 结果页 HTML 快照。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、文件复制、时间戳、序列化、路径和网络读取能力。
import argparse
import datetime
import json
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any

# 构造命令行参数解析器，统一声明本地 HTML、远端 URL 和输出目录参数。
def parse_arguments() -> argparse.Namespace:
    """解析命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含输入源和输出目录的参数对象。

    异常：
    - 参数缺失或组合非法时由 `argparse` 自动结束进程。
    """

    # 初始化 HTML 快照入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description="Save a CNIPA result-page HTML snapshot from a local file or URL.")  # HTML 快照入口命令行解析器

    # 注册本地 HTML 输入参数，供本地夹具或手工抓取结果直接入库。
    obj_parser.add_argument(
        "--input-html",
        help="Local HTML file to stage into the governed output directory.",
    )  # 本地 HTML 输入参数

    # 注册远端 URL 参数，供本地直接抓取 CNIPA 结果页使用。
    obj_parser.add_argument("--url", help="Remote URL to fetch when local HTML is not provided.")  # 远端 URL 输入参数

    # 注册输出目录参数，确保快照和 manifest 都落在受管目录中。
    obj_parser.add_argument("--output-dir", required=True, help="Output directory for the saved HTML snapshot.")  # 输出目录参数

    # 返回解析后的参数对象，供主流程定位输入源和输出位置。
    return obj_parser.parse_args()

# 返回紧凑时间戳，供 HTML 快照文件稳定命名使用。
def now_timestamp() -> str:
    """返回紧凑时间戳。

    参数：
    - 无。

    返回：
    - `str`：`YYYYMMDDHHMMSS` 形式的时间戳文本。

    异常：
    - 无。
    """

    # 读取当前本地时间对象，供快照文件名复用。
    dt_now = datetime.datetime.now()  # 快照命名时间对象

    # 输出没有空格与冒号的紧凑时间戳文本。
    return dt_now.strftime("%Y%m%d%H%M%S")

# 确保输出目录存在并返回目录对象，供快照和 manifest 落盘使用。
def ensure_dir(path_dir: Path) -> Path:
    """创建目录并返回目录对象。

    参数：
    - `path_dir`：需要存在的目录路径。

    返回：
    - `Path`：已经确保存在的目录路径对象。

    异常：
    - 目录创建失败时由底层文件系统异常上抛。
    """

    # 递归创建输出目录，允许调用方直接传入多级路径。
    path_dir.mkdir(parents=True, exist_ok=True)  # 已创建或已存在的目录路径

    # 返回输出目录对象，方便主流程继续拼接文件路径。
    return path_dir

# 统一写入可读 JSON 文件，便于记录快照来源与输出文件位置。
def write_json_file(path_file: Path, obj_data: Any) -> None:
    """写入 UTF-8 JSON 文件。

    参数：
    - `path_file`：目标 JSON 文件路径。
    - `obj_data`：可被 `json.dumps` 序列化的数据对象。

    返回：
    - `None`。

    异常：
    - 目录创建、序列化或文件写入失败时由底层异常上抛。
    """

    # 先确保 manifest 所在目录存在，避免写文件前还要手工建目录。
    path_parent_dir = ensure_dir(path_file.parent)  # manifest 文件父目录

    # 先把 manifest 载荷序列化成可读 JSON 文本。
    str_json_text = json.dumps(obj_data, ensure_ascii=False, indent=2)  # 写入快照 manifest 的可读 JSON 文本

    # 把 manifest JSON 文本写入目标文件，保留中文直出和稳定缩进。
    (path_parent_dir / path_file.name).write_text(str_json_text, encoding="utf-8")  # 已写入的 manifest 文件

# 抓取远端 HTML 文本，供在线 CNIPA 结果页快照保存逻辑复用。
def fetch_html(str_url: str) -> str:
    """抓取远端 HTML 文本。

    参数：
    - `str_url`：待抓取的远端结果页 URL。

    返回：
    - `str`：按 UTF-8 解码后的 HTML 文本。

    异常：
    - 网络访问失败时由底层异常上抛。
    """

    # 打开远端 URL 并读取响应体，供后续保存到本地 HTML 快照文件。
    with urllib.request.urlopen(str_url, timeout=30) as obj_response:

        # 读取响应字节并按 UTF-8 宽松解码，兼容 CNIPA 页面中的非严格编码片段。
        return obj_response.read().decode("utf-8", errors="ignore")

# 执行 HTML 快照保存入口，并把最终快照路径写到标准输出末尾。
def main() -> int:
    """执行 HTML 快照保存入口。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 输入缺失、路径不存在或网络抓取失败时由相关异常上抛。
    """

    # 解析命令行参数，定位当前输入源和受管输出目录。
    namespace_arguments = parse_arguments()  # HTML 快照入口参数对象

    # 解析并确保输出目录存在，后续快照与 manifest 都会写到这里。
    path_output_dir = ensure_dir(Path(namespace_arguments.output_dir).resolve())  # 受管 HTML 快照输出目录

    # 基于当前时间戳生成快照文件路径，避免重复执行时覆盖旧快照。
    path_output_html = path_output_dir / f"cnipa_results_{now_timestamp()}.html"  # HTML 快照文件路径

    # 在给定本地 HTML 文件时优先走本地复制逻辑，保留原始快照内容。
    if namespace_arguments.input_html:

        # 解析本地 HTML 输入绝对路径，避免相对路径受调用目录影响。
        path_input_html = Path(namespace_arguments.input_html).resolve()  # 本地 HTML 输入文件路径

        # 在本地 HTML 文件不存在时立即报错，避免写出空壳快照文件。
        if not path_input_html.exists():

            # 抛出明确错误，提醒调用方检查本地 HTML 文件路径。
            raise FileNotFoundError("> ERR: [Python] 指定的本地 HTML 文件不存在。")

        # 把本地 HTML 文件复制到受管输出目录，形成正式快照副本。
        shutil.copyfile(path_input_html, path_output_html)

        # 记录本次快照来源路径，供 manifest 后续回溯输入来源。
        str_source = str(path_input_html)  # 本地 HTML 快照来源路径

    # 在未提供本地 HTML 但给定 URL 时走在线抓取逻辑。
    elif namespace_arguments.url:

        # 读取远端 HTML 文本，供受管快照文件落盘使用。
        str_html_text = fetch_html(namespace_arguments.url)  # 远端抓取到的 HTML 文本

        # 把抓取到的 HTML 文本写入受管快照文件，保留本地可追溯副本。
        path_output_html.write_text(str_html_text, encoding="utf-8")

        # 把在线检索来源 URL 记录到 manifest，方便后续追溯这份快照的抓取入口。
        str_source = namespace_arguments.url  # 在线 HTML 快照来源 URL

    # 在本地 HTML 和 URL 都未提供时立即报错，避免不完整调用静默通过。
    else:

        # 抛出明确错误，提醒调用方至少提供本地 HTML 或 URL 之一。
        raise ValueError("> ERR: [Python] 请提供 --input-html 或 --url。")

    # 组装快照 manifest 载荷，记录来源和受管 HTML 快照文件位置。
    dict_manifest = {  # HTML 快照 manifest 字典
        "source": str_source,  # 快照来源路径或 URL
        "html_file": str(path_output_html.resolve()),  # 受管 HTML 快照绝对路径
    }

    # 把 manifest 写入输出目录，便于后续检索与解析入口直接复用。
    write_json_file(path_output_dir / "cnipa_snapshot_manifest.json", dict_manifest)

    # 把最终 HTML 快照路径作为机器可读输出写回上游流程。
    sys.stdout.write(str(path_output_html.resolve()) + "\n")

    # 返回成功状态码，表示快照和 manifest 都已完成落盘。
    return 0

# 保留标准命令行入口，方便直接执行 HTML 快照保存脚本。
if __name__ == "__main__":

    # 使用 main 的返回值作为进程退出码，保持 CLI 行为一致。
    raise SystemExit(main())
