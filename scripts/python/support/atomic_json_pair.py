"""以无覆盖事务一次发布两个 JSON 工件。"""

# 延迟解析类型注解，保持技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库负责 JSON 序列化、刷盘、硬链接发布和临时文件清理。
import json
import os
import tempfile
from pathlib import Path
from typing import Any

# 生成发布到磁盘的确定性 JSON 原始字节。
def serialize_json_bytes(dict_payload: dict[str, Any]) -> bytes:
    """返回 UTF-8、固定缩进和末尾换行的 JSON 字节。

    参数：
    - `dict_payload`：需要序列化的 JSON 对象。

    返回：
    - `bytes`：最终落盘使用的确定性原始字节。

    异常：
    - 不可序列化值由 `json.dumps` 上抛。
    """

    # receipt 必须计算最终落盘字节，而不是另一份近似序列化文本。
    return (
        json.dumps(dict_payload, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

# 把完整 JSON 写入与最终目标同目录的临时文件。
def stage_json(path_output: Path, dict_payload: dict[str, Any]) -> Path:
    """为事务发布准备完整 JSON 临时文件。

    参数：
    - `path_output`：最终输出路径。
    - `dict_payload`：待序列化 JSON 对象。

    返回：
    - `Path`：已经刷盘的同目录临时文件。

    异常：
    - 文件系统或序列化错误由底层实现上抛。
    """

    # 输出父目录必须在临时文件创建前存在。
    path_output.parent.mkdir(parents=True, exist_ok=True)

    # staging 与 receipt 摘要共享同一序列化边界。
    bytes_payload = serialize_json_bytes(dict_payload)  # 当前工件最终原始字节

    # 临时文件与目标同卷，保证后续硬链接具有原子创建语义。
    int_descriptor, str_temp_path = tempfile.mkstemp(  # 当前同目录临时文件描述符和路径
        prefix=f".{path_output.name}.",  # 临时文件沿用目标名称
        suffix=".tmp",  # 未发布工件固定后缀
        dir=path_output.parent,  # 与最终文件保持同一目录
        text=True,  # 使用文本描述符写入 UTF-8
    )

    # Path 对象供事务清理逻辑复用。
    path_temp = Path(str_temp_path)  # 当前已创建临时路径

    # 接管底层描述符并同步完整内容。
    with os.fdopen(int_descriptor, "wb") as obj_file:

        # 一次写入完整文本，避免临时文件内部出现阶段性结构。
        obj_file.write(bytes_payload)

        # 刷新解释器缓冲区。
        obj_file.flush()

        # 要求操作系统同步当前文件内容。
        os.fsync(obj_file.fileno())

    # 返回等待事务提交的临时文件。
    return path_temp

# 通过同一事务边界发布任意数量的互相绑定工件。
def write_json_batch_atomic(
    list_artifacts: list[tuple[Path, dict[str, Any]]],
) -> None:
    """以无覆盖语义事务式发布一批 JSON 工件。

    staging 和发布均处于同一清理边界。发布失败时，只删除仍与本事务
    staging 文件指向同一文件身份的目录项，避免删除竞争者替换内容。

    参数：
    - `list_artifacts`：最终路径与 JSON 对象组成的有序批次。

    返回：
    - `None`：全部目录项均由本事务成功创建。

    异常：
    - `ValueError`：批次不足两项或目标路径重复时抛出。
    - `FileExistsError`：任一目标已经存在时抛出。
    - `OSError`：staging、link、刷盘或安全回滚失败时上抛。
    """

    # 单工件不应借用批次语义掩盖调用方边界错误。
    if len(list_artifacts) < 2:

        # 要求调用方显式选择单工件发布器。
        raise ValueError("> ERR: [Python] JSON 批次至少需要两份工件。")

    # 规范路径后检查别名，避免同一目标被事务内重复发布。
    list_paths = [  # 当前批次规范目标路径
        path_output.resolve()  # 消除相对路径差异
        for path_output, _ in list_artifacts  # 遍历全部待发布工件
    ]

    # 目标别名会破坏“全部创建或零创建”的事务含义。
    if len(set(list_paths)) != len(list_paths):

        # 在 staging 前阻断，保证没有临时文件副作用。
        raise ValueError("> ERR: [Python] JSON 批次输出路径必须不同。")

    # 预存目标属于其他调用方，当前事务绝不覆盖。
    if any(path_output.exists() for path_output in list_paths):

        # 失败发生在 staging 前，既有目录项保持原样。
        raise FileExistsError("> ERR: [Python] JSON 批次事务目标已存在。")

    # 记录成功 staging 的目录项，第二次 staging 失败时也能完整清理。
    list_staged: list[tuple[Path, Path]] = []  # 最终路径与本事务临时路径

    # 仅已成功 link 的目录项可能需要所有权安全回滚。
    list_published: list[tuple[Path, Path]] = []  # 已发布目标及其同 inode 临时路径

    # staging、发布和清理必须共享一个 finally 边界。
    try:

        # 所有工件完整刷盘后才允许任何最终路径可见。
        for path_output, dict_payload in list_artifacts:

            # 保存实际 staging 路径，不能重新推导随机临时名。
            path_temp = stage_json(path_output, dict_payload)  # 当前完整临时工件

            # 登记后续统一清理和文件身份验证所需关系。
            list_staged.append((path_output, path_temp))

        # 硬链接以无覆盖语义逐项创建最终目录项。
        for path_output, path_temp in list_staged:

            # link 成功前不登记发布状态，避免回滚未创建目标。
            os.link(path_temp, path_output)

            # 目标和临时路径当前指向同一文件身份。
            list_published.append((path_output, path_temp))

    # 任一阶段失败时撤销仍属于本事务的可见目录项。
    except BaseException:

        # 逆序回滚与发布次序相反，保持批次事务常规语义。
        for path_output, path_temp in reversed(list_published):

            # 竞争者可能已经替换目标，所有权检查本身也必须失败关闭。
            try:

                # 只有目标仍与 staging 同一文件身份时才属于本事务。
                bool_owned = path_output.exists() and os.path.samefile(  # 当前目标是否仍由本事务拥有
                    path_output,  # 当前最终目录项
                    path_temp,  # 当前事务保留的 staging 身份
                )

            # 路径竞争或平台查询失败时禁止删除不明目标。
            except OSError:

                # 无法证明所有权等价于无删除权限。
                bool_owned = False  # 当前目标所有权未获证明

            # 竞争者替换的目录项必须保持可见。
            if bool_owned:

                # 当前目标仍是本事务硬链接，安全恢复为零输出。
                path_output.unlink()

        # 保留原始失败类型和调用栈供 CLI 转换。
        raise

    # 成功和失败都不得遗留 staging 目录项。
    finally:

        # 只遍历实际创建成功的临时文件。
        for _, path_temp in list_staged:

            # link 成功后删除临时名不会影响最终硬链接内容。
            if path_temp.exists():

                # staging 永远不是正式交付工件。
                path_temp.unlink()

# 兼容既有调用的双工件事务包装器。
def write_json_pair_atomic(
    path_first: Path,
    dict_first: dict[str, Any],
    path_second: Path,
    dict_second: dict[str, Any],
) -> None:
    """事务式发布一对互相引用的 JSON 工件。

    参数：
    - `path_first`：第一份最终输出路径。
    - `dict_first`：第一份 JSON 对象。
    - `path_second`：第二份最终输出路径。
    - `dict_second`：第二份 JSON 对象。

    返回：
    - `None`：两份输出均已创建。

    异常：
    - 任一目标已存在或文件系统提交失败时上抛，且不遗留第一份输出。
    """

    # 双工件复用批次事务，保持既有 API 与新所有权边界一致。
    write_json_batch_atomic(
        [
            (path_first, dict_first),
            (path_second, dict_second),
        ]
    )
