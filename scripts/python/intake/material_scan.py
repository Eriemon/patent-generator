#!/usr/bin/env python3
"""研究材料目录扫描支持。"""
from __future__ import annotations
import os
from pathlib import Path

# 这里集中列出可继续做正文抽取的材料类型，避免盘点阶段误跳过常见研发输入。
TEXT_EXTENSIONS = frozenset(  # 允许继续做正文抽取的后缀集合
    """
    .md
    .markdown
    .txt
    .rst
    .py
    .ipynb
    .json
    .yaml
    .yml
    .toml
    .csv
    .tsv
    .html
    .htm
    .docx
    .pptx
    .pdf
    """.split()
)

# 这里集中列出明显不应走正文抽取的二进制类型，减少后续乱码和误分类。
BINARY_EXTENSIONS = frozenset(  # 应当跳过正文抽取的二进制后缀集合
    """
    .png
    .jpg
    .jpeg
    .gif
    .webp
    .zip
    .tar
    .gz
    .7z
    .mp4
    .mov
    .avi
    .bin
    .onnx
    .pt
    .pth
    .ckpt
    .xlsx
    """.split()
)

# 这里集中列出扫描时要主动绕开的目录，避免缓存、依赖和运行输出污染盘点结果。
SKIP_DIRECTORY_NAMES = frozenset(  # 扫描阶段主动绕开的目录名称集合
    """
    .git
    .hg
    .svn
    node_modules
    .venv
    venv
    env
    __pycache__
    .mypy_cache
    .pytest_cache
    dist
    build
    .idea
    .vscode
    .next
    target
    runs
    """.split()
)

# 这里判断目录是否允许继续深入扫描，避免主循环里塞入过长条件表达式。
def should_keep_directory(str_dir_name: str) -> bool:
    """判断目录是否允许继续扫描。

    参数：
    - `str_dir_name`：待判断目录名。

    返回：
    - `bool`：允许继续扫描时返回 `True`。

    异常：
    - 无。
    """

    # 这里先排除治理规则明确要求跳过的目录。
    if str_dir_name in SKIP_DIRECTORY_NAMES:

        # 这里对命中黑名单的目录立即返回禁止扫描。
        return False

    # 这里再排除其他隐藏目录，避免把本地工具状态写进盘点。
    return not str_dir_name.startswith(".")

# 这里递归枚举研究材料文件，并排除依赖、缓存与运行输出目录。
def iter_files(path_root: Path, int_max_files: int = 2000) -> list[Path]:
    """返回研究根目录中的文件列表。

    参数：
    - `path_root`：研究材料根目录。
    - `int_max_files`：最多收集的文件数量。

    返回：
    - `list[Path]`：按遍历顺序收集的文件路径列表。

    异常：
    - 无。
    """

    # 这里初始化结果列表，按遍历顺序保存材料路径。
    list_paths: list[Path] = []  # 按遍历顺序收集的材料路径列表

    # 这里记录已经纳入盘点的文件数量，避免超大目录拖慢流程。
    int_file_count = 0  # 当前已经纳入盘点的文件数量

    # 这里统一解析绝对研究根目录，减少后续路径判断歧义。
    path_root = path_root.resolve()  # 绝对研究根目录

    # 这里从研究根目录向下遍历，只保留允许进入的子目录。
    for str_dir_path, list_dir_names, list_file_names in os.walk(path_root):

        # 这里就地裁剪待进入目录列表，避免进入缓存、依赖和隐藏目录。
        list_dir_names[:] = [str_dir_name for str_dir_name in list_dir_names if should_keep_directory(str_dir_name)]  # 允许继续进入的子目录名称列表

        # 这里逐个处理当前目录中的文件名。
        for str_file_name in list_file_names:

            # 这里跳过 Office 临时锁文件，避免把无效占位文件纳入盘点。
            if str_file_name.startswith("~$"):

                # 这里直接跳过临时锁文件，不让它们干扰盘点结果。
                continue

            # 这里在保留文件前先累加计数，便于及时停止超大目录扫描。
            int_file_count += 1  # 当前累计扫描文件数加一

            # 这里在超出文件上限时立即返回当前结果，保证流程时长可控。
            if int_file_count > int_max_files:

                # 这里返回已收集路径，让上层基于当前材料继续执行。
                return list_paths

            # 这里构造当前文件完整路径，供后续分类和正文抽取使用。
            path_file = Path(str_dir_path) / str_file_name  # 当前材料的完整路径

            # 这里按遍历顺序保存材料路径，保持盘点输出稳定。
            list_paths.append(path_file)

    # 这里返回扫描结果，供盘点与事实抽取继续处理。
    return list_paths

# 这里判断文件是否适合走文本抽取路径。
def is_probably_text(path_file: Path) -> bool:
    """判断文件是否适合文本抽取。

    参数：
    - `path_file`：待判断文件路径。

    返回：
    - `bool`：适合文本抽取时返回 `True`。

    异常：
    - 无。
    """

    # 这里统一获取小写后缀，供白名单和黑名单双重判断。
    str_suffix = path_file.suffix.lower()  # 小写文件后缀

    # 这里只有位于文本白名单且不在二进制黑名单中的文件才继续处理。
    return str_suffix in TEXT_EXTENSIONS and str_suffix not in BINARY_EXTENSIONS
