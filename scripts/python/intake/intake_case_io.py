#!/usr/bin/env python3
"""intake 目录本地文件读写支持。"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

# 这里确保目标目录存在，供 intake 目录内的盘点和转换脚本统一复用。
def ensure_dir(path_dir: Path) -> Path:
    """创建目录并返回目录路径。

    参数：
    - `path_dir`：需要存在的目录路径。

    返回：
    - `Path`：已经确保存在的目录路径。

    异常：
    - 目录创建失败时由底层文件系统异常上抛。
    """

    # 这里递归创建目录，允许上层直接传入多级路径。
    path_dir.mkdir(parents=True, exist_ok=True)  # 已确保存在的目录路径

    # 这里返回目录对象，方便调用方继续拼接子路径。
    return path_dir

# 这里统一写入 UTF-8 文本文件，避免入口脚本重复处理父目录创建。
def write_text_file(path_file: Path, text: str) -> None:
    """写入 UTF-8 文本文件。

    参数：
    - `path_file`：目标文本文件路径。
    - `text`：待写入的文本内容。

    返回：
    - `None`。

    异常：
    - 目录创建或文件写入失败时由底层异常上抛。
    """

    # 这里先确保父目录存在，避免调用方在写文件前手动建目录。
    path_parent_dir = ensure_dir(path_file.parent)  # 文本文件父目录

    # 这里真正写入 UTF-8 文本，保证中文内容可直接读取。
    (path_parent_dir / path_file.name).write_text(text, encoding="utf-8")  # 写入后的目标文本文件

# 这里统一写入 JSON 文件，保证缩进、编码和中文输出格式一致。
def write_json_file(path_file: Path, data: Any) -> None:
    """写入 UTF-8 JSON 文件。

    参数：
    - `path_file`：目标 JSON 文件路径。
    - `data`：可被 `json.dumps` 序列化的数据。

    返回：
    - `None`。

    异常：
    - 目录创建、序列化或文件写入失败时由底层异常上抛。
    """

    # 这里把结构化数据序列化为可读 JSON，便于后续人工审阅。
    str_json_text = json.dumps(data, ensure_ascii=False, indent=2)  # 可读 JSON 文本

    # 这里复用统一文本写入入口，减少重复文件处理逻辑。
    write_text_file(path_file, str_json_text)

# 这里统一读取 JSON 文件，保证 intake 流程对配置格式解释一致。
def read_json_file(path_file: Path) -> Any:
    """读取 UTF-8 JSON 文件。

    参数：
    - `path_file`：待读取的 JSON 文件路径。

    返回：
    - `Any`：反序列化后的 Python 数据结构。

    异常：
    - 文件不存在、编码错误或 JSON 格式错误时由底层异常上抛。
    """

    # 这里读取原始 JSON 文本，供统一反序列化处理。
    str_json_text = path_file.read_text(encoding="utf-8")  # JSON 原始文本

    # 这里返回解析结果，供调用方继续访问字段。
    return json.loads(str_json_text)

# 这里加载案件配置文件，在未建案或配置缺失时返回空字典。
def load_case_config(path_case_dir: Path) -> dict[str, Any]:
    """读取案件配置文件。

    参数：
    - `path_case_dir`：案件根目录。

    返回：
    - `dict[str, Any]`：案件配置；配置不存在时返回空字典。

    异常：
    - 配置存在但 JSON 非法时由底层异常上抛。
    """

    # 这里固定案件配置路径，保持 intake 目录内入口脚本的约定一致。
    path_config = path_case_dir / "case_config.json"  # 案件配置文件路径

    # 这里在配置文件缺失时返回空配置，方便只读工具安全降级。
    if not path_config.exists():

        # 这里对未建案或配置被清理的场景安全降级。
        return {}

    # 这里读取现有案件配置，供后续脚本获取研究根目录和案件名。
    return read_json_file(path_config)

# 这里计算相对路径，便于把绝对研究路径转换为可审阅的材料清单路径。
def relative_to_root(path_file: Path, path_root: Path) -> str:
    """计算路径相对显示值。

    参数：
    - `path_file`：目标文件路径。
    - `path_root`：参考根目录。

    返回：
    - `str`：相对路径；无法相对化时退化为文件名或原始路径文本。

    异常：
    - 无。
    """

    # 这里尝试生成相对路径，避免在正式材料中暴露绝对盘符路径。
    try:

        # 这里先解析目标相对路径，供优先展示简洁材料路径使用。
        path_relative = path_file.resolve().relative_to(path_root.resolve())  # 相对根目录路径

        # 这里优先返回相对路径文本，减少正式材料中的本地路径暴露。
        return str(path_relative)

    # 这里捕获路径无法相对化的场景，转入兜底显示逻辑。
    except (ValueError, OSError):

        # 这里保留兜底分支继续执行，不把相对化失败直接升级为流程错误。
        path_relative = None  # 相对路径失败占位

    # 这里在相对化失败时优先返回文件名，保持输出结果尽量简洁。
    if path_file.is_file():

        # 这里优先返回文件名，避免展示过长的绝对文件路径。
        return path_file.name

    # 这里最后退化为原始路径文本，至少保证信息不丢失。
    return str(path_file)
