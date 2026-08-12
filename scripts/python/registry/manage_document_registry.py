"""治理 Markdown 文档注册。

stdout_protocol: json
当调用方使用 `--json` 时，stdout 只包含单个完整 JSON 对象。
"""

# 启用延迟注解，保持 CLI 类型标注在 Python 3.10 及以上版本稳定可用。
from __future__ import annotations

# 标准库
import argparse
import json
import os
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Sequence

# 同目录公共能力：退出码与异常协议。
from registry_common import (
    INT_EXIT_OK,
    INT_EXIT_REGISTRY,
    INT_EXIT_REQUEST,
    RegistryError,
    calculate_markdown_hash,
)

# 同目录公共能力：注册表读取与路径解析。
from registry_common import (
    load_registry,
    read_json_object,
    registry_root,
    require_object_list,
    resolve_skill_root,
)

# 模糊重复阈值偏向只报告高度等价正文，避免删除唯一语义。
FLOAT_FUZZY_THRESHOLD = 0.92  # Markdown 规范文本相似度阈值

# 修改型 finalize 的第二次确认文本保持稳定且可审计。
STR_MODIFIED_CONFIRMATION = "CONFIRM MODIFIED DOCUMENT REGISTRY"  # 修改决定二次确认口令

# 为五个文档治理动作建立统一参数解析器。
def build_argument_parser() -> argparse.ArgumentParser:
    """创建 registry.document-governance 参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：包含 status、scan、init、check、finalize 的解析器。

    异常：
    - 无。
    """

    # 顶层描述强调 Markdown 正文与 JSON 元数据的权威分工。
    parser = argparse.ArgumentParser(  # 文档治理顶层解析器
        description="检查并治理 Markdown 正文与 JSON 注册元数据。",  # 顶层帮助说明
    )

    # 子命令是必需动作，防止无意进入写入路径。
    object_subparsers: Any = parser.add_subparsers(  # 五类文档治理动作集合
        dest="str_action",  # 保存调用方选择的动作名称
        required=True,  # 禁止缺失动作时进入治理流程
    )

    # status 只读检查已注册路径和哈希。
    argument_parser_status: argparse.ArgumentParser = object_subparsers.add_parser(  # 文档状态动作解析器
        "status",  # 只读状态动作名称
        help="只读检查已注册文档路径、哈希与评审状态",  # 状态动作帮助文本
    )

    # status 可选择机器 JSON 输出。
    argument_parser_status.add_argument("--json", action="store_true", dest="bool_json")

    # scan 只读比较十份 Markdown 的精确与模糊等价关系。
    argument_parser_scan: argparse.ArgumentParser = object_subparsers.add_parser(  # 重复扫描动作解析器
        "scan",  # 只读扫描动作名称
        help="只读扫描精确和模糊等价重复",  # 扫描动作帮助文本
    )

    # 重复扫描结果可切换为机器 JSON 输出。
    argument_parser_scan.add_argument("--json", action="store_true", dest="bool_json")

    # init 发现未注册 Markdown，只有显式 write 才更新目录。
    argument_parser_init = object_subparsers.add_parser(  # 文档初始化动作解析器
        "init",  # 候选初始化动作名称
        help="发现并初始化尚未注册的 Markdown 元数据",  # 初始化动作帮助文本
    )

    # 显式写入开关授权新增 pending 记录。
    argument_parser_init.add_argument("--write", action="store_true")

    # 初始化预览或写入结果可切换为机器 JSON 输出。
    argument_parser_init.add_argument("--json", action="store_true", dest="bool_json")

    # check 汇总状态和重复扫描，保持只读。
    argument_parser_check: argparse.ArgumentParser = object_subparsers.add_parser(  # 综合检查动作解析器
        "check",  # 只读综合检查动作名称
        help="只读执行文档注册完整检查",  # 综合检查动作帮助文本
    )

    # 综合检查证据可切换为机器 JSON 输出。
    argument_parser_check.add_argument("--json", action="store_true", dest="bool_json")

    # finalize 显式更新哈希与评审决定。
    argument_parser_finalize: argparse.ArgumentParser = object_subparsers.add_parser(  # 评审完成动作解析器
        "finalize",  # 显式完成评审动作名称
        help="显式完成文档注册评审并刷新哈希",  # 完成动作帮助文本
    )

    # finalize 必须声明处置决定。
    argument_parser_finalize.add_argument("--decision", required=True, choices=("accepted", "modified", "rejected"))

    # 评审说明进入 reviews JSON，保持处置原因可追溯。
    argument_parser_finalize.add_argument("--notes", required=True)

    # 修改决定要求第二次精确确认。
    argument_parser_finalize.add_argument("--second-confirmation")

    # finalize 只有显式 write 才允许更新 JSON 权威。
    argument_parser_finalize.add_argument("--write", action="store_true")

    # 评审完成结果可切换为机器 JSON 输出。
    argument_parser_finalize.add_argument("--json", action="store_true", dest="bool_json")

    # 返回完整解析器供 main 使用。
    return parser

# 规范化 Markdown 正文供等价重复比较。
def normalize_markdown(str_text: str) -> str:
    """生成忽略空白与 Markdown 标点的比较文本。

    参数：
    - `str_text`：Markdown 正文。

    返回：
    - `str`：小写、单空格分隔的规范文本。

    异常：
    - 无。
    """

    # 将常见 Markdown 标点替换为空格，保留正文语义字符。
    str_without_markup = str_text.translate(str.maketrans({char: " " for char in "#*`_~>|-[](){}"}))  # 去除展示标记的正文

    # 合并全部空白并小写英文，形成确定性比较文本。
    str_normalized = " ".join(str_without_markup.lower().split())  # Markdown 规范比较文本

    # 返回供哈希和相似度计算复用的正文。
    return str_normalized

# 读取文档目录并返回注册对象列表。
def load_document_records(path_skill_root: Path) -> list[dict[str, Any]]:
    """读取文档注册目录。

    参数：
    - `path_skill_root`：正式技能源码、dist 或安装副本根目录。

    返回：
    - `list[dict[str, Any]]`：文档注册记录。

    异常：
    - `RegistryError`：目录缺失、损坏或字段类型错误时抛出。
    """

    # 定位固定文档目录路径。
    path_catalog = registry_root(path_skill_root) / "documents" / "catalog.json"  # 文档注册目录路径

    # 读取 JSON 对象并收窄 documents 字段类型。
    dict_catalog = read_json_object(path_catalog)  # 文档目录对象

    # 返回对象记录副本，避免只读动作意外修改解析对象。
    return require_object_list(dict_catalog, "documents", path_catalog)

# 只读计算全部已注册文档的路径和哈希状态。
def document_status(path_skill_root: Path) -> dict[str, Any]:
    """检查文档注册数量、缺失路径和陈旧哈希。

    参数：
    - `path_skill_root`：正式技能源码、dist 或安装副本根目录。

    返回：
    - `dict[str, Any]`：已注册数量、缺失项、陈旧项和评审决定。

    异常：
    - `RegistryError`：文档目录或评审 JSON 无法读取时抛出。
    """

    # 加载文档目录，不要求所有哈希先通过，便于状态命令报告差异。
    list_documents = load_document_records(path_skill_root)  # 已注册文档记录

    # 分别收集不存在路径与哈希不一致记录。
    list_missing: list[str] = []  # 已注册但不存在的文档标识

    # 陈旧记录要求显式 finalize 刷新。
    list_stale: list[str] = []  # 正文哈希已变化的文档标识

    # 逐项读取真实文件事实。
    for dict_document in list_documents:

        # 根据技能内相对路径定位 Markdown。
        path_document = path_skill_root / str(dict_document.get("path", ""))  # 当前已注册文档路径

        # 缺失正文不再尝试计算哈希。
        if not path_document.is_file():

            # 保存稳定 id，避免状态结果泄漏绝对路径。
            list_missing.append(str(dict_document.get("id", "")))

            # 继续检查下一份文档。
            continue

        # 原始字节哈希与 catalog 事实逐字节比较。
        str_actual_hash = calculate_markdown_hash(path_document)  # 当前文档规范 SHA-256

        # 哈希变化表示元数据尚未完成评审。
        if str_actual_hash != dict_document.get("sha256"):

            # 保存稳定 id 供 finalize 和报告引用。
            list_stale.append(str(dict_document.get("id", "")))

    # 读取当前评审决定，不从文档内容反推处置结论。
    dict_reviews = read_json_object(registry_root(path_skill_root) / "governance" / "reviews.json")  # 当前评审记录

    # 返回只读状态载荷。
    dict_result = {  # 文档注册状态
        "status": "ready" if not list_missing and not list_stale else "attention",  # 当前整体状态
        "registered_count": len(list_documents),  # 已注册 Markdown 数量
        "missing_document_ids": list_missing,  # 缺失正文标识
        "stale_document_ids": list_stale,  # 哈希陈旧标识
        "review_decision": dict_reviews.get("decision", "pending"),  # 当前语义评审决定
        "written": False,  # status 永远只读
    }

    # 返回供 status 和 check 共用的结果。
    return dict_result

# 扫描已注册 Markdown 的精确和高度模糊等价关系。
def scan_documents(path_skill_root: Path) -> dict[str, Any]:
    """比较已注册 Markdown 正文。

    参数：
    - `path_skill_root`：正式技能源码、dist 或安装副本根目录。

    返回：
    - `dict[str, Any]`：扫描数量、精确重复和模糊重复对。

    异常：
    - `RegistryError`：目录记录或 Markdown 无法读取时抛出。
    """

    # 文档目录决定扫描范围，不递归吸收未注册 Markdown。
    list_documents = load_document_records(path_skill_root)  # 参与重复扫描的文档记录

    # 保存每份文档的规范正文供成对比较。
    list_texts: list[tuple[str, str]] = []  # 文档 id 与规范正文

    # 逐项读取 UTF-8 Markdown 并规范化。
    for dict_document in list_documents:

        # 当前文档路径必须保持在技能根内。
        path_document = path_skill_root / str(dict_document.get("path", ""))  # 待扫描 Markdown 路径

        # 缺失文档无法参与重复判断，必须显式阻断。
        if not path_document.is_file():

            # 状态错误包含稳定 id 而不是绝对路径。
            raise RegistryError(f"> ERR: [Python] 已注册文档不存在：{dict_document.get('id', '')}")

        # 读取并规范化正文，保留语义文本用于相似度计算。
        str_normalized = normalize_markdown(path_document.read_text(encoding="utf-8"))  # 当前文档规范正文

        # 保存 id 与正文供唯一成对组合使用。
        list_texts.append((str(dict_document.get("id", "")), str_normalized))

    # 精确重复只报告规范正文完全相同的文档对。
    list_exact_duplicates: list[list[str]] = []  # 精确等价文档对

    # 模糊重复只报告未精确相同且达到高阈值的文档对。
    list_fuzzy_duplicates: list[dict[str, object]] = []  # 高相似文档对与相似度

    # 每份文档只与后续成员比较一次。
    for int_left_index, tuple_left in enumerate(list_texts):

        # 从下一位置开始构造无重复组合。
        for tuple_right in list_texts[int_left_index + 1 :]:

            # 解包当前左右文档标识和规范正文。
            str_left_id, str_left_text = tuple_left  # 左侧文档事实

            # 右侧文档事实保持同一字段顺序。
            str_right_id, str_right_text = tuple_right  # 右侧文档事实

            # 完全相同正文优先登记为精确重复。
            if str_left_text == str_right_text:

                # 精确重复对保持目录顺序。
                list_exact_duplicates.append([str_left_id, str_right_id])

                # 精确重复不再重复登记为模糊项。
                continue

            # 使用标准库 SequenceMatcher 计算规范正文相似度。
            float_similarity = SequenceMatcher(None, str_left_text, str_right_text).ratio()  # 当前文档对相似度

            # 只报告高度接近的候选，唯一语义文档不进入处置队列。
            if float_similarity >= FLOAT_FUZZY_THRESHOLD:

                # 保存稳定 id 和四位小数相似度供人工审查。
                list_fuzzy_duplicates.append({  # 当前模糊重复候选
                    "left": str_left_id,  # 左侧文档标识
                    "right": str_right_id,  # 右侧文档标识
                    "similarity": round(float_similarity, 4),  # 规范正文相似度
                })

    # 返回只读扫描结果，不自动删除或合并任何 Markdown。
    dict_result = {  # 文档重复扫描结果
        "status": "ready" if not list_exact_duplicates and not list_fuzzy_duplicates else "review-required",  # 重复处置状态
        "scanned_count": len(list_texts),  # 实际扫描文档数
        "exact_duplicates": list_exact_duplicates,  # 规范正文完全相同的文档对
        "fuzzy_duplicates": list_fuzzy_duplicates,  # 高相似文档对
        "written": False,  # 重复扫描未修改注册表
    }

    # 返回供 scan、check 和 finalize 复用的证据。
    return dict_result

# 以同目录临时文件原子写入 JSON 权威。
def write_json_atomic(path_target: Path, dict_payload: dict[str, Any]) -> None:
    """原子写入 UTF-8 JSON 文件。

    参数：
    - `path_target`：受管 JSON 目标路径。
    - `dict_payload`：待写入顶层对象。

    返回：
    - 无。

    异常：
    - `OSError`：写入或原子替换失败时传播。
    """

    # 临时文件固定在目标同目录，确保 replace 具备原子语义。
    path_temp = path_target.with_suffix(path_target.suffix + ".tmp")  # JSON 原子写入临时路径

    # 使用稳定键序和末尾换行生成可审阅 JSON。
    str_text = json.dumps(dict_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"  # 待写入 JSON 文本

    # 临时文件写入成功后才替换权威目标。
    path_temp.write_text(str_text, encoding="utf-8")

    # 同目录原子替换避免调用方观察到半写入对象。
    os.replace(path_temp, path_target)

# 发现技能内尚未登记的 Markdown，并可显式加入 pending 目录。
def initialize_documents(path_skill_root: Path, bool_write: bool) -> dict[str, Any]:
    """发现或登记未注册 Markdown。

    参数：
    - `path_skill_root`：正式技能源码、dist 或隔离副本根目录。
    - `bool_write`：是否显式写入新增 pending 记录。

    返回：
    - `dict[str, Any]`：候选路径、登记数量和写入状态。

    异常：
    - `RegistryError`：文档目录无法读取时抛出。
    """

    # 读取现有目录并建立已登记路径集合。
    path_catalog = registry_root(path_skill_root) / "documents" / "catalog.json"  # 文档目录路径

    # 保留顶层 schema 和原记录顺序。
    dict_catalog = read_json_object(path_catalog)  # 初始化前的文档目录对象

    # 收窄文档记录并收集已登记路径。
    list_documents = require_object_list(dict_catalog, "documents", path_catalog)  # 当前文档记录

    # 路径集合用于快速排除已登记 Markdown。
    set_registered_paths = {str(dict_document.get("path", "")) for dict_document in list_documents}  # 已登记相对路径

    # 技能入口与 references 子树构成允许发现范围。
    list_candidates = ["SKILL.md"]  # 未过滤 Markdown 候选路径

    # references 递归扫描只收集普通 Markdown 文件。
    path_references = path_skill_root / "references"  # 允许发现 Markdown 的参考资料根

    # 将 references 下真实 Markdown 转为技能内相对路径。
    iterator_relative_paths = (  # 参考资料 Markdown 相对路径迭代器
        path_document.relative_to(path_skill_root)  # 当前 Markdown 的技能内路径
        for path_document in path_references.rglob("*.md")  # references 下的 Markdown 文件
    )

    # 扩展候选清单，后续统一稳定排序。
    list_candidates.extend(  # 加入参考资料 Markdown 路径
        path_relative.as_posix()  # 跨平台稳定的正斜杠路径
        for path_relative in iterator_relative_paths  # 已收窄的技能内路径
    )

    # 稳定排序并排除已登记路径。
    list_missing_paths = sorted(str_path for str_path in list_candidates if str_path not in set_registered_paths)  # 尚未登记 Markdown 路径

    # 仅显式 write 且存在候选时更新目录。
    if bool_write and list_missing_paths:

        # 为每个新文档创建 pending 元数据，不猜测详细业务摘要。
        for str_path in list_missing_paths:

            # 解析 Markdown 真实路径并计算初始哈希。
            path_document = path_skill_root / str_path  # 待登记 Markdown 路径

            # 文件名生成稳定候选 id，冲突仍由后续完整校验阻断。
            str_stem = path_document.stem.lower().replace("_", "-")  # 文档 id 候选后缀

            # 追加 pending 记录，要求人工 finalize 补充和确认语义。
            list_documents.append({  # 新增文档 pending 元数据
                "id": f"doc.{str_stem}",  # 基于文件名的候选标识
                "path": str_path,  # 技能内 Markdown 相对路径
                "title": path_document.stem.replace("_", " "),  # 初始可读标题
                "kind": "canonical" if str_path.startswith("references/canonical/") else "index",  # 初始文档种类
                "summary": "待人工复核并在 finalize 时确认的新增 Markdown 文档。",  # pending 摘要
                "keywords": [path_document.stem],  # 初始检索关键词
                "sha256": calculate_markdown_hash(path_document),  # 新增正文规范哈希
            })

        # 更新目录对象并原子写回。
        dict_catalog["documents"] = list_documents  # 包含新增 pending 记录的目录

        # 写入权威 JSON，Markdown 正文本身保持不变。
        write_json_atomic(path_catalog, dict_catalog)

    # 返回发现与写入证据。
    dict_result = {  # 文档初始化结果
        "status": "initialized" if bool_write else "preview",  # 写入或预览状态
        "candidate_paths": list_missing_paths,  # 尚未登记或本次登记路径
        "candidate_count": len(list_missing_paths),  # 候选数量
        "written": bool_write and bool(list_missing_paths),  # 实际写入标记
    }

    # 返回供 CLI 输出。
    return dict_result

# 显式刷新文档哈希与当前评审决定。
def finalize_documents(
    path_skill_root: Path,
    str_decision: str,
    str_notes: str,
    str_second_confirmation: str | None,
    bool_write: bool,
) -> dict[str, Any]:
    """完成文档注册评审。

    参数：
    - `path_skill_root`：正式技能源码、dist 或隔离副本根目录。
    - `str_decision`：accepted、modified 或 rejected。
    - `str_notes`：本次评审原因与保留边界。
    - `str_second_confirmation`：modified 决定要求的精确二次确认。
    - `bool_write`：是否显式写回 JSON 权威。

    返回：
    - `dict[str, Any]`：决定、扫描证据和写入状态。

    异常：
    - `RegistryError`：确认不足、重复未处置或文件读取失败时抛出。
    """

    # modified 决定只有精确二次确认后才能进入写入路径。
    if str_decision == "modified" and str_second_confirmation != STR_MODIFIED_CONFIRMATION:

        # 修改候选需要第二次确认，避免一次输入直接提升语义变更。
        raise RegistryError("> ERR: [Python] modified 决定缺少精确二次确认", INT_EXIT_REQUEST)

    # 先只读扫描重复，保留处置证据。
    dict_scan = scan_documents(path_skill_root)  # finalize 前重复扫描结果

    # accepted 不允许在仍有重复候选时直接完成。
    if str_decision == "accepted" and (dict_scan["exact_duplicates"] or dict_scan["fuzzy_duplicates"]):

        # 唯一语义边界必须先逐项处置后再接受。
        raise RegistryError("> ERR: [Python] 仍有重复候选时不能 finalize 为 accepted")

    # 未显式 write 时只返回预览，不更新任何哈希或决定。
    if not bool_write:

        # 预览结果明确标记未写入。
        return {
            "status": "preview",  # finalize 预览状态
            "decision": str_decision,  # 待写入决定
            "scan": dict_scan,  # 当前重复扫描证据
            "written": False,  # 未获写入授权
        }

    # 定位文档目录并读取原始对象。
    path_root = registry_root(path_skill_root)  # 当前注册表配置根

    # 文档目录用于刷新全部正文哈希。
    path_catalog = path_root / "documents" / "catalog.json"  # 待刷新哈希的文档目录路径

    # 保留目录顶层 schema。
    dict_catalog = read_json_object(path_catalog)  # finalize 使用的文档目录对象

    # 收窄记录后逐项刷新真实哈希。
    list_documents = require_object_list(dict_catalog, "documents", path_catalog)  # 待刷新文档记录

    # 每份文档必须存在才能完成评审。
    for dict_document in list_documents:

        # 根据登记路径读取真实 Markdown。
        path_document = path_skill_root / str(dict_document.get("path", ""))  # 待 finalize 文档路径

        # 缺失正文阻断整个原子评审更新。
        if not path_document.is_file():

            # 报告稳定标识，避免生成半更新目录。
            raise RegistryError(f"> ERR: [Python] 无法 finalize 缺失文档：{dict_document.get('id', '')}")

        # 刷新正文逐字节 SHA-256。
        dict_document["sha256"] = calculate_markdown_hash(path_document)  # 当前正文新规范哈希

    # 写回刷新后的文档目录。
    dict_catalog["documents"] = list_documents  # 已刷新哈希的文档记录

    # 评审记录保留现有接口事实并更新重复证据、决定和说明。
    path_reviews = path_root / "governance" / "reviews.json"  # 文档治理评审路径

    # 读取当前评审对象以保留未修改字段。
    dict_reviews = read_json_object(path_reviews)  # 当前文档治理评审对象

    # 写入本次扫描结果与处置决定。
    dict_reviews["exact_duplicates"] = dict_scan["exact_duplicates"]  # 当前精确重复证据

    # 模糊重复证据同样来自本次扫描。
    dict_reviews["fuzzy_duplicates"] = dict_scan["fuzzy_duplicates"]  # 当前模糊重复证据

    # 保存用户明确选择的评审决定。
    dict_reviews["decision"] = str_decision  # 本次文档治理决定

    # 保存非空评审说明，禁止无理由完成治理。
    dict_reviews["notes"] = str_notes.strip()  # 本次评审说明

    # 原子写入两份权威 JSON；单文件原子性避免半文件状态。
    write_json_atomic(path_catalog, dict_catalog)

    # 评审记录在目录成功后写入，任何失败都会由发布门禁继续阻断。
    write_json_atomic(path_reviews, dict_reviews)

    # 返回最终写入证据。
    dict_result = {  # 文档 finalize 结果
        "status": "finalized",  # 已完成评审更新
        "decision": str_decision,  # 已写入决定
        "registered_count": len(list_documents),  # 已刷新文档数量
        "scan": dict_scan,  # 本次重复扫描证据
        "written": True,  # 已显式写入 JSON 权威
    }

    # 返回供 CLI 输出和后续 registry.build 使用。
    return dict_result

# 输出机器 JSON 或简短人类摘要。
def emit_result(dict_result: dict[str, Any], bool_json: bool) -> None:
    """输出文档治理结果。

    参数：
    - `dict_result`：当前子命令结果载荷。
    - `bool_json`：是否启用机器可读 stdout 协议。

    返回：
    - 无。

    异常：
    - 无。
    """

    # 机器协议只输出一份完整 JSON。
    if bool_json:

        # 稳定键序便于 CI 与发布证据比较。
        print(json.dumps(dict_result, ensure_ascii=False, sort_keys=True))

        # JSON 协议分支不追加人类摘要。
        return

    # 人类模式只报告状态与写入布尔值。
    str_status = str(dict_result.get("status", "unknown"))  # 文档治理结果状态

    # 写入标志用于区分只读检查和显式变更。
    bool_written = bool(dict_result.get("written", False))  # 本次动作是否写入权威文件

    # 人类模式只输出稳定的简短摘要。
    print(f"> INFO: [Python] document registry {str_status}，written={bool_written}")

# 根据已解析动作调用对应文档治理职责。
def dispatch_action(args: argparse.Namespace, path_skill_root: Path) -> dict[str, Any]:
    """路由文档治理动作并返回结构化结果。

    参数：
    - `args`：已解析的文档治理命令行参数。
    - `path_skill_root`：当前源码、dist 或安装副本技能根。

    返回：
    - `dict[str, Any]`：所选动作的结构化结果。

    异常：
    - `RegistryError`：注册表状态或写入授权不满足时抛出。
    """

    # status 先执行完整注册表校验，再生成文档职责状态。
    if args.str_action == "status":

        # 加载结果无需返回，但调用本身强制验证全部注册关系。
        load_registry(path_skill_root)

        # 返回文档路径、哈希和评审状态。
        return document_status(path_skill_root)

    # scan 只读扫描精确和模糊等价重复。
    if args.str_action == "scan":

        # 扫描职责不写入任何 JSON 或 Markdown。
        return scan_documents(path_skill_root)

    # init 预览或显式登记未注册 Markdown。
    if args.str_action == "init":

        # write 开关是初始化目录的唯一写入授权。
        return initialize_documents(path_skill_root, args.write)

    # check 汇总路径哈希与重复扫描结果。
    if args.str_action == "check":

        # 分别保留状态和重复证据，避免单个布尔值掩盖细节。
        dict_status = document_status(path_skill_root)  # 文档路径与哈希状态

        # 重复扫描保持独立证据字段。
        dict_scan = scan_documents(path_skill_root)  # 文档精确与模糊重复状态

        # 只有两类证据均就绪时综合状态才可发布。
        str_status = (  # 文档治理综合状态
            "ready"  # 两类检查全部通过
            if dict_status["status"] == "ready" and dict_scan["status"] == "ready"  # 就绪判定条件
            else "attention"  # 任一检查需要处置
        )

        # 返回综合检查证据且明确保持只读。
        return {
            "status": str_status,  # 综合治理状态
            "document_status": dict_status,  # 路径与哈希证据
            "duplicate_scan": dict_scan,  # 精确与模糊重复证据
            "written": False,  # 综合检查未修改注册表
        }

    # finalize 是解析器保证的剩余动作，显式传递确认和写入授权。
    return finalize_documents(
        path_skill_root,  # 当前技能根
        args.decision,  # 用户选择的评审决定
        args.notes,  # 可追溯评审说明
        args.second_confirmation,  # modified 决定二次确认
        args.write,  # JSON 权威写入授权
    )

# 路由五个文档治理动作并转换稳定退出码。
def main(list_argv: Sequence[str] | None = None) -> int:
    """执行 registry.document-governance CLI。

    参数：
    - `list_argv`：可选参数序列；`None` 时读取真实命令行。

    返回：
    - `int`：0 成功，2 请求错误，3 注册表状态错误。

    异常：
    - 无；预期错误转换为稳定退出码。
    """

    # 解析子命令及其写入授权。
    parser = build_argument_parser()  # 文档治理参数解析器

    # argparse 负责语法错误退出码 2。
    args = parser.parse_args(list_argv)  # 当前文档治理参数

    # 从入口位置定位当前技能副本。
    path_skill_root = resolve_skill_root(Path(__file__))  # 当前文档治理入口所属技能根

    # 各动作共享统一状态错误处理。
    try:

        # 独立路由函数保持入口控制流浅且便于测试。
        dict_result = dispatch_action(args, path_skill_root)  # 当前动作结构化结果

    # 预期治理错误写 stderr 并返回固定退出码。
    except RegistryError as exc:

        # 保持成功 JSON stdout 纯净。
        if args.bool_json:

            # JSON 模式的 stderr 也保持单对象机器协议。
            dict_error = {  # 文档治理错误对象
                "status": "error",  # 失败状态
                "message": str(exc),  # 已带稳定前缀的错误消息
                "exit_code": exc.int_exit_code,  # 注册表异常协议码
            }

            # 错误对象只写 stderr，stdout 保持为空。
            print(json.dumps(dict_error, ensure_ascii=False, sort_keys=True), file=sys.stderr)

        # 非 JSON 模式输出带稳定错误前缀的人类摘要。
        else:

            # 保留异常细节并确保静态输出协议可识别。
            print(f"> ERR: [Python] document registry failed: {exc}", file=sys.stderr)

        # 请求或状态错误沿用异常协议码。
        return exc.int_exit_code

    # 输出机器协议或简短人类摘要。
    emit_result(dict_result, args.bool_json)

    # check 的 attention 状态使用注册表错误码阻断发布。
    if args.str_action == "check" and dict_result["status"] != "ready":

        # 状态不完整但请求有效，返回 3。
        return INT_EXIT_REGISTRY

    # 其他成功动作统一返回 0。
    return INT_EXIT_OK

# 仅直接执行文件时启动 CLI，导入模块保持无副作用。
if __name__ == "__main__":

    # 将治理业务退出码交给操作系统。
    raise SystemExit(main())
