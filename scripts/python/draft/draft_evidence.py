"""构建交底书证据映射与结构化合同工件。"""

# 延迟解析证据结构中的类型注解，保持运行时兼容。
from __future__ import annotations

# 标准库负责哈希、模块加载、路径与动态载荷类型。
import hashlib
import importlib.util
from pathlib import Path
from typing import Any

# 证据记录复用内容模块的关键词提取规则。
from readable_patent_draft_content import collect_evidence_keywords

# 固定事实完整性合同路径，确保审核决定沿用正式规则。
PATH_FACT_INTEGRITY_CONTRACT = Path(__file__).resolve().parents[1] / "support" / "fact_integrity_contract.py"  # 事实完整性合同路径

# 固定最终模板路径，供起草合同记录可追溯模板哈希。
PATH_TEMPLATE_DOCX = Path(__file__).resolve().parents[3] / "assets" / "cn_technical_disclosure_template.docx"  # 正式 DOCX 模板路径

# 加载候选审核和数据白名单使用的事实完整性合同。
def load_fact_integrity_contract_module() -> Any:
    """加载事实完整性合同模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行源码的事实完整性模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 使用起草专用模块名绑定正式事实合同源码。
    obj_specification = importlib.util.spec_from_file_location(  # 事实完整性模块加载规格
        "readable_patent_fact_integrity_contract",  # 起草进程内隔离模块名
        PATH_FACT_INTEGRITY_CONTRACT,  # 正式事实合同源码路径
    )

    # 无法加载事实规则时禁止继续构造版本三模型。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出稳定错误，提醒修复正式事实合同。
        raise ImportError("> ERR: [Python] 无法加载 support/fact_integrity_contract.py。")

    # 根据已验证规格创建事实合同模块对象。
    module_contract = importlib.util.module_from_spec(obj_specification)  # 事实完整性模块对象

    # 执行正式源码，使起草与自检共享数据批准规则。
    obj_specification.loader.exec_module(module_contract)

    # 返回已经初始化的事实合同模块。
    return module_contract

# 构造保留公开时序和明确用途的现有技术证据记录。
def build_prior_evidence_record(
    dict_prior_record: dict[str, Any],
    str_summary: str,
    int_index: int,
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> dict[str, Any]:
    """构造版本三现有技术证据记录。

    参数：
    - `dict_prior_record`：人工核验的现有技术记录。
    - `str_summary`：正文使用的受控摘要。
    - `int_index`：当前记录的一基引用顺序。
    - `module_runtime_support`：共享文本清洗模块。
    - `module_quality_contract`：证据关键词提取合同。

    返回：
    - `dict[str, Any]`：可供文献时序门禁消费的证据记录。

    异常：
    - 无。
    """

    # 读取人工声明用途，缺失时只允许作为背景说明。
    obj_uses = dict_prior_record.get("uses", ["background_only"])  # 当前文献用途原始值

    # 非数组用途不能扩大解释，统一降为背景说明。
    list_uses = list(obj_uses) if isinstance(obj_uses, list) else ["background_only"]  # 当前文献明确用途

    # 返回正文证据字段及时间用途字段，禁止在模型阶段补猜日期。
    return {
        "id": f"E-PRIOR-{int_index}",  # 现有技术证据编号
        "kind": "prior_art",  # 现有技术证据类型
        "text": module_runtime_support.clean_text(str_summary),  # 正文使用的受控摘要
        "keywords": collect_evidence_keywords(str_summary, module_quality_contract),  # 摘要关键词
        "publication_date": str(dict_prior_record.get("publication_date", "")),  # 人工核验公开日
        "reference_date": str(dict_prior_record.get("reference_date", "")),  # 本案现有技术参考日
        "uses": list_uses,  # 人工明确声明的文献用途
    }

# 把同类主案事实登记为稳定证据记录。
def append_selected_evidence_records(
    list_evidence_index: list[dict[str, Any]],
    list_items: list[dict[str, Any]],
    str_identifier_prefix: str,
    str_evidence_kind: str,
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> None:
    """清洗并追加一类主案事实证据。

    参数：
    - `list_evidence_index`：待追加的证据索引列表。
    - `list_items`：当前类别的原始事实列表。
    - `str_identifier_prefix`：当前类别的证据编号前缀。
    - `str_evidence_kind`：当前证据类别名称。
    - `module_runtime_support`：共享文本清洗模块。
    - `module_quality_contract`：证据关键词提取合同。

    返回：
    - `None`。
    """

    # 逐项登记当前类别事实，保持输入顺序和一基编号稳定。
    for int_index, dict_item in enumerate(list_items, start=1):

        # 清洗当前事实文本，空文本不能进入来源映射。
        str_evidence_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前证据文本

        # 仅登记存在有效文本的事实记录。
        if str_evidence_text:

            # 保存稳定编号、类别、正文与关键词，供后续章节回溯。
            list_evidence_index.append(
                {
                    "id": f"E-{str_identifier_prefix}-{int_index}",  # 当前证据稳定编号
                    "kind": str_evidence_kind,  # 当前证据类别
                    "text": str_evidence_text,  # 清洗后的证据正文
                    "keywords": collect_evidence_keywords(str_evidence_text, module_quality_contract),
                }
            )

# 生成 review 与 claims 可复用的轻量来源映射，避免正文关键特征脱离真实材料。
def build_evidence_map(
    path_case_dir: Path,
    list_steps: list[dict[str, Any]],

    # 主案事实与现有技术事实分别承担发明证据和背景证据来源。
    dict_selected: dict[str, Any],
    list_prior_summaries: list[str],
    list_prior_records: list[dict[str, Any]],

    # 两个共享模块分别负责文本处理和证据映射规则。
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> dict[str, Any]:
    """生成来源证据映射。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `list_steps`：结构化方法步骤列表。
    - `dict_selected`：当前主案选择结果字典。
    - `list_prior_summaries`：最接近现有技术摘要列表。
    - `list_prior_records`：保留公开时序与用途的人工核验记录。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

    返回：
    - `dict[str, Any]`：已经写回 `latest_evidence_map.json` 的结构化映射字典。

    异常：
    - JSON 写入失败时由底层异常上抛。
    """

    # 先准备证据索引列表，后续逐批登记问题、方案、效果和现有技术来源。
    list_evidence_index: list[dict[str, Any]] = []  # 证据索引列表

    # 按问题、方案、效果的原顺序登记三类主案事实。
    for str_source_key, str_identifier_prefix, str_evidence_kind in (
        ("technical_problem_evidence", "PROB", "problem"),
        ("technical_solution_evidence", "SOL", "solution"),
        ("technical_effect_evidence", "EFF", "effect"),
    ):

        # 复用同一清洗与编号规则，避免三类证据产生语义漂移。
        append_selected_evidence_records(
            list_evidence_index,  # 当前案件证据索引
            dict_selected.get(str_source_key, []),  # 当前类别原始事实
            str_identifier_prefix,  # 当前类别编号前缀
            str_evidence_kind,  # 本轮主案事实类别名称
            module_runtime_support,  # 文本清洗支持模块
            module_quality_contract,  # 证据关键词合同
        )

    # 逐项登记最接近现有技术摘要，补齐背景技术对比来源索引。
    for int_index, str_summary in enumerate(list_prior_summaries, start=1):

        # 按同一顺序读取人工核验记录；缺失时保持空字段而不猜测时序。
        dict_prior_record = (  # 当前摘要对应的核验记录
            list_prior_records[int_index - 1]  # 与摘要共用的一基顺序
            if int_index <= len(list_prior_records)  # 当前索引存在核验记录
            else {}  # 缺失记录时保留空事实边界
        )

        # 把摘要及其公开时序和用途登记到证据索引。
        list_evidence_index.append(
            build_prior_evidence_record(
                dict_prior_record,  # 当前人工核验记录
                str_summary,  # 正文使用的现有技术摘要
                int_index,  # 当前引用顺序

                # 共享模块保持摘要清洗和关键词生成与其他证据类型一致。
                module_runtime_support,  # 现有技术摘要清洗模块
                module_quality_contract,  # 现有技术关键词提取合同
            )
        )

    # 由质量合同按关键词构建步骤到证据的最小映射，禁止把全部证据泛挂到每一步。
    list_features = module_quality_contract.build_step_support_map(list_steps, list_evidence_index)  # 精确步骤证据映射

    # 组装最终来源证据映射字典，供 review 和 claims 阶段共同复用。
    dict_evidence_map = {  # 最终来源证据映射字典
        "generated_at": module_runtime_support.iso_now(),  # 来源映射生成时间
        "case_dir": str(path_case_dir.resolve()),  # 当前案件目录绝对路径文本
        "evidence_index": list_evidence_index,  # 来源证据索引列表
        "features": list_features,  # 正文特征到来源编号的映射列表
    }

    # 把最新证据映射写回案件目录，供权利要求、自检和导出阶段统一读取。
    module_runtime_support.write_json_file(path_case_dir / "03_drafts" / "latest_evidence_map.json", dict_evidence_map)

    # 返回已经落盘的来源证据映射字典，便于当前正文阶段继续复用。
    return dict_evidence_map

# 写入起草计划、槽位正文和哈希状态，锁定预览确认边界。
def write_draft_contract_artifacts(
    path_output_dir: Path,
    str_markdown: str,
    dict_artifact_context: dict[str, Any],
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> None:
    """写入起草计划、槽位正文和预览哈希，锁定确认后的生成边界。

    参数：
    - `path_output_dir`：草稿输出目录。
    - `str_markdown`：已生成的主交底书 Markdown。
    - `dict_artifact_context`：标题、步骤、模块和效果组成的合同上下文。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

    返回：
    - `None`。

    异常：
    - 状态文件或 JSON 写入失败时由底层异常上抛。
    """

    # 从合同上下文解出各槽位数据，保持函数参数数量和写入边界清晰。
    str_title = str(dict_artifact_context["title"])  # 正式发明标题

    # 复制步骤列表，避免写入阶段修改主流程持有的原始对象。
    list_steps = list(dict_artifact_context["steps"])  # 结构化方法步骤列表

    # 复制模块列表，保持装置槽位数据在写入期间稳定。
    list_modules = list(dict_artifact_context["modules"])  # 结构化模块列表

    # 复制技术效果列表，保持质量分类结果不被合同装配修改。
    list_effects = list(dict_artifact_context["effects"])  # 已分类技术效果列表

    # 仅登记不引入新事实的结构性连接补写，供预览阶段显式确认。
    list_inference_candidates = ["将前一处理步骤的输出作为下一处理步骤的输入。"]  # 受控推断候选列表

    # 根据标题、步骤和推断候选生成可追踪的代理起草计划。
    dict_draft_plan = module_quality_contract.build_draft_plan(  # 代理起草计划与推断清单
        str_title,  # 起草计划使用的发明名称
        list_steps,  # 起草计划覆盖的方法步骤
        list_inference_candidates,  # 待确认的结构性推断候选
    )

    # 将正文结构整理为与模板槽位一一对应的机器可读合同。
    dict_draft_content = {  # 与最终模板槽位对应的正文内容
        "title": str_title,  # 发明名称槽位内容
        "template_slots": {"一、发明名称": str_title},  # 模板标题槽位映射
        "method_steps": list_steps,  # 方法方案槽位内容
        "modules": list_modules,  # 装置模块槽位内容
        "effects": list_effects,  # 技术效果槽位内容
    }

    # 分别计算正文和模板哈希，用于阻止确认后的内容或模板静默漂移。
    str_draft_hash = hashlib.sha256(str_markdown.encode("utf-8")).hexdigest()  # 主正文内容哈希

    # 单独计算模板哈希，使模板变更也会触发重新确认。
    str_template_hash = hashlib.sha256(PATH_TEMPLATE_DOCX.read_bytes()).hexdigest()  # 模板内容哈希

    # 读取现有预览状态，保留人工确认标记并更新当前生成资格。
    path_preview_status = path_output_dir / "preview_status.json"  # 预览确认状态路径

    # 从稳定路径加载当前预览状态，随后仅更新本轮生成字段。
    dict_preview_status = module_runtime_support.read_json_file(path_preview_status)  # 当前预览确认状态

    # 只收集质量合同允许的推断编号，禁止被拒绝项进入确认范围。
    list_inference_ids = [  # 已登记推断编号列表
        str(dict_item["id"])  # 当前允许推断项的稳定编号
        for dict_item in dict_draft_plan["inferences"]  # 扫描计划登记的推断对象
        if dict_item["allowed"]  # 只暴露允许进入确认边界的推断
    ]

    # 把本轮哈希、推断边界和起草状态原子更新到预览状态对象。
    dict_preview_status.update(
        {
            "draft_hash": str_draft_hash,
            "template_hash": str_template_hash,
            "inference_ids": list_inference_ids,
            "inferences_confirmed": bool(dict_preview_status.get("confirmed")),
            "authoring_status": (
                "authoring_required"
                if not dict_preview_status.get("confirmed")
                else "ready_for_export"
            ),
        }
    )

    # 分别写出起草计划、槽位正文和预览状态，供后续验证与导出消费。
    module_runtime_support.write_json_file(path_output_dir / "draft_plan.json", dict_draft_plan)

    # 写出与模板槽位对应的正文合同，供 DOCX 装配器直接消费。
    module_runtime_support.write_json_file(path_output_dir / "draft_content.json", dict_draft_content)

    # 最后写出预览状态，使哈希和推断确认结果保持一致。
    module_runtime_support.write_json_file(path_preview_status, dict_preview_status)

# 读取人工审核工件并构造获批数据与来源登记表。
def load_approved_review_registries(
    path_case_dir: Path,
    module_runtime_support: Any,
) -> dict[str, list[dict[str, Any]]]:
    """加载审核工件并生成指纹有效的获批登记表。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `module_runtime_support`：共享 JSON 读取模块。

    返回：
    - `dict[str, list[dict[str, Any]]]`：数据登记表和来源清单映射。
    """

    # 定位候选与人工决定工件，缺失时保持空数组供模型门禁阻断。
    path_review_candidates = path_case_dir / "02_facts" / "review_candidates.json"  # 审核候选工件路径

    # 人工决定保存在草稿阶段目录，与候选事实分离受管。
    path_review_decisions = path_case_dir / "03_drafts" / "review_decisions.json"  # 人工决定工件路径

    # 仅在候选工件存在时读取，禁止起草阶段伪造候选。
    list_review_candidates = (  # 当前审核候选数组
        module_runtime_support.read_json_file(path_review_candidates)  # 已落盘的内容绑定候选
        if path_review_candidates.exists()  # 仅在 facts 已生成候选时读取
        else []  # 缺失时保持空候选边界
    )

    # 仅在决定工件存在时读取，禁止起草器自动接受候选。
    list_review_decisions = (  # 当前人工决定数组
        module_runtime_support.read_json_file(path_review_decisions)  # 已落盘的人工决定
        if path_review_decisions.exists()  # 仅在人工审核工件存在时读取
        else []  # 缺失时保持未批准状态
    )

    # 使用同源事实合同过滤类型、决定和内容指纹。
    module_fact_contract = load_fact_integrity_contract_module()  # 事实完整性合同模块

    # 分别生成获批数据白名单与来源清单，保持两类事实边界独立。
    list_data_registry = module_fact_contract.build_approved_data_registry(  # 已批准数据登记表
        list_review_candidates,  # 当前内容绑定候选
        list_review_decisions,  # 当前人工审核决定
    )

    # 来源清单保留获批原文，供后续章节重合检查。
    list_source_manifest = module_fact_contract.build_approved_source_manifest(  # 已批准来源登记表
        list_review_candidates,  # 用于来源筛选的候选
        list_review_decisions,  # 用于指纹核验的人工决定
    )

    # 按稳定键返回两个登记表，避免多值赋值破坏命名类型约定。
    return {
        "data_registry": list_data_registry,  # 获批量化事实白名单
        "source_manifest": list_source_manifest,  # 获批事实来源清单
    }

# 为章节绑定正文真实包含的获批数据编号。
def attach_approved_data_ids(
    list_section_records: list[dict[str, Any]],
    list_data_registry: list[dict[str, Any]],
) -> None:
    """把正文实际包含的获批数据编号登记到章节。

    参数：
    - `list_section_records`：待更新的结构化章节记录。
    - `list_data_registry`：内容指纹有效的获批数据登记表。

    返回：
    - `None`。
    """

    # 逐章执行获批原句精确包含判断。
    for dict_section in list_section_records:

        # 读取当前章节正文，避免仅凭候选来源进行泛绑定。
        str_section_content = str(dict_section.get("content", ""))  # 当前章节正文

        # 仅把正文真实包含的批准数据编号写入章节。
        dict_section["data_ids"] = [
            str(dict_record["data_id"])  # 当前章节引用的正式数据编号
            for dict_record in list_data_registry  # 遍历全部获批数据记录
            if str(dict_record["text"]) in str_section_content  # 要求获批原句真实出现
        ]  # 当前章节数据引用闭包

# 从起草上下文生成术语登记表。
def build_term_registry(dict_context: dict[str, Any]) -> list[dict[str, Any]]:
    """按正文术语顺序生成稳定术语登记表。

    参数：
    - `dict_context`：包含正文术语数组的起草上下文。

    返回：
    - `list[dict[str, Any]]`：带稳定编号的术语登记表。
    """

    # 按正文实际使用顺序分配一基稳定编号。
    return [
        {
            "term_id": f"T{int_index:03d}",  # 正式术语编号
            "canonical": str(str_term),  # 当前术语规范名称
            "aliases": [],  # 尚未声明其他允许别名
        }
        for int_index, str_term in enumerate(  # 按正文术语顺序分配稳定编号
            dict_context.get("terms", []),  # 当前起草上下文术语
            start=1,  # 术语编号从一开始
        )
    ]

# 构建并写出版本二结构化交底模型。
def write_structured_disclosure_model(
    path_case_dir: Path,
    dict_model_payload: dict[str, Any],
    module_runtime_support: Any,
    module_disclosure_model: Any,
    module_quality_contract: Any,
) -> None:
    """把正文上下文、公式事实和证据映射写成版本三模型。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `dict_model_payload`：公式块、证据映射和章节上下文。
    - `module_runtime_support`：共享 JSON 写入模块。
    - `module_disclosure_model`：版本三模型构建模块。
    - `module_quality_contract`：证据映射使用的正文质量合同模块。

    返回：
    - `None`。

    异常：
    - 公式事实或章节合同损坏时由模型模块异常上抛。
    """

    # 先写出最新证据映射，使事实报告和版本三模型共享同一来源编号。
    dict_evidence_map = build_evidence_map(  # 正文与结构化模型共享的来源映射
        path_case_dir,  # 审核工件所在案件目录
        dict_model_payload["context"]["steps"],  # 已生成的方法步骤
        dict_model_payload["selected"],  # 当前主案事实
        dict_model_payload["context"]["prior_summaries"],  # 背景章节使用的查新摘要
        dict_model_payload["context"]["prior_records"],  # 背景文献公开时序和明确用途
        module_runtime_support,  # JSON 与文本支持模块
        module_quality_contract,  # 精确步骤证据映射规则
    )

    # 从研究根目录读取人工确认公式事实；缺失语义不会在生成阶段被猜测。
    list_confirmed_formula_facts = module_disclosure_model.load_confirmed_formula_facts(path_case_dir)  # 人工确认公式事实

    # 逐条匹配正文展示公式，未匹配记录将在后续语义验证中形成 blocker。
    list_formula_records = module_disclosure_model.match_formula_records(  # 与正文公式一一对应的登记表
        dict_model_payload["formula_blocks"],  # 正文实际使用的展示公式
        list_confirmed_formula_facts,  # 本地材料提供的确认语义
    )

    # 按正式章节合同生成十一项叶子章节。
    list_section_records = module_disclosure_model.build_section_records(  # 十一项章节记录
        dict_model_payload["context"],  # 标题、问题、步骤、模块和效果
        dict_evidence_map,  # 当前案件真实来源映射
    )

    # 加载人工审核结果，生成内容指纹有效的数据和来源登记表。
    dict_review_registries = load_approved_review_registries(  # 获批审核登记表映射
        path_case_dir,  # 当前案件根目录
        module_runtime_support,  # JSON 读取支持模块
    )

    # 为每个章节绑定正文实际包含的获批数据编号。
    attach_approved_data_ids(list_section_records, dict_review_registries["data_registry"])

    # 从起草上下文生成术语登记表，保留正文实际使用顺序。
    list_term_registry = build_term_registry(dict_model_payload["context"])  # 版本三术语登记表

    # 汇总当前起草阶段可以确定的版本三附加登记表。
    dict_registries = {
        "source_manifest": dict_review_registries["source_manifest"],  # 已接受候选来源登记表
        "data_registry": dict_review_registries["data_registry"],  # 章节允许引用的数据记录
        "term_registry": list_term_registry,  # 正文术语规范名称
        "figure_registry": [],  # 附图阶段完成后由专用入口补齐
        "cross_references": [],  # 当前生成器尚未声明显式章节引用
        "pending_items": [],  # 预览审核已关闭后进入正式起草
        "feature_registry": module_disclosure_model.build_feature_registry(  # 正文真实特征及证据身份
            dict_evidence_map,  # 正文阶段形成的特征证据映射
            list_section_records,  # 实际章节记录用于建立章节证据闭包
        ),
        "rule_applicability": {"ai_applicability": "pending"},  # Task 2 前保持待人工判定
    }  # 版本三模型附加事实域

    # 将 evidence_index 映射为验证器消费的正式 evidence_registry。
    dict_normalized_evidence_map = module_disclosure_model.normalize_evidence_map(  # 版本三证据登记表
        dict_evidence_map  # 旧版 evidence_index 来源对象
    )

    # 组合章节、公式与证据三个事实域，并为公式添加稳定内容哈希。
    dict_disclosure_model = module_disclosure_model.build_disclosure_model(  # 完整结构化交底模型
        list_section_records,  # 十一项章节事实
        list_formula_records,  # 与正文展示公式一致的语义登记
        dict_normalized_evidence_map,  # 含正式 records 的来源映射
        dict_registries,  # 来源、数据、术语及其他版本三登记表
    )

    # 固定写入验证器约定路径，使旧案件必须重新生成版本三模型。
    module_runtime_support.write_json_file(
        path_case_dir / "03_drafts" / "latest_disclosure_model.json",
        dict_disclosure_model,
    )
