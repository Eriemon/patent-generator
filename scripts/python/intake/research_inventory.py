#!/usr/bin/env python3
"""扫描研究材料并生成材料盘点结果。"""
from __future__ import annotations

# 这里引入标准库参数、类型和路径工具，供材料盘点入口处理命令行与文件系统。
import argparse
import mimetypes
import sys
from pathlib import Path
from typing import Any

# 这里引入 intake 目录下的受管支持模块，避免依赖外部同名包或旧式路径注入。
from intake_case_io import ensure_dir
from intake_case_io import load_case_config
from intake_case_io import relative_to_root
from intake_case_io import write_json_file
from intake_case_io import write_text_file

# 这里引入材料分类、正文抽取与术语整理工具，供盘点入口补齐可读记录和排序摘要。
from material_classify import classify_input_document
from material_classify import strip_template_instructions
from material_extract import extract_text
from material_scan import is_probably_text
from material_scan import iter_files
from material_text import extract_headings
from material_text import keyword_counter

# 这里集中列出高价值文件名关键词，供盘点排序时优先保留背景、方案与实验材料。
HIGH_VALUE_NAME_KEYWORDS = frozenset(  # 高价值文件名关键词集合
    """
    readme
    overview
    design
    architecture
    paper
    spec
    prd
    research
    方案
    设计
    总结
    专利
    交底
    实验
    结果
    """.split()
)

# 这里集中列出高价值正文关键词，供盘点排序时识别更像发明事实的材料。
HIGH_VALUE_TEXT_KEYWORDS = frozenset(  # 高价值正文关键词集合
    """
    novel
    invention
    technical
    experiment
    result
    architecture
    algorithm
    专利
    发明
    创新
    技术方案
    实验
    效果
    现有技术
    """.split()
)

# 这里集中列出可直接视为二进制或当前盘点脚本不支持正文抽取的后缀。
BINARY_OR_UNSUPPORTED_SUFFIXES = frozenset(  # 二进制或当前不支持抽取的后缀集合
    """
    .zip
    .tar
    .gz
    .7z
    .png
    .jpg
    .jpeg
    .gif
    .webp
    """.split()
)

# 这里解析盘点参数，锁定案件目录、研究目录与扫描上限。
def parse_arguments() -> argparse.Namespace:
    """
    解析材料盘点命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含案件目录、研究目录与扫描上限的参数对象。

    异常：
    - 参数缺失时由 `argparse` 自动结束进程。
    """

    # 这里构造命令行解析器，向调用方说明本脚本负责研究材料盘点。
    obj_parser = argparse.ArgumentParser(description="Inventory research files for patent drafting.")  # 材料盘点命令行解析器

    # 这里允许显式覆盖研究根目录，保持脚本既能读配置也能直接接收外部参数。
    obj_parser.add_argument(  # 研究根目录参数
        "--research-root",
        required=False,
        help="Research folder or file. Defaults to case_config.json value.",
    )

    # 这里要求调用方提供案件目录，保证所有输出稳定落到当前案件下。
    obj_parser.add_argument(  # 案件目录参数
        "--case-dir",
        required=True,
        help="Case directory created by create_case.py.",
    )

    # 这里允许追加额外的转换目录，让 Office 转换结果也参与盘点。
    obj_parser.add_argument(  # 额外盘点根目录参数
        "--extra-root",
        action="append",
        default=[],
        help="Additional converted Markdown root to include in the inventory.",
    )

    # 这里限制最多扫描的文件数量，避免异常目录把流程拖得过长。
    obj_parser.add_argument(  # 扫描文件数量上限参数
        "--max-files",
        type=int,
        default=2000,
        help="Maximum file count for inventory.",
    )

    # 这里限制单文件保留的最大字符数，避免 JSON 和 Markdown 被超大正文撑爆。
    obj_parser.add_argument(  # 单文件抽取字符上限参数
        "--max-chars-per-file",
        type=int,
        default=80_000,
        help="Maximum extracted text per file.",
    )

    # 这里返回参数对象，供主流程继续解析研究目录和输出路径。
    return obj_parser.parse_args()

# 这里根据文件名、后缀与正文关键词对材料进行优先级评分。
def score_file(path_file: Path, str_text: str) -> int:
    """
    计算材料优先级分数。

    参数：
    - `path_file`：当前材料文件路径。
    - `str_text`：当前材料的提取文本。

    返回：
    - `int`：材料优先级分数，数值越高越应优先阅读。

    异常：
    - 无。
    """

    # 这里统一获取小写文件名主体，供标题关键词加权使用。
    str_file_stem = path_file.stem.lower()  # 小写文件名主体

    # 这里初始化优先级分数，后续按命名、格式和正文线索逐步累加。
    int_score = 0  # 当前材料优先级分数

    # 这里在文件名命中高价值关键词时加分，优先保留背景、方案与实验材料。
    if any(str_keyword in str_file_stem for str_keyword in HIGH_VALUE_NAME_KEYWORDS):

        # 这里给高价值命名加较大权重，便于人工先看关键材料。
        int_score += 5  # 高价值命名加权分

    # 这里对更可能承载高密度信息的后缀再加一层权重。
    if path_file.suffix.lower() in {".md", ".docx", ".pptx", ".pdf", ".ipynb"}:

        # 这里给常见研发文档格式补充中等权重。
        int_score += 2  # 研发文档格式加权分

    # 这里只分析头部文本，足以覆盖大多数方案、实验与创新关键词。
    str_head_text = str_text[:5000].lower()  # 正文头部样本

    # 这里按正文关键词继续加权，让真正包含技术事实的材料排到前面。
    for str_keyword in HIGH_VALUE_TEXT_KEYWORDS:

        # 这里在正文命中技术关键词时继续提高优先级。
        if str_keyword in str_head_text:

            # 这里给正文层面的技术信号增加固定权重。
            int_score += 2  # 正文技术关键词加权分

    # 这里返回最终分数，供后续排序和报告生成使用。
    return int_score

# 这里移除重复路径，保证盘点顺序稳定且不会重复处理同一材料。
def dedupe_paths(list_paths: list[Path]) -> list[Path]:
    """
    对路径列表去重并保持首次出现顺序。

    参数：
    - `list_paths`：待去重的路径列表。

    返回：
    - `list[Path]`：去重后的路径列表。

    异常：
    - 无。
    """

    # 这里初始化去重后的路径列表，按首次出现顺序保留结果。
    list_unique_paths: list[Path] = []  # 去重后的路径列表

    # 这里初始化已见路径集合，按绝对路径字符串判断重复。
    set_seen_paths: set[str] = set()  # 已见绝对路径集合

    # 这里逐个处理输入路径，保证同一路径只保留第一份记录。
    for path_item in list_paths:

        # 这里解析当前路径的绝对字符串键，避免相对写法导致重复。
        str_resolved_key = str(path_item.resolve())  # 当前路径的绝对字符串键

        # 这里跳过已见路径，防止同一材料被重复纳入盘点。
        if str_resolved_key in set_seen_paths:

            # 这里直接处理下一个路径，保持结果列表中不出现重复项。
            continue

        # 这里登记当前路径键，标记该材料已经纳入结果集。
        set_seen_paths.add(str_resolved_key)

        # 这里保留首次出现的路径对象，维持原始遍历顺序。
        list_unique_paths.append(path_item)

    # 这里返回去重后的路径列表，供主流程继续生成盘点记录。
    return list_unique_paths

# 这里解析实际研究根目录，允许命令行参数覆盖案件配置中的默认值。
def resolve_research_root(
    namespace_arguments: argparse.Namespace,
    dict_case_config: dict[str, Any],
) -> Path:
    """
    解析本次盘点实际使用的研究根目录。

    参数：
    - `namespace_arguments`：命令行参数对象。
    - `dict_case_config`：案件配置字典。

    返回：
    - `Path`：本次盘点使用的研究根目录或研究文件路径。

    异常：
    - 无；若配置缺失则退化为当前目录。
    """

    # 这里优先读取命令行指定值，没有时再回退到案件配置中的研究根目录。
    str_research_root = namespace_arguments.research_root or dict_case_config.get("research_root", ".")  # 研究根目录原始文本

    # 这里解析绝对路径，保证后续盘点记录和输出路径稳定可比较。
    return Path(str_research_root).resolve()

# 这里整理参与盘点的根路径列表，兼容主研究目录与额外转换目录。
def collect_inventory_roots(path_research_root: Path, list_extra_roots: list[str]) -> list[Path]:
    """
    收集本次盘点需要展开的根路径列表。

    参数：
    - `path_research_root`：主研究根目录或研究文件路径。
    - `list_extra_roots`：额外传入的根路径文本列表。

    返回：
    - `list[Path]`：存在且允许参与盘点的根路径列表。

    异常：
    - 无。
    """

    # 这里先放入主研究根目录，保证盘点始终覆盖正式研究输入。
    list_roots = [path_research_root]  # 参与盘点的根路径列表

    # 这里逐个处理额外根目录，只保留当前本地确实存在的路径。
    for str_extra_root in list_extra_roots:

        # 这里解析额外根目录绝对路径，供存在性判断与后续扫描使用。
        path_extra_root = Path(str_extra_root).resolve()  # 额外根目录绝对路径

        # 这里仅在额外路径存在时纳入盘点，避免无效参数干扰主流程。
        if path_extra_root.exists():

            # 这里把存在的额外根目录加入盘点输入列表。
            list_roots.append(path_extra_root)

    # 这里返回最终根路径列表，供主流程统一展开候选材料。
    return list_roots

# 这里展开参与盘点的候选材料路径，兼容目录型与单文件型研究入口。
def collect_candidate_paths(list_roots: list[Path], int_max_files: int) -> list[Path]:
    """
    展开所有需要进入盘点的候选材料路径。

    参数：
    - `list_roots`：参与盘点的根路径列表。
    - `int_max_files`：允许保留的最大文件数量。

    返回：
    - `list[Path]`：去重并裁剪后的候选材料路径列表。

    异常：
    - 无。
    """

    # 这里初始化原始候选路径列表，后续统一去重并裁剪数量。
    list_candidate_paths: list[Path] = []  # 原始候选材料路径列表

    # 这里逐个展开根路径，兼容单文件研究入口和目录研究入口。
    for path_root in list_roots:

        # 这里在单文件入口场景下直接保留该文件路径。
        if path_root.is_file():

            # 这里把单文件入口直接加入候选列表。
            list_candidate_paths.append(path_root)

        # 这里在目录入口场景下递归扫描研究材料文件。
        else:

            # 这里调用受管扫描函数展开目录内容，并遵守当前文件上限参数。
            list_candidate_paths.extend(iter_files(path_root, int_max_files=int_max_files))

    # 这里先去重再裁剪上限，保证输出顺序稳定且不会重复处理同一材料。
    return dedupe_paths(list_candidate_paths)[:int_max_files]

# 这里构造材料基础记录，统一补齐路径、大小与类型等共有字段。
def build_base_record(path_file: Path, path_research_root: Path) -> dict[str, Any]:
    """
    构造单个材料的基础盘点记录。

    参数：
    - `path_file`：当前材料文件路径。
    - `path_research_root`：主研究根目录或研究文件路径。

    返回：
    - `dict[str, Any]`：包含通用路径、大小与类型字段的基础记录。

    异常：
    - 无。
    """

    # 这里统一获取小写后缀，供后续记录与类型判断复用。
    str_suffix = path_file.suffix.lower()  # 小写文件后缀

    # 这里读取文件大小，便于后续排序和报告展示材料体量。
    int_size_bytes = path_file.stat().st_size if path_file.exists() else 0  # 文件字节数

    # 这里为相对显示路径选择参考根目录，单文件入口时退回其父目录。
    path_display_root = path_research_root if path_research_root.is_dir() else path_research_root.parent  # 材料显示参考根目录

    # 这里生成相对显示路径，尽量避免在正式结果里暴露本地绝对路径。
    str_display_path = relative_to_root(path_file, path_display_root)  # 材料显示路径

    # 这里推断材料类型标签，供清单和人工审阅快速理解文件类别。
    str_guessed_kind = mimetypes.guess_type(str(path_file))[0] or str_suffix.lstrip(".") or "unknown"  # 材料类型标签

    # 这里返回基础记录，供后续按不同材料类型继续补充字段。
    return {
        "path": str_display_path,
        "absolute_path": str(path_file),
        "suffix": str_suffix,
        "size_bytes": int_size_bytes,
        "kind": str_guessed_kind,
    }

# 这里补齐转换清单记录，避免把流水线内部工件误当成发明事实。
def apply_pipeline_manifest_record(dict_record: dict[str, Any]) -> None:
    """
    把转换清单记录标记为流水线内部文件。

    参数：
    - `dict_record`：待更新的盘点记录字典。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 这里把转换清单显式标记为不可读发明证据，防止后续事实抽取误用。
    dict_record.update(
        {
            "readable": False,
            "priority_score": -100,
            "headings": [],
            "note": "Office conversion manifest; not invention evidence.",
            "skip_as_invention": True,
            "document_role": "pipeline_manifest",
        }
    )

# 这里补齐二进制或暂不支持材料的记录，避免正文抽取对它们做无意义尝试。
def apply_unreadable_record(dict_record: dict[str, Any], str_note: str) -> None:
    """
    把盘点记录标记为当前不参与正文抽取的材料。

    参数：
    - `dict_record`：待更新的盘点记录字典。
    - `str_note`：写入记录的说明文本。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 这里把当前材料标记为不可读，同时保留说明文本供人工审阅。
    dict_record.update(
        {
            "readable": False,
            "priority_score": 0,
            "headings": [],
            "note": str_note,
        }
    )

# 这里补齐可读文本材料的记录，并在需要时把正文加入术语统计池。
def apply_text_record(
    dict_record: dict[str, Any],
    path_file: Path,
    int_max_chars_per_file: int,
    list_term_texts: list[str],
) -> None:
    """
    处理可进入正文抽取路径的材料记录。

    参数：
    - `dict_record`：待更新的盘点记录字典。
    - `path_file`：当前材料文件路径。
    - `int_max_chars_per_file`：单文件允许保留的最大字符数。
    - `list_term_texts`：术语统计文本池，会在可作为发明事实时追加正文片段。

    返回：
    - `None`。

    异常：
    - 无；底层抽取异常会由对应解析器转成可读失败文本。
    """

    # 这里抽取材料文本，供分类、预览、标题识别与术语统计复用。
    str_extracted_text = extract_text(path_file, int_max_chars=int_max_chars_per_file)  # 材料提取文本

    # 这里识别材料角色，区分真实研发材料、带提示交底书和纯模板示例。
    dict_doc_class = classify_input_document(path_file, str_extracted_text)  # 材料角色分类结果

    # 这里在带模板提示时清洗提示语，避免它们污染预览和术语统计。
    if dict_doc_class.get("contains_template_prompts"):

        # 这里在带模板提示的场景下移除提示行，只保留真实技术正文。
        str_cleaned_text = strip_template_instructions(str_extracted_text)  # 清洗后的材料正文

    # 这里在不含模板提示时保留原始提取文本，避免无谓清洗损失技术细节。
    else:

        # 这里在普通研发材料场景下直接沿用原始提取文本。
        str_cleaned_text = str_extracted_text  # 原始提取正文

    # 这里抽取标题列表，便于人工快速浏览材料结构。
    list_headings = extract_headings(str_cleaned_text)  # 材料标题列表

    # 这里计算材料优先级分数，供报告排序时优先展示高价值材料。
    int_priority_score = score_file(path_file, str_cleaned_text)  # 材料优先级分数

    # 这里对模板或示例材料强制降权，防止它们挤占高优先级位置。
    if dict_doc_class.get("skip_as_invention"):

        # 这里把只读模板材料压到列表末尾，避免误导发明事实抽取。
        int_priority_score = -100  # 模板或示例材料降权分

    # 这里把文本相关字段写回盘点记录，保留预览、角色和降权依据。
    dict_record.update(
        {
            "readable": True,
            "priority_score": int_priority_score,
            "headings": list_headings,
            "preview": str_cleaned_text[:800].replace("\x00", " "),
            "document_role": dict_doc_class.get("role"),
            "skip_as_invention": dict_doc_class.get("skip_as_invention", False),
            "contains_template_prompts": dict_doc_class.get("contains_template_prompts", False),
            "classification_reasons": dict_doc_class.get("reasons", []),
        }
    )

    # 这里仅把可作为发明事实的正文纳入术语统计池，避免模板提示干扰结果。
    if not dict_doc_class.get("skip_as_invention"):

        # 这里只截取前部正文，兼顾术语统计效果与输出体量控制。
        list_term_texts.append(str_cleaned_text[:20_000])

# 这里把盘点记录渲染成 Markdown 报告，供人工快速审阅关键材料。
def render_inventory_markdown(
    path_research_root: Path,
    list_records: list[dict[str, Any]],
    list_top_terms: list[tuple[str, int]],
    int_readable_count: int,
) -> str:
    """
    生成研究材料盘点 Markdown 报告文本。

    参数：
    - `path_research_root`：本次盘点使用的研究根目录。
    - `list_records`：排序后的盘点记录列表。
    - `list_top_terms`：高频术语统计结果。
    - `int_readable_count`：可读材料数量。

    返回：
    - `str`：最终写入文件的 Markdown 报告文本。

    异常：
    - 无。
    """

    # 这里初始化 Markdown 行列表，先写总体摘要和术语概览。
    list_lines = [  # 盘点 Markdown 行列表
        "# Research Inventory",  # 报告主标题
        "",  # 主标题后的空行
        f"Research root: `{path_research_root}`",  # 研究根目录摘要
        f"Files scanned: {len(list_records)}",  # 已扫描文件数量
        f"Readable files: {int_readable_count}",  # 可读材料数量
        "",  # 摘要段后的空行
        "## Top terms",  # 高频术语小节标题
        "",  # 术语标题后的空行
    ]

    # 这里把高频术语写入 Markdown，方便人工先理解材料主题。
    list_lines.extend([f"- {str_term}: {int_hit_count}" for str_term, int_hit_count in list_top_terms[:30]])

    # 这里补齐高优先级材料章节标题，供后续逐条展开记录。
    list_lines.extend(
        [
            "",  # 术语段与材料段之间的空行
            "## High priority files",  # 高优先级材料小节标题
            "",  # 材料小节标题后的空行
        ]
    )

    # 这里把前若干高优先级材料展开到 Markdown 报告中。
    for dict_record in list_records[:40]:

        # 这里写入当前材料标题，作为该材料的小节入口。
        list_lines.append(f"### {dict_record['path']}")

        # 这里把当前材料的基础排序与体量信息作为一组条目写入报告。
        list_lines.extend(
            [
                f"- score: {dict_record.get('priority_score', 0)}",  # 帮助人工先看高价值材料的排序分数
                f"- suffix: {dict_record.get('suffix') or '[none]'}",  # 保留源文件后缀以判断材料格式
                f"- size: {dict_record.get('size_bytes')} bytes",  # 展示材料体量以估计阅读成本
            ]
        )

        # 这里在存在标题列表时写入前若干标题，便于快速浏览文档结构。
        if dict_record.get("headings"):

            # 这里写入标题列表小节名，提示下方为章节标题摘要。
            list_lines.append("- headings:")

            # 这里逐个写入标题条目，保留前若干关键标题供人工预览。
            list_lines.extend([f"  - {str_heading}" for str_heading in dict_record["headings"][:10]])

        # 这里在存在正文预览时写入预览摘要，帮助人工判断材料内容。
        if dict_record.get("preview"):

            # 这里压平预览文本中的换行，避免 Markdown 报告被长段正文切碎。
            str_preview_text = str(dict_record["preview"]).strip().replace("\n", " ")[:300]  # 预览摘要文本

            # 这里写入当前材料的正文预览摘要。
            list_lines.append(f"- preview: {str_preview_text}")

        # 这里在存在附加说明时写入说明文本，保留降权或跳过原因。
        if dict_record.get("note"):

            # 这里写入当前材料说明，方便人工理解为什么被跳过或降权。
            list_lines.append(f"- note: {dict_record['note']}")

        # 这里在每个材料小节后补一个空行，保证 Markdown 阅读体验稳定。
        list_lines.append("")

    # 这里返回最终 Markdown 文本，供主流程统一写入案件目录。
    return "\n".join(list_lines)

# 这里执行研究材料盘点主流程，并把 Markdown 报告路径写到标准输出末尾。
def main() -> int:
    """
    执行研究材料盘点主流程。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 配置缺失、文件读写失败或材料路径错误时由底层异常上抛。
    """

    # 这里解析命令行参数，锁定案件目录、研究目录与扫描上限。
    namespace_arguments = parse_arguments()  # 材料盘点参数

    # 这里解析案件目录绝对路径，保证输出始终落到当前案件下。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 案件根目录

    # 这里读取案件配置，供研究根目录缺省场景回退使用。
    dict_case_config = load_case_config(path_case_dir)  # 案件配置字典

    # 这里解析实际研究根目录，允许命令行显式覆盖案件配置。
    path_research_root = resolve_research_root(namespace_arguments, dict_case_config)  # 实际研究根目录

    # 这里创建盘点输出目录，保证 JSON 与 Markdown 都有稳定落点。
    path_output_dir = ensure_dir(path_case_dir / "01_inventory")  # 盘点输出目录

    # 这里把主研究入口与已存在的转换目录合并成待扫描根集合。
    list_roots = collect_inventory_roots(path_research_root, namespace_arguments.extra_root)  # 本轮扫描起点集合

    # 这里把每个扫描根展开成真实材料文件路径，形成本轮候选清单。
    list_paths = collect_candidate_paths(list_roots, namespace_arguments.max_files)  # 最终候选材料路径列表

    # 这里初始化盘点记录列表，后续逐个写入结构化条目。
    list_records: list[dict[str, Any]] = []  # 盘点记录列表

    # 这里初始化术语统计文本池，只汇总真正可作为发明事实的材料正文。
    list_term_texts: list[str] = []  # 术语统计文本池

    # 这里逐个处理候选材料路径，生成最终盘点记录。
    for path_item in list_paths:

        # 这里先构造当前材料基础记录，补齐路径、大小与类型等共有字段。
        dict_record = build_base_record(path_item, path_research_root)  # 当前材料基础记录

        # 这里把转换清单标记为流水线内部工件，不让它参与发明事实判断。
        if path_item.name == "conversion_manifest.json":

            # 这里把转换清单写成专门记录，明确它只是流水线内部文件。
            apply_pipeline_manifest_record(dict_record)

        # 这里对二进制或暂不支持的后缀直接做不可读标记，避免无意义正文抽取。
        elif path_item.suffix.lower() in BINARY_OR_UNSUPPORTED_SUFFIXES:

            # 这里把当前材料标记为当前盘点脚本不支持的文件类型。
            apply_unreadable_record(dict_record, "binary or unsupported by inventory script")

        # 这里对可进入正文抽取路径的材料补齐文本预览、角色和优先级信息。
        elif is_probably_text(path_item):

            # 这里对文本材料执行正文抽取和角色分类，并在需要时更新术语统计池。
            apply_text_record(
                dict_record,
                path_item,
                namespace_arguments.max_chars_per_file,
                list_term_texts,
            )

        # 这里把其他未支持正文抽取的材料统一标记为不可读。
        else:

            # 这里给未支持后缀写入统一说明，避免后续流程猜测其处理方式。
            apply_unreadable_record(dict_record, "unsupported extension")

        # 这里把当前材料记录加入总结果列表，供后续排序与输出。
        list_records.append(dict_record)

    # 这里按优先级分数和文件大小排序，让高价值材料排到报告前面。
    list_records.sort(
        key=lambda dict_record: (
            dict_record.get("priority_score", 0),
            dict_record.get("size_bytes", 0),
        ),
        reverse=True,
    )

    # 这里统计可进入正文抽取路径的材料数量，用于摘要展示盘点覆盖度。
    int_readable_count = sum(1 for dict_record in list_records if dict_record.get("readable"))  # 正文可读材料总数

    # 这里从有效正文中提炼高频技术词，供后续事实抽取和查新计划参考。
    list_top_terms = keyword_counter("\n".join(list_term_texts), int_limit=50)  # 高频术语统计结果

    # 这里组装最终盘点 JSON 数据结构，供后续事实抽取和总流程复用。
    dict_inventory = {  # 最终盘点 JSON 数据
        "research_root": str(path_research_root),  # 写入清单头部的研究根目录文本
        "file_count": len(list_records),  # 已纳入当前盘点的材料总数
        "readable_count": int_readable_count,  # 允许进入正文抽取链的材料数
        "top_terms": list_top_terms,  # 后续事实整理可直接参考的术语统计表
        "files": list_records,  # 每个材料对应的逐条盘点记录
    }

    # 这里固定 JSON 落盘位置，供后续结构化事实抽取读取材料清单。
    path_inventory_json = path_output_dir / "research_inventory.json"  # 盘点 JSON 路径

    # 这里固定人工审阅报告位置，方便人工快速浏览优先级较高的材料。
    path_inventory_markdown = path_output_dir / "research_inventory.md"  # 人工审阅 Markdown 报告路径

    # 这里写出结构化盘点 JSON，供后续脚本读取材料清单与优先级。
    write_json_file(path_inventory_json, dict_inventory)

    # 这里拼装给人工审阅的报告正文，集中展示术语概览和重点材料摘要。
    str_inventory_markdown = render_inventory_markdown(  # 渲染后的 Markdown 报告文本
        path_research_root,  # 用于报告摘要头部展示的研究根目录
        list_records,  # 已按优先级排好序的材料明细
        list_top_terms,  # 展示在术语小节中的高频词表
        int_readable_count,  # 报告摘要里展示的可读材料总数
    )  # 盘点 Markdown 文本

    # 这里把盘点 Markdown 报告写入正式案件目录。
    write_text_file(path_inventory_markdown, str_inventory_markdown)

    # 这里把 Markdown 报告路径作为机器可读输出写给上游流程。
    sys.stdout.write(str(path_inventory_markdown.resolve()) + "\n")

    # 这里返回成功状态码，表示研究材料盘点已完成。
    return 0

# 这里保留标准脚本入口，方便命令行和流水线子进程统一调用。
if __name__ == "__main__":

    # 这里通过标准退出路径返回状态码，保持命令行调用行为一致。
    raise SystemExit(main())
