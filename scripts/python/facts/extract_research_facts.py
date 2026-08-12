#!/usr/bin/env python3
"""协调研究事实抽取、候选构造与人工审核工件生成。"""

# 延迟解析类型注解，保持文件规格加载兼容。
from __future__ import annotations

# 标准库负责按真实路径加载拆分后的事实职责模块。
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 报告辅助模块负责缺口汇总与 Markdown 渲染。
from facts_report_support import build_missing_information
from facts_report_support import render_markdown

# 固定事实职责模块目录，避免依赖调用方搜索路径。
PATH_FACT_MODULE_DIR = Path(__file__).resolve().parent  # 事实职责模块目录

# 声明职责模块加载顺序，使跨模块依赖先于使用方完成登记。
TUPLE_FACT_MODULE_NAMES = (  # 固定基础、证据与候选模块的依赖加载顺序
    "readable_patent_facts_io",  # 基础 I/O 与文本统计职责
    "readable_patent_facts_evidence",  # 结构化证据与来源术语职责
    "readable_patent_facts_candidates",  # 候选专利点与人工审核职责
)

# 按同目录真实路径加载职责模块，避免调用方搜索路径影响入口兼容性。
def load_fact_internal_module(str_module_name: str) -> Any:
    """按文件路径加载事实内部模块。

    参数：
    - str_module_name：内部模块的稳定注册名称。

    返回：
    - Any：已经执行并登记的模块对象。

    异常：
    - ImportError：模块文件无法建立加载规格时抛出。
    """

    # 从稳定注册名称还原同目录文件名。
    str_file_stem = str_module_name.removeprefix("readable_patent_")  # 职责模块文件 stem

    # 拼出职责模块真实路径，避免修改 sys.path。
    path_module = PATH_FACT_MODULE_DIR / f"{str_file_stem}.py"  # 职责模块源码路径

    # 读取稳定名称下已登记的模块，判断它是否属于当前技能 root。
    obj_registered_module = sys.modules.get(str_module_name)  # 已登记的同名职责模块

    # 只有真实文件路径一致时才复用模块对象，保持同 root 对象身份。
    if obj_registered_module is not None:

        # 读取已登记模块文件路径；无文件来源的对象不能证明属于当前 root。
        str_registered_file = getattr(obj_registered_module, "__file__", "")  # 已登记模块来源路径

        # 当前路径一致时返回原对象，避免重复初始化模块级常量。
        if str_registered_file and Path(str_registered_file).resolve() == path_module.resolve():

            # 返回当前技能 root 已完成加载的职责模块。
            return obj_registered_module

    # 为当前职责模块创建独立加载规格。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, path_module)  # 职责模块加载规格

    # 加载规格不完整时阻断协调器启动。
    if obj_specification is None or obj_specification.loader is None:

        # 报告真实缺件路径，便于定位不完整技能包。
        raise ImportError(f"> ERR: [Python] 无法加载事实内部模块：{path_module}")

    # 创建模块对象并提前登记，供后续职责模块解析前序依赖。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 待执行职责模块

    # 登记稳定模块名，保持跨模块 import 指向同一对象。
    sys.modules[str_module_name] = obj_module  # 职责模块注册项

    # 执行当前职责模块源码；组事务统一负责所有稳定键的失败回滚。
    obj_specification.loader.exec_module(obj_module)

    # 返回已加载模块供兼容导出收集名称。
    return obj_module

# 以完整稳定键组为事务边界加载全部事实职责模块。
def load_fact_module_group() -> list[Any]:
    """原子加载当前 root 的全部事实职责模块。

    参数：
    - 无。

    返回：
    - `list[Any]`：按依赖顺序完成加载的事实职责模块。

    异常：
    - 任一 helper 加载失败时恢复整组稳定键后原样上抛。
    """

    # 只记录事务开始时真实存在的稳定键及其对象身份。
    dict_original_modules = {  # 事实模块组事务快照
        str_module_name: sys.modules[str_module_name]  # 事务开始前的原模块对象
        for str_module_name in TUPLE_FACT_MODULE_NAMES  # 覆盖完整事实稳定键组
        if str_module_name in sys.modules  # 原先不存在的键不写入快照
    }

    # 顺序加载整组 helper，成功时保留当前 root 的完整模块组。
    try:

        # 返回完整模块列表，供兼容名称收集保持旧覆盖顺序。
        return [
            load_fact_internal_module(str_module_name)  # 当前事实职责模块
            for str_module_name in TUPLE_FACT_MODULE_NAMES  # 固定依赖加载顺序
        ]

    # 任一 helper 失败时必须撤销本轮所有前序稳定键替换。
    except Exception:

        # 按完整稳定键组恢复原对象或删除本轮新增键。
        for str_module_name in TUPLE_FACT_MODULE_NAMES:

            # 原先存在的键恢复为事务开始前的同一对象。
            if str_module_name in dict_original_modules:

                # 恢复事实 helper 的原始注册身份。
                sys.modules[str_module_name] = dict_original_modules[str_module_name]  # 原事实模块对象

            # 原先不存在的键必须删除，避免留下当前 root 的部分模块组。
            else:

                # 清除本轮事务新登记的事实 helper。
                sys.modules.pop(str_module_name, None)

        # 保留真实加载异常和 traceback，供调用方定位具体缺件。
        raise

# 按依赖顺序原子加载全部事实职责模块。
LIST_FACT_MODULES = load_fact_module_group()  # 已加载事实职责模块

# 收集拆分模块的全部非私有名称，完整恢复原入口公共 helper 面。
def collect_fact_compatibility() -> dict[str, Any]:
    """收集事实职责模块的公共兼容名称。

    参数：
    - 无。

    返回：
    - dict[str, Any]：原入口继续暴露的名称与对象。
    """

    # 初始化兼容名称表，后加载模块沿用旧单文件覆盖顺序。
    dict_compatibility: dict[str, Any] = {}  # 事实入口兼容名称表

    # 按依赖顺序扫描已经加载的职责模块。
    for obj_fact_module in LIST_FACT_MODULES:

        # 逐项恢复非私有名称，兼容既有 helper import。
        for str_export_name in dir(obj_fact_module):

            # 私有实现细节不属于原入口公共面。
            if str_export_name.startswith("_"):

                # 跳过内部名称并检查下一个候选。
                continue

            # 读取当前公共名称对应的真实对象。
            obj_export_value = getattr(obj_fact_module, str_export_name)  # 当前兼容导出对象

            # 写入兼容表，保留后加载模块覆盖同名绑定的顺序。
            dict_compatibility[str_export_name] = obj_export_value  # 当前公共名称绑定

    # 返回完整兼容表供协调器一次性恢复。
    return dict_compatibility

# 生成旧入口公共 helper 的兼容绑定表。
DICT_FACT_COMPATIBILITY = collect_fact_compatibility()  # 旧入口公共绑定

# 把受控兼容表合入当前入口模块。
globals().update(DICT_FACT_COMPATIBILITY)

# 这里执行 facts 主流程，并把 Markdown 报告路径写到标准输出末尾。
def main() -> int:
    """
    执行 facts 摘要主流程。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 缺少案件配置、盘点结果或 facts 输出目录写入失败时由底层异常上抛。
    """

    # 这里解析命令行参数，锁定案件目录和本次 facts 汇总的处理上限。
    namespace_arguments = parse_arguments()  # facts 入口参数

    # 这里解析案件目录绝对路径，保证后续读取配置和写结果都指向同一案件目录。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 案件根目录

    # 这里固定案件配置路径，供 facts 入口读取案件名称和默认研究根目录。
    path_case_config = path_case_dir / "case_config.json"  # 案件配置文件路径

    # 这里在缺少案件配置时立即报错，避免 facts 结果失去案件上下文。
    if not path_case_config.exists():

        # 这里抛出明确错误，提醒调用方先完成建案或补齐案件配置。
        raise FileNotFoundError("> ERR: [Python] 缺少 case_config.json，无法生成事实摘要")

    # 这里读取案件配置，供 facts 结果补齐案件名称和研究根目录字段。
    dict_case_config = read_json_file(path_case_config)  # 案件配置字典

    # 这里解析本次 research_root 文本，允许命令行覆盖案件配置里的默认值。
    str_research_root = namespace_arguments.research_root or dict_case_config.get("research_root", ".")  # 研究根目录文本

    # 这里固定盘点 JSON 路径，facts 入口默认直接消费受管盘点结果。
    path_inventory_json = path_case_dir / "01_inventory" / "research_inventory.json"  # 盘点 JSON 路径

    # 这里在缺少盘点结果时立即报错，避免 facts 入口在无输入场景下伪造成功。
    if not path_inventory_json.exists():

        # 这里抛出明确错误，提醒调用方先完成材料盘点步骤。
        raise FileNotFoundError("> ERR: [Python] 缺少 research_inventory.json，请先完成材料盘点")

    # 这里读取盘点结果，作为 facts 入口构造 source 记录和候选专利点的主输入。
    dict_inventory = read_json_file(path_inventory_json)  # 盘点结果字典

    # 这里创建 facts 输出目录，保证 JSON 和 Markdown 都有稳定落点。
    path_output_dir = ensure_dir(path_case_dir / "02_facts")  # facts 输出目录

    # 这里初始化原始 source 记录输入列表，后续只保留可读且非模板的材料记录。
    list_inventory_records = list(dict_inventory.get("files", []))  # 原始盘点记录列表

    # 这里初始化经过筛选的 source 输入记录列表，后续只纳入高价值可读材料。
    list_selected_records: list[dict[str, Any]] = []  # 已筛选的 source 输入记录列表

    # 这里逐个筛选盘点记录，只保留可读且不应跳过的材料进入 facts 汇总。
    for dict_record in list_inventory_records:

        # 这里在材料不可读或明确应跳过时直接略过，避免候选专利点被模板或空壳记录污染。
        if not dict_record.get("readable") or dict_record.get("skip_as_invention"):

            # 这里继续检查下一条盘点记录，把名额留给真实研发材料。
            continue

        # 这里把通过筛选的盘点记录加入 source 输入列表，供后续事实抽取使用。
        list_selected_records.append(dict_record)

        # 这里在达到 source 数量上限时及时停止，避免拉入过多低价值材料。
        if len(list_selected_records) >= namespace_arguments.max_sources:

            # 这里结束 source 记录筛选，保持 facts 结果规模稳定。
            break

    # 这里在筛选后仍无可读材料时立即报错，避免生成没有来源支撑的 facts 结果。
    if not list_selected_records:

        # 这里抛出明确错误，提示调用方补充可读材料或检查盘点结果。
        raise ValueError("> ERR: [Python] 盘点结果中没有可用于事实抽取的材料")

    # 这里逐个构造 source 事实记录，供 candidate point 聚合和 Markdown 渲染复用。
    list_sources = [build_source_record(dict_record) for dict_record in list_selected_records]  # source 事实记录列表

    # 这里根据 source 记录聚合候选专利点，形成事实摘要的核心结果。
    list_candidate_points = build_candidate_points(list_sources)  # 聚合后的候选专利点主视图

    # 这里初始化 prior-art 说明列表，后续按 source 展开对比线索。
    list_prior_art_notes = []  # prior-art 摘要列表

    # 这里逐个 source 展开 prior-art 线索，方便报告回看对比依据。
    for dict_source in list_sources:

        # 这里逐条写入当前 source 的 prior-art 摘要，保留来源语义。
        for dict_evidence in dict_source.get("prior_art_evidence", [])[:4]:

            # 这里把当前线索压成单行摘要，直接显示来源与结论。
            list_prior_art_notes.append(f"{dict_source['path']}: {dict_evidence['text']}")

    # 这里初始化全局术语片段列表，后续把候选点和 source 术语统一压平。
    list_terms_fragments = []  # 全局术语片段列表

    # 这里先追加候选点名称，保留主案命名和创新点标签。
    list_terms_fragments.extend(dict_point["name"] for dict_point in list_candidate_points)

    # 这里继续追加问题描述，避免问题导向术语被漏掉。
    list_terms_fragments.extend(dict_point["problem"] for dict_point in list_candidate_points)

    # 这里继续追加方案描述，让词频更贴近真实方案表达。
    list_terms_fragments.extend(dict_point["solution"] for dict_point in list_candidate_points)

    # 这里继续追加效果描述，让收益和性能类术语进入全局词频。
    for dict_point in list_candidate_points:

        # 这里逐条追加当前候选点的效果描述，保留收益类术语。
        for str_effect in dict_point["effects"]:

            # 这里写入当前效果片段，让收益术语进入统计输入。
            list_terms_fragments.append(str_effect)

    # 这里最后追加各个 source 的技术术语，补足候选点之外的领域词。
    for dict_source in list_sources:

        # 这里逐条追加当前 source 的技术术语，补齐领域词汇。
        for str_term in dict_source.get("technical_terms", []):

            # 这里写入当前 source 的术语片段，补足聚合摘要之外的词汇。
            list_terms_fragments.append(str_term)

    # 这里把全局术语片段压成统一词频输入，供项目级主题词统计继续复用。
    str_terms_source = "\n".join(list_terms_fragments)  # 全局技术术语统计输入文本

    # 这里统计全局技术术语，供 facts JSON 和 Markdown 报告展示项目级技术主题。
    list_global_terms = [str_term for str_term, _ in keyword_counter(str_terms_source, int_limit=80)]  # 全局技术术语列表

    # 这里把候选点缺口和 prior-art 线索残缺度转成待补料清单，供后续人工补齐。
    list_missing_information = build_missing_information(list_candidate_points, list_prior_art_notes)  # 缺失信息提示列表

    # 这里组装最终 facts 数据字典，供 JSON 落盘和 Markdown 渲染共同复用。
    dict_facts = {  # 最终 facts 数据字典
        "case_name": str(dict_case_config.get("case_name", path_case_dir.name)),  # 案件名称文本
        "research_root": str(Path(str_research_root).resolve()),  # 研究根目录绝对路径文本
        "generated_at": iso_now(),  # facts 生成时间戳
        "sources": list_sources,  # 当前案件的 source 事实记录列表
        "candidate_invention_points": list_candidate_points,  # 供后续主案选择使用的候选专利点列表
        "prior_art_notes": list_prior_art_notes[:40],  # 供人工审阅的 prior-art 摘要线索列表
        "technical_terms": list_global_terms,  # 汇总后的全局技术术语列表
        "missing_information": list_missing_information,  # 后续仍需补料的缺失信息提示列表
    }

    # 这里固定 facts JSON 输出路径，供后续候选点选择和正文起草步骤继续读取。
    path_facts_json = path_output_dir / "research_facts.json"  # facts JSON 输出路径

    # 这里固定人工审阅版 Markdown 路径，方便与 JSON 机器结果形成一对输出件。
    path_facts_markdown = path_output_dir / "research_facts.md"  # 人工审阅版 facts Markdown 路径

    # 这里把结构化 facts 数据写成 JSON 文件，作为后续步骤的稳定机器输入。
    write_json_file(path_facts_json, dict_facts)

    # 把候选点转换为内容绑定的审核工件，禁止直接流入正文。
    list_review_candidates = build_review_candidates(list_candidate_points)  # 当前候选审核数组

    # 固定审核候选路径，供人工决定和预览门禁读取同一份候选。
    path_review_candidates = path_output_dir / "review_candidates.json"  # 审核候选工件路径

    # 写入当前候选集合；材料变化后指纹会随载荷同步变化。
    write_json_file(path_review_candidates, list_review_candidates)

    # 固定人工决定路径，使决定与草稿阶段同域管理。
    path_review_decisions = path_case_dir / "03_drafts" / "review_decisions.json"  # 人工决定工件路径

    # 首次生成 pending 决定，并保留任何已存在的人工审核结果。
    ensure_initial_review_decisions(path_review_decisions, list_review_candidates)

    # 这里渲染 facts Markdown 文本，供人工快速审阅候选专利点和待补信息。
    str_facts_markdown = render_markdown(dict_facts)  # 待写入案件目录的 facts Markdown 报告文本

    # 这里把 facts Markdown 报告写入案件目录，方便人工继续阅读和确认。
    write_text_file(path_facts_markdown, str_facts_markdown)

    # 这里把 Markdown 报告路径作为机器可读输出写给上游流程。
    sys.stdout.write(str(path_facts_markdown.resolve()) + "\n")

    # 这里返回成功状态码，表示 facts 摘要已经完成并写入案件目录。
    return 0

# 这里保留标准脚本入口，方便命令行和流水线子进程统一调用 facts 入口。
if __name__ == "__main__":

    # 这里通过标准退出路径返回状态码，保持命令行调用行为一致。
    raise SystemExit(main())
