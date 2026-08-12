#!/usr/bin/env python3
"""案件目录、基础配置和轻量文件读写支持。"""
from __future__ import annotations
import datetime
import json
import re
from pathlib import Path
from typing import Any

# 这里固定案件内部的阶段目录顺序，保证每次建案都得到一致的落盘结构。
CASE_STAGE_DIRECTORIES = (
    "00_research",  # 保存原始研究材料和转换结果
    "01_inventory",  # 保存材料盘点与清单结果
    "01_inventory/converted",  # 保存 Office 材料转换后的 Markdown
    "02_facts",  # 保存事实抽取、专利点和查新计划
    "03_drafts",  # 保存预览、正文草稿和权利要求草稿
    "04_reviews",  # 保存自检报告和人工复核材料
    "05_figures",  # 保存附图和附图清单
    "05_exports",  # 保存导出的 DOCX 等交付件
    "99_logs",  # 保存流程日志和补充说明
)

# 这里收敛文件系统不允许的字符，避免案件名在 Windows 路径中失效。
ILLEGAL_TITLE_CHARACTERS = set('\\/:*?"<>|\n\r\t')  # 文件系统非法字符集合

# 这里返回精确到秒的 ISO 时间，供案件配置和报告文件统一使用。
def iso_now() -> str:
    """返回 ISO 时间字符串。

    参数：
    - 无。

    返回：
    - `str`：精确到秒的本地时间字符串。

    异常：
    - 无。
    """

    # 这里生成当前时刻，供后续配置文件和报告文件复用。
    dt_now = datetime.datetime.now()  # 当前本地时间对象

    # 这里返回统一格式的时间文本，避免不同脚本各自拼接时间格式。
    return dt_now.isoformat(timespec="seconds")

# 这里返回紧凑时间戳，供输出文件名和导出件命名使用。
def now_timestamp() -> str:
    """返回紧凑时间戳。

    参数：
    - 无。

    返回：
    - `str`：`YYYYMMDDHHMMSS` 形式的时间戳。

    异常：
    - 无。
    """

    # 这里生成当前时刻，供导出文件名和草稿快照命名复用。
    dt_now = datetime.datetime.now()  # 导出和快照命名时间对象

    # 这里输出稳定的紧凑时间格式，避免文件名中出现空格和冒号。
    return dt_now.strftime("%Y%m%d%H%M%S")

# 这里将用户输入名称规整为稳定路径名，避免英文被误删或中文被过度清洗。
def sanitize_name(value: str, fallback: str = "patent_case", max_len: int = 80) -> str:
    """清洗案件名称并返回可用路径片段。

    参数：
    - `value`：原始案件名称或发明名称。
    - `fallback`：名称清洗后为空时使用的兜底值。
    - `max_len`：输出路径片段允许的最大长度。

    返回：
    - `str`：适合作为目录名和文件名前缀的稳定字符串。

    异常：
    - 无。
    """

    # 这里先去掉首尾空白，避免名称前后多余空格影响目录名。
    cleaned_value = (value or "").strip()  # 去首尾空白后的名称

    # 这里删除文件系统非法字符，保留可读的中英文主体。
    cleaned_value = "".join(character for character in cleaned_value if character not in ILLEGAL_TITLE_CHARACTERS)  # 去除非法字符后的名称

    # 这里把内部空白压缩成下划线，兼顾英文可读性与路径稳定性。
    cleaned_value = re.sub(r"\s+", "_", cleaned_value)  # 统一空白为下划线

    # 这里去掉路径名两端容易造成歧义的装饰字符。
    cleaned_value = cleaned_value.strip("._- ")  # 删除首尾装饰字符

    # 这里在用户输入为空时回退到默认案件名，避免产生空目录名。
    if not cleaned_value:

        # 这里在标题完全不可用时落回默认案件名，保证后续目录仍可创建。
        cleaned_value = fallback  # 空标题兜底名称

    # 这里限制长度，避免过长路径影响 Windows 本地操作。
    if len(cleaned_value) > max_len:

        # 这里把超长标题裁剪到受控长度，避免后续路径过深触发系统限制。
        cleaned_value = cleaned_value[:max_len].rstrip("-_ ")  # 裁剪后的标题片段

    # 这里再次兜底，防止截断后名称为空。
    return cleaned_value or fallback

# 这里确保目标目录存在，供所有写文件流程共享相同行为。
def ensure_dir(path: Path) -> Path:
    """创建目录并返回目录路径。

    参数：
    - `path`：需要存在的目录路径。

    返回：
    - `Path`：已经确保存在的目录路径。

    异常：
    - 目录创建失败时由底层文件系统异常上抛。
    """

    # 这里递归创建目录，允许上层直接传入多级路径。
    path.mkdir(parents=True, exist_ok=True)  # 创建目标目录

    # 这里返回目录对象，方便调用方继续拼接子路径。
    return path

# 这里统一写入 UTF-8 文本文件，避免每个脚本重复处理编码和父目录创建。
def write_text_file(path: Path, text: str) -> None:
    """写入 UTF-8 文本文件。

    参数：
    - `path`：目标文本文件路径。
    - `text`：待写入的文本内容。

    返回：
    - `None`。

    异常：
    - 目录创建或文件写入失败时由底层异常上抛。
    """

    # 这里先确保父目录存在，避免调用方在写文件前手动建目录。
    path_parent_dir = ensure_dir(path.parent)  # 文本文件父目录

    # 这里真正写入 UTF-8 文本，保证中文内容可直接读取。
    (path_parent_dir / path.name).write_text(text, encoding="utf-8")  # 写入目标文件

# 这里统一写入 JSON 文件，保证缩进、编码和中文输出格式一致。
def write_json_file(path: Path, data: Any) -> None:
    """写入 UTF-8 JSON 文件。

    参数：
    - `path`：目标 JSON 文件路径。
    - `data`：可被 `json.dumps` 序列化的数据。

    返回：
    - `None`。

    异常：
    - 目录创建、序列化或文件写入失败时由底层异常上抛。
    """

    # 这里把结构化数据序列化为可读 JSON，便于后续人工审阅。
    json_text = json.dumps(data, ensure_ascii=False, indent=2)  # 可读 JSON 文本

    # 这里复用统一文本写入入口，减少重复文件处理逻辑。
    write_text_file(path, json_text)  # 写入 JSON 文件

# 这里统一读取 JSON 文件，保证整个技能对配置和中间件格式解释一致。
def read_json_file(path: Path) -> Any:
    """读取 UTF-8 JSON 文件。

    参数：
    - `path`：待读取的 JSON 文件路径。

    返回：
    - `Any`：反序列化后的 Python 数据结构。

    异常：
    - 文件不存在、编码错误或 JSON 格式错误时由底层异常上抛。
    """

    # 这里读取原始 JSON 文本，供统一反序列化处理。
    json_text = path.read_text(encoding="utf-8")  # JSON 原始文本

    # 这里返回解析结果，供调用方继续访问字段。
    return json.loads(json_text)

# 这里加载案件配置文件，在未建案或配置缺失时返回空字典。
def load_case_config(case_dir: Path) -> dict[str, Any]:
    """读取案件配置文件。

    参数：
    - `case_dir`：案件根目录。

    返回：
    - `dict[str, Any]`：案件配置；配置不存在时返回空字典。

    异常：
    - 配置存在但 JSON 非法时由底层异常上抛。
    """

    # 这里固定案件配置路径，保持各脚本对入口配置的一致约定。
    config_path = case_dir / "case_config.json"  # 案件配置文件路径

    # 这里在配置文件缺失时返回空配置，方便只读工具安全降级。
    if not config_path.exists():

        # 这里对未建案或配置被清理的场景安全降级，避免只读工具直接崩溃。
        return {}  # 缺少配置时返回空配置

    # 这里读取现有案件配置，供后续脚本获取研究根目录和案件名。
    return read_json_file(config_path)

# 这里计算相对路径，便于把绝对研究路径转换为可审阅的材料清单路径。
def relative_to_root(path: Path, root: Path) -> str:
    """计算路径相对显示值。

    参数：
    - `path`：目标文件路径。
    - `root`：参考根目录。

    返回：
    - `str`：相对路径；无法相对化时退化为文件名或原始路径文本。

    异常：
    - 无。
    """

    # 这里尝试生成相对路径，避免在正式材料中暴露绝对盘符路径。
    try:

        # 这里先解析目标相对路径，供优先展示简洁材料路径使用。
        path_relative = path.resolve().relative_to(root.resolve())  # 相对根目录路径

        # 这里优先返回相对路径文本，减少正式材料中的本地路径暴露。
        return str(path_relative)

    # 这里捕获路径无法相对化的场景，转入兜底显示逻辑。
    except (ValueError, OSError):

        # 这里保留兜底分支继续执行，不把相对化失败直接升级为流程错误。
        path_relative = None  # 相对路径失败占位

    # 这里在相对化失败时优先返回文件名，保持输出结果尽量简洁。
    if path.is_file():

        # 这里优先返回文件名，避免展示过长的绝对文件路径。
        return path.name  # 文件兜底显示名称

    # 这里最后退化为原始路径文本，至少保证信息不丢失。
    return str(path)

# 这里定位案件目录下最新的 Markdown 成果文件，供导出和校验脚本使用。
def find_latest_markdown(root: Path) -> Path | None:
    """查找最近修改的 Markdown 文件。

    参数：
    - `root`：待搜索的目录。

    返回：
    - `Path | None`：最近修改的 Markdown 文件；没有结果时返回 `None`。

    异常：
    - 无。
    """

    # 这里枚举所有 Markdown 文件，供后续按修改时间排序。
    list_markdown_files = list(root.rglob("*.md"))  # 目录中的 Markdown 文件

    # 这里排除明显属于中间清单和报告的 Markdown，优先返回正文类产物。
    set_ignored_markdown_names = {  # 需要排除的中间 Markdown 名称
        "research_inventory.md",  # 材料盘点报告
        "research_facts.md",  # 事实抽取报告
        "validation_report.md",  # 自检报告
        "figures_manifest.md",  # 附图清单
    }

    # 这里过滤掉中间报告文件，优先保留真正可导出和可审阅的正文草稿。
    list_markdown_files = [path for path in list_markdown_files if path.name not in set_ignored_markdown_names]  # 排除中间文件后的 Markdown 文件

    # 这里在没有结果时返回空值，交由调用方决定如何提示。
    if not list_markdown_files:

        # 这里在目录中没有正文类 Markdown 时返回空值，让调用方自己决定下一步。
        return None

    # 这里按最近修改时间倒序排列，优先选择最新正文草稿。
    list_markdown_files.sort(key=lambda path: path.stat().st_mtime, reverse=True)  # 按时间倒序排序

    # 这里返回最新文件，供导出和自检流程继续处理。
    return list_markdown_files[0]
