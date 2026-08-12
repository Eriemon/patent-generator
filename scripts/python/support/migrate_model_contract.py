#!/usr/bin/env python3
"""显式把 Model 3.0 转换为仍待特征映射和审查的 Model 4.0。"""

# 延迟解析类型注解，保持技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库负责参数解析、摘要计算、JSON 处理和原子文件发布。
import argparse
import hashlib
import importlib.util
import json

# 文件系统模块负责兼容入口和临时发布。
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

# Claims 2 到 3 只允许这些字段进入正式 claim。
SET_CLAIM_KEYS = {
    "claim_no",  # 权利要求编号
    "claim_type",  # 权利要求类型
    "mapped_steps",  # 旧步骤映射
    "support_ids",  # 旧证据引用
    "unsupported_features",  # 旧版明确缺口文本
    "feature",  # 旧版单特征文本
}  # Claims 3 正式字段白名单

# Claims 3 省略候选只允许基础类型和原因进入正式合同。
SET_OMITTED_KEYS = {"claim_type", "reason"}  # Claims 3 omitted candidate 基础字段

# 双输出事务实现由迁移和映射入口共享。
PATH_ATOMIC_PAIR = Path(__file__).resolve().with_name("atomic_json_pair.py")  # 双 JSON 事务模块

# 正式验证器在写入前检查完整 Model 和 Claims schema。
PATH_VALIDATOR = Path(__file__).resolve().parents[1] / "review" / "structured_contract_validator.py"  # 结构验证器

# 从共享模块加载 JSON 事务实现。
def load_atomic_module() -> Any:
    """加载唯一批次事务模块。

    参数：
    - 无。

    返回：
    - `Any`：已执行的 JSON 批次事务模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 固定文件位置确保迁移和 mapping 共享同一事务语义。
    obj_specification = importlib.util.spec_from_file_location(  # 当前批次事务模块规格
        "patent_atomic_json_pair",  # 隔离动态模块名称
        PATH_ATOMIC_PAIR,  # 受管事务实现的固定路径
    )

    # 缺少正式实现时禁止退回顺序写入。
    if obj_specification is None or obj_specification.loader is None:

        # 三工件无法证明原子性时失败关闭。
        raise ImportError("> ERR: [Python] 无法加载 JSON 批次事务模块。")

    # 创建本次调用独享的事务模块对象。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 当前事务模块对象

    # 执行正式实现后才允许调用批次发布 API。
    obj_specification.loader.exec_module(obj_module)

    # 返回迁移与测试共同复用的事务模块。
    return obj_module

# 从共享模块加载双 JSON 事务函数。
def write_json_pair_atomic(
    path_first: Path,
    dict_first: dict[str, Any],
    path_second: Path,
    dict_second: dict[str, Any],
) -> None:
    """调用共享实现事务发布两个 JSON 工件。

    参数：
    - `path_first`：第一份输出路径。
    - `dict_first`：第一份 JSON 对象。
    - `path_second`：第二份输出路径。
    - `dict_second`：第二份 JSON 对象。

    返回：
    - `None`：两份输出均已发布。

    异常：
    - 共享模块加载或事务发布错误由底层实现上抛。
    """

    # 兼容包装器只转交参数，不复制 staging 或回滚规则。
    load_atomic_module().write_json_pair_atomic(
        path_first,
        dict_first,
        path_second,
        dict_second,
    )

# 使用正式验证器检查两个迁移候选的完整 schema。
def validate_pair_schemas(
    dict_model: dict[str, Any],
    dict_claims: dict[str, Any],
) -> None:
    """在事务发布前验证 Model 4 和 Claims 3 schema。

    参数：
    - `dict_model`：待发布 Model 4。
    - `dict_claims`：待发布 Claims Map 3。

    返回：
    - `None`：两个候选均无 schema finding。

    异常：
    - `ValueError`：任一候选不符合完整 schema 时抛出。
    """

    # 从正式路径加载统一结构验证器。
    obj_specification = importlib.util.spec_from_file_location("patent_migration_validator", PATH_VALIDATOR)  # 验证器规格

    # 缺少验证器时禁止发布未证明工件。
    if obj_specification is None or obj_specification.loader is None:

        # 迁移发布必须依赖正式 schema。
        raise ImportError("> ERR: [Python] 无法加载 Model 4 结构验证器。")

    # 执行验证器源码并调用公开 schema API。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 当前验证器模块

    # 加载正式 schema 规则。
    obj_specification.loader.exec_module(obj_module)

    # Model 4 候选必须完整通过 disclosure schema。
    list_model_findings = obj_module.validate_model_schema(dict_model)  # 主模型结构问题

    # Claims 验证返回业务 findings，本阶段只阻断 schema 代码。
    list_claims_findings = obj_module.validate_claims_map(dict_claims, dict_model)  # 权利要求完整验证问题

    # 只提取 Claims schema 错误，pending 业务状态允许后续映射。
    list_schema_claims = [
        dict_item  # 保留当前结构问题
        for dict_item in list_claims_findings  # 遍历权利要求完整问题
        if dict_item.get("code") == "CLM_SCHEMA"  # 只阻断结构代码
    ]  # 权利要求结构问题

    # 任一 schema 问题都必须发生在两个输出可见之前。
    if list_model_findings or list_schema_claims:

        # 汇总稳定错误代码供调用方定位。
        list_codes = [
            str(dict_item.get("code", ""))  # 规范化当前错误代码
            for dict_item in [*list_model_findings, *list_schema_claims]  # 合并两个候选问题
        ]  # 当前迁移 schema 错误代码

        # 迁移器不得发布只通过局部结构的工件。
        raise ValueError(f"> ERR: [Python] 迁移候选 schema 无效:{','.join(list_codes)}")

# 固定从旧模型保留到新模型的事实域，避免迁移器猜测新增语义。
TUPLE_PRESERVED_KEYS = (
    "source_manifest",  # 旧模型材料来源登记表
    "evidence_registry",  # 旧模型证据登记表
    "data_registry",  # 旧模型受管事实登记表
    "formula_registry",  # 旧模型公式登记表
    "term_registry",  # 旧模型术语登记表
    "figure_registry",  # 旧模型附图登记表
    "sections",  # 旧模型章节事实
    "cross_references",  # 旧模型章节引用
    "pending_items",  # 旧模型人工待办
)  # 可直接保留的旧模型字段

# 固定迁移 CLI 的诊断流编码，避免 Windows 本地代码页破坏协议。
def configure_utf8_text_streams() -> None:
    """把可重配置的标准流固定为 UTF-8。

    参数：
    - 无。

    返回：
    - `None`：可用标准流已经重配置。

    异常：
    - 无。
    """

    # stdout 与 stderr 使用同一协议编码。
    for obj_stream in (sys.stdout, sys.stderr):

        # 测试替身可能没有 reconfigure，需安全探测。
        obj_reconfigure = getattr(obj_stream, "reconfigure", None)  # 当前流重配置函数

        # 真实文本流支持时固定 UTF-8。
        if callable(obj_reconfigure):

            # 避免中文路径和错误消息被本地代码页破坏。
            obj_reconfigure(encoding="utf-8")

# 读取 JSON 对象，同时保留文件原始字节供迁移审计。
def read_json_object(path_file: Path) -> tuple[dict[str, Any], bytes]:
    """读取 JSON 对象并保留原始字节。

    参数：
    - `path_file`：待读取的 JSON 文件路径。

    返回：
    - `tuple[dict[str, Any], bytes]`：解析对象与完全相同的文件字节。

    异常：
    - `UnicodeDecodeError`：输入不是 UTF-8 时抛出。
    - `json.JSONDecodeError`：输入不是合法 JSON 时抛出。
    - `ValueError`：JSON 顶层不是对象时抛出。
    """

    # 直接读取原始字节，禁止换行规范化改变审计摘要。
    bytes_content = path_file.read_bytes()  # 当前迁移输入原始字节

    # 使用 UTF-8 解码并解析 JSON，保留解析异常的真实位置。
    obj_value = json.loads(bytes_content.decode("utf-8"))  # 当前迁移输入 JSON 值

    # 顶层数组或标量无法表达版本化模型合同。
    if not isinstance(obj_value, dict):

        # 抛出包含输入路径的明确结构错误。
        raise ValueError(f"> ERR: [Python] JSON 顶层必须为对象:{path_file}")

    # 返回解析对象和未经修改的原始字节。
    return obj_value, bytes_content

# 原子发布临时文件，并在目标已存在时保持目标内容不变。
def publish_no_clobber(path_temp: Path, path_output: Path) -> None:
    """原子发布迁移临时文件。

    参数：
    - `path_temp`：已经完整写入并刷盘的同目录临时文件。
    - `path_output`：不得覆盖的最终输出路径。

    返回：
    - `None`：硬链接发布成功。

    异常：
    - `FileExistsError`：最终输出已经存在时抛出。
    - `OSError`：底层原子链接失败时抛出。
    """

    # 使用硬链接的原子创建语义消除 exists-check 与 replace 之间的竞争窗口。
    try:

        # 只有目标此前不存在时，链接创建才会成功。
        os.link(path_temp, path_output)

    # 竞争方先创建目标时转成项目统一错误消息。
    except FileExistsError:

        # 保持竞争方字节不变并报告明确拒绝覆盖。
        raise FileExistsError(f"> ERR: [Python] 输出已存在，拒绝覆盖:{path_output}") from None

# 先在同目录完整写入临时文件，再执行原子无覆盖发布。
def write_json_atomic(path_output: Path, dict_model: dict[str, Any]) -> None:
    """原子且无覆盖地写出迁移模型。

    参数：
    - `path_output`：最终迁移模型路径。
    - `dict_model`：待序列化的 Model 4.0 对象。

    返回：
    - `None`：完整模型成功发布。

    异常：
    - `FileExistsError`：输出已经存在或发生竞争创建时抛出。
    - `OSError`：目录、写入、刷盘或发布失败时抛出。
    """

    # 确保输出父目录存在，临时文件和最终文件保持同一文件系统。
    path_output.parent.mkdir(parents=True, exist_ok=True)

    # 固定缩进、UTF-8 和末尾换行，便于人工审阅与重复比较。
    str_text = json.dumps(dict_model, ensure_ascii=False, indent=2) + "\n"  # 迁移模型 JSON 文本

    # 在输出目录创建唯一临时文件，避免跨卷移动破坏原子性。
    int_descriptor, str_temp_path = tempfile.mkstemp(  # 临时文件描述符和路径
        prefix=f".{path_output.name}.",  # 临时文件使用输出名作为前缀
        suffix=".tmp",  # 明确标识未发布临时文件
        dir=path_output.parent,  # 保证与最终文件位于同一目录
        text=True,  # 使用文本描述符写入 UTF-8 JSON
    )

    # 将临时路径转成 Path，供发布和清理逻辑共同复用。
    path_temp = Path(str_temp_path)  # 当前迁移临时文件路径

    # 无论发布成功与否都清理临时目录项。
    try:

        # 接管底层描述符并固定 UTF-8 与 LF 写入边界。
        with os.fdopen(int_descriptor, "w", encoding="utf-8", newline="\n") as obj_file:

            # 一次写入完整 JSON 文本，避免多个阶段暴露半成品。
            obj_file.write(str_text)

            # 刷新 Python 缓冲区后再要求操作系统同步文件内容。
            obj_file.flush()

            # 将当前临时文件内容同步到底层存储。
            os.fsync(obj_file.fileno())

        # 使用原子无覆盖原语发布完整临时文件。
        publish_no_clobber(path_temp, path_output)

    # 发布后或异常退出时都删除临时链接。
    finally:

        # 仅在临时路径仍存在时执行清理。
        if path_temp.exists():

            # 删除临时目录项；成功发布的最终硬链接仍保留完整内容。
            path_temp.unlink()

# 深复制 claims map，确保迁移元数据不共享调用方可变对象。
def copy_claims_map(dict_v2_claims: dict[str, Any]) -> dict[str, Any]:
    """复制旧版 claims map 的全部可接纳值。

    参数：
    - `dict_v2_claims`：通过版本检查的 claims map 2.0 对象。

    返回：
    - `dict[str, Any]`：与输入语义相同的独立 JSON 对象。

    异常：
    - `TypeError`：输入包含不可 JSON 序列化值时抛出。
    """

    # JSON 往返同时限制迁移元数据只能保存可落盘值。
    str_serialized = json.dumps(dict_v2_claims, ensure_ascii=False)  # 旧 claims map 临时文本

    # 返回独立副本，后续修改迁移结果不会污染输入对象。
    return json.loads(str_serialized)

# 按 Claims 3 白名单迁移省略候选并隔离历史扩展字段。
def migrate_omitted_candidates(
    obj_candidates: Any,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """迁移旧省略候选及其 legacy sidecar。

    参数：
    - `obj_candidates`：旧 Claims Map 的 omitted_candidates 根值。

    返回：
    - `tuple`：正式候选数组与按原索引保存的扩展字段。

    异常：
    - `ValueError`：根值、候选类型或基础字段无效时抛出。
    """

    # 省略候选必须保持数组合同，不能把坏根值静默解释为空。
    if not isinstance(obj_candidates, list):

        # 要求调用方先修复旧 companion 基础结构。
        raise ValueError("> ERR: [Python] omitted_candidates 必须为数组。")

    # 正式数组只保存 Claims 3 schema 允许字段。
    list_omitted: list[dict[str, Any]] = []  # 当前迁移后的正式省略候选

    # 扩展字段按原数组索引保存，避免与正式字段混合。
    dict_legacy_omitted: dict[str, dict[str, Any]] = {}  # 当前省略候选历史侧车

    # 每个旧候选独立验证并保持原顺序。
    for int_index, obj_candidate in enumerate(obj_candidates):

        # 标量或数组无法表达候选字段合同。
        if not isinstance(obj_candidate, dict):

            # 坏基础类型必须阻断，不能跳过后造成索引漂移。
            raise ValueError("> ERR: [Python] omitted_candidates 每项必须为对象。")

        # 只有类型和省略原因进入 Claims 3 正式数组。
        dict_candidate = {
            str_key: obj_candidate[str_key]  # 当前基础字段原值
            for str_key in SET_OMITTED_KEYS  # 遍历正式字段白名单
            if str_key in obj_candidate  # 只复制旧对象真实字段
        }  # 当前正式省略候选

        # 两个基础字段都必须是非空字符串。
        bool_base_invalid = any(  # 当前基础字段是否无效
            not isinstance(dict_candidate.get(str_key), str)  # 拒绝非文本基础值
            or not str(dict_candidate.get(str_key, "")).strip()  # 拒绝空白基础值
            for str_key in SET_OMITTED_KEYS  # 逐项验证正式字段
        )

        # 坏基础字段不能降级到 legacy sidecar 后继续发布。
        if bool_base_invalid:

            # 明确要求修复 claim_type 和 reason。
            raise ValueError(
                "> ERR: [Python] omitted_candidates 缺少有效 claim_type 或 reason。"
            )

        # 基础字段通过后按原顺序追加正式候选。
        list_omitted.append(dict_candidate)

        # 所有非白名单字段保留到独立历史侧车。
        dict_extra = {
            str_key: obj_value  # 当前历史扩展字段和值
            for str_key, obj_value in obj_candidate.items()  # 遍历旧候选全部字段
            if str_key not in SET_OMITTED_KEYS  # 排除已进入正式合同的字段
        }  # 当前候选扩展字段

        # 空扩展不创建冗余侧车条目。
        if dict_extra:

            # 原数组索引是没有稳定候选 ID 时唯一无损定位方式。
            dict_legacy_omitted[str(int_index)] = dict_extra  # 当前索引历史扩展

    # 返回正式数组和不会被下游业务消费的审计侧车。
    return list_omitted, dict_legacy_omitted

# 把旧 claims 值转换为 schema-valid 的 pending companion。
def build_v3_claims_map(
    dict_v2_claims: dict[str, Any],
    bytes_claims_input: bytes,
) -> dict[str, Any]:
    """构造待稳定特征映射的 Claims Map 3。

    参数：
    - `dict_v2_claims`：旧 Claims Map 2 对象。
    - `bytes_claims_input`：旧文件原始字节。

    返回：
    - `dict[str, Any]`：schema-valid pending companion。

    异常：
    - 无。
    """

    # 逐条白名单保留正式字段，其他值进入独立审计侧车。
    list_claims: list[dict[str, Any]] = []  # 等待重新映射特征和支撑结论的权利要求

    # 按 claim_no 保存不属于 Claims 3 正式字段的旧值。
    dict_legacy_claims: dict[str, dict[str, Any]] = {}  # 逐项历史字段审计映射

    # 每条旧权利要求独立转换。
    for dict_claim in dict_v2_claims.get("claims", []):

        # 非对象记录由旧合同调用方修复，本层不猜测字段。
        if not isinstance(dict_claim, dict):

            # 继续迁移其余可解释记录。
            continue

        # 正式 claim 只复制 schema 白名单字段。
        dict_migrated = {
            str_key: obj_value  # 当前可接纳旧字段和值
            for str_key, obj_value in dict_claim.items()  # 遍历旧 claim 全部字段
            if str_key in SET_CLAIM_KEYS  # 只保留 Claims 3 正式字段
        }  # 当前 pending claim

        # 收集未进入正式 claim 的旧扩展字段。
        dict_legacy_fields = {
            str_key: obj_value  # 保存被白名单排除的原值
            for str_key, obj_value in dict_claim.items()  # 遍历旧 claim 字段
            if str_key not in SET_CLAIM_KEYS | {"feature_ids", "support_status"}  # 排除正式或重建字段
        }  # 当前 claim 历史扩展字段

        # 非空扩展字段按 claim_no 进入审计侧车。
        if dict_legacy_fields:

            # claim_no 是跨迁移稳定的审计索引。
            dict_legacy_claims[str(dict_claim.get("claim_no", ""))] = dict_legacy_fields  # 按权利要求编号保存侧车

        # 新特征身份尚未映射。
        dict_migrated["feature_ids"] = []  # 待映射稳定特征集合

        # 旧支撑结论不得跨合同沿用。
        dict_migrated["support_status"] = "pending"  # 当前迁移支撑状态

        # 保存当前 schema-valid claim。
        list_claims.append(dict_migrated)

    # 顶层未知字段同样不能泄漏到正式 Claims 3 根对象。
    dict_legacy_root = {
        str_key: obj_value  # 保存旧根扩展原值
        for str_key, obj_value in dict_v2_claims.items()  # 遍历旧 companion 根字段
        if str_key not in {"contract_version", "claims", "omitted_candidates"}  # 排除正式根字段
    }  # Claims 2 顶层历史扩展字段

    # 省略候选基础字段严格验证，扩展值只进入 legacy sidecar。
    tuple_omitted_results = migrate_omitted_candidates(  # 正式候选与扩展的隔离结果
        dict_v2_claims.get("omitted_candidates", [])  # 旧候选的完整原始数组
    )  # 候选迁移器返回的唯一结果对

    # 正式数组只接收白名单字段。
    list_omitted = tuple_omitted_results[0]  # Claims 3 正式省略候选

    # 旧扩展按原索引保留，避免污染正式 schema。
    dict_legacy_omitted = tuple_omitted_results[1]  # 省略候选历史扩展侧车

    # 返回包含原始字节摘要和 schema 声明审计侧车的 companion。
    return {
        "contract_version": "3.0",
        "claims": list_claims,
        "omitted_candidates": list_omitted,
        "legacy_audit": {
            "root": dict_legacy_root,
            "claims": dict_legacy_claims,
            "omitted_candidates": dict_legacy_omitted,
        },
        "migration": {
            "state": "pending",
            "source_contract_version": str(dict_v2_claims.get("contract_version", "")),
            "input_sha256": hashlib.sha256(bytes_claims_input).hexdigest(),
        },
    }

# 构建保留旧事实但显式保持待补齐状态的 Model 4.0。
def build_v4_model(
    dict_v3_model: dict[str, Any],
    bytes_model_input: bytes,
    dict_v2_claims: dict[str, Any] | None,
    bytes_claims_input: bytes | None,
) -> dict[str, Any]:
    """构建待审查 Model 4.0 迁移结果。

    参数：
    - `dict_v3_model`：通过版本检查的 Model 3.0 对象。
    - `bytes_model_input`：旧模型文件原始字节。
    - `dict_v2_claims`：可选 claims map 2.0 对象。
    - `bytes_claims_input`：可选 claims map 文件原始字节。

    返回：
    - `dict[str, Any]`：保留旧值且新增域保持 pending 的 Model 4.0。

    异常：
    - `TypeError`：claims map 包含不可序列化值时抛出。
    """

    # 按白名单复制旧模型事实域，缺失登记表使用其正式空结构。
    dict_v4_model = {  # 待补齐的 Model 4.0 主体
        str_key: dict_v3_model.get(  # 当前旧模型字段保留值
            str_key,  # 当前需要保留的旧模型字段
            {"records": []} if str_key == "evidence_registry" else [],  # 当前字段正式空结构
        )
        for str_key in TUPLE_PRESERVED_KEYS  # 遍历允许直接保留的事实域
    }

    # 显式切换合同版本，禁止运行时继续兼容解释旧结构。
    dict_v4_model["contract_version"] = "4.0"  # 迁移输出合同版本

    # 新增特征不能由迁移器猜测，必须由后续人工或代理映射。
    dict_v4_model["feature_registry"] = []  # 待补齐稳定特征登记表

    # AI 适用性没有旧版等价字段，只能保持待确认。
    dict_v4_model["rule_applicability"] = {"ai_applicability": "pending"}  # 待确认规则适用性

    # 新增审查域从空记录和显式待办开始。
    dict_v4_model["semantic_review"] = {  # 待完成语义审查状态
        "agent_reviews": [],  # 尚无活动代理审查
        "human_confirmations": [],  # 尚无人工确认
        "agent_review_history": [],  # 尚无代理 supersession 历史
        "human_confirmation_history": [],  # 尚无人工 supersession 历史
        "pending_reviews": ["sections", "feature_registry"],  # 待审章节和特征
        "pending_confirmations": [  # 待完成人工确认类别
            "governed_facts",  # 受管事实确认
            "independent_claim_feature_sets",  # 独立项特征集确认
            "ai_applicability",  # AI 适用性确认
        ],
    }

    # 迁移元数据绑定旧模型原始字节并列出未完成动作。
    dict_migration = {  # Model 4.0 迁移审计对象
        "state": "pending",  # 迁移尚未完成语义补齐
        "source_contract_version": str(dict_v3_model.get("contract_version", "")),  # 旧模型版本
        "input_sha256": hashlib.sha256(bytes_model_input).hexdigest(),  # 旧模型原始字节摘要
        "pending_actions": [  # 迁移后必须完成的动作
            "map_features",  # 建立稳定特征映射
            "record_agent_reviews",  # 记录活动代理审查
            "record_human_confirmations",  # 记录人工确认
        ],
    }

    # 可选 claims map 存在时保留其全部可接纳值和独立原始字节摘要。
    if dict_v2_claims is not None:

        # 记录旧 claims map 版本，供后续显式升级到合同 3.0。
        dict_migration["claims_source_contract_version"] = str(  # 旧 claims map 合同版本
            dict_v2_claims.get("contract_version", "")  # 读取旧合同版本值
        )  # 完成 claims 来源版本文本转换

        # claims 特征身份尚未映射，因此迁移状态保持 pending。
        dict_migration["claims_state"] = "pending"  # claims map 迁移状态

        # 原始 claims 字节独立绑定，禁止使用重序列化文本替代。
        dict_migration["claims_input_sha256"] = hashlib.sha256(  # 旧 claims 原始字节摘要
            bytes_claims_input or b""  # 可选输入缺失时使用空字节
        ).hexdigest()  # 完成 claims 文件 SHA-256 计算

    # 把完整迁移审计对象嵌入唯一输出模型。
    dict_v4_model["migration"] = dict_migration  # Model 4.0 迁移元数据

    # 迁移器不具备案件内容上下文，来源链只能等待 pipeline 封印。
    dict_v4_model["provenance"] = {
        "state": "pending",  # 等待案件流水线封印
        "artifact_role": "initial",  # 迁移模型的初始工件角色
        "producer": "model4_pipeline",  # 封印后允许的生产者
        "case_id": "pending",  # 等待真实案件身份
        "parent_model_sha256": "0" * 64,  # 等待封印前父模型摘要
        "root_model_sha256": "0" * 64,  # 等待根模型摘要
        "draft_sha256": "0" * 64,  # 等待正式正文摘要
        "preview_sha256": "0" * 64,  # 等待确认预览摘要
        "claims_sha256": "0" * 64,  # 等待 companion 摘要
        "chain": [],  # 迁移初始模型尚无审查跳转
    }  # 待案件封印来源链

    # 返回仍明确待审查的版本四模型。
    return dict_v4_model

# 构造显式迁移命令行参数解析器。
def build_parser() -> argparse.ArgumentParser:
    """构造迁移入口参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册模型、claims 和输出参数的解析器。

    异常：
    - 无。
    """

    # 初始化迁移入口解析器，说明本工具只生成 pending Model 4.0。
    obj_parser = argparse.ArgumentParser(  # 迁移入口参数解析器
        description="Migrate a Model 3.0 file to pending Model 4.0."  # 入口用途说明
    )  # 完成 pending 迁移入口初始化

    # 注册必填旧模型路径。
    obj_parser.add_argument("--model", required=True)

    # 注册可选 claims map 2.0 路径。
    obj_parser.add_argument("--claims-map")

    # 注册与旧 claims 输入配对的新版 companion 输出。
    obj_parser.add_argument("--claims-output")

    # 双工件迁移必须同时发布批次回执。
    obj_parser.add_argument("--receipt-output")

    # 注册必填且不得覆盖的输出路径。
    obj_parser.add_argument("--output", required=True)

    # 返回已完成注册的解析器。
    return obj_parser

# 解析路径并验证迁移输入版本和覆盖边界。
def load_migration_inputs(
    obj_args: argparse.Namespace,
) -> tuple[Path, dict[str, Any], bytes, dict[str, Any] | None, bytes | None]:
    """加载并验证迁移输入。

    参数：
    - `obj_args`：命令行解析后的迁移参数。

    返回：
    - `tuple`：输出路径、旧模型对象及字节、可选 claims 对象及字节。

    异常：
    - `ValueError`：路径覆盖或输入合同版本不符合要求时抛出。
    """

    # 规范化三个文件路径，确保覆盖比较不受相对路径影响。
    path_model = Path(obj_args.model).resolve()  # 旧模型输入绝对路径

    # 输出路径在任何写入前完成规范化。
    path_output = Path(obj_args.output).resolve()  # 新模型输出绝对路径

    # 仅在调用方提供 claims map 时解析其绝对路径。
    path_claims = Path(obj_args.claims_map).resolve() if obj_args.claims_map else None  # 可选 claims 路径

    # 收集全部输入路径，供输出覆盖边界统一判断。
    set_input_paths = {path_model}  # 当前迁移输入路径集合

    # 可选 claims 路径也属于只读输入，不能成为输出目标。
    if path_claims is not None:

        # 把 claims 输入加入不可覆盖集合。
        set_input_paths.add(path_claims)

    # 输出与任一输入相同时立即拒绝。
    if path_output in set_input_paths:

        # 抛出明确边界错误，禁止迁移器反向修改输入。
        raise ValueError("> ERR: [Python] --output 不得覆盖任何迁移输入。")

    # 读取旧模型对象和完全相同的原始字节。
    tuple_model_input = read_json_object(path_model)  # 旧模型对象与字节元组

    # 从输入元组提取旧模型对象。
    dict_v3_model = tuple_model_input[0]  # 旧模型 JSON 对象

    # 从同一输入元组提取旧模型原始字节。
    bytes_model_input = tuple_model_input[1]  # 旧模型文件原始字节

    # 迁移器只接受明确的 Model 3.0。
    if dict_v3_model.get("contract_version") != "3.0":

        # 拒绝其他版本，避免重复迁移或宽松兼容。
        raise ValueError("> ERR: [Python] 仅接受 contract_version=3.0 的模型。")

    # 默认没有可选 claims 输入。
    dict_v2_claims = None  # 可选旧 claims map 对象

    # 默认没有可选 claims 原始字节。
    bytes_claims_input = None  # 可选旧 claims map 原始字节

    # 调用方提供 claims 路径时读取并验证其独立合同版本。
    if path_claims is not None:

        # 读取旧 claims 对象和原始字节。
        tuple_claims_input = read_json_object(path_claims)  # 旧 claims 对象与字节元组

        # 从输入元组提取旧 claims 对象。
        dict_v2_claims = tuple_claims_input[0]  # 等待 2.0 版本检查的 claims 根对象

        # 保存未经文本规范化的 claims 文件载荷用于独立摘要。
        bytes_claims_input = tuple_claims_input[1]  # 旧 claims map 文件原始字节

        # 只接受明确的 claims map 2.0。
        if dict_v2_claims.get("contract_version") != "2.0":

            # 拒绝未知 claims 合同，避免丢弃无法解释的字段。
            raise ValueError("> ERR: [Python] 可选 claims map 必须为 contract_version=2.0。")

    # 返回完成验证的全部迁移输入。
    return (
        path_output,  # 唯一新模型输出路径
        dict_v3_model,  # 已确认版本为 3.0 的模型主体
        bytes_model_input,  # 旧模型原始字节
        dict_v2_claims,  # 经过版本检查的旧 claims 对象
        bytes_claims_input,  # 与 claims 摘要绑定的文件字节
    )

# 解析并验证可选 companion 与 receipt 输出路径。
def resolve_batch_output_paths(
    obj_args: argparse.Namespace,
    path_output: Path,
) -> tuple[Path | None, Path | None]:
    """解析迁移批次的 companion 和 receipt 路径。

    参数：
    - `obj_args`：迁移 CLI 参数。
    - `path_output`：已经验证的 Model 4 输出路径。

    返回：
    - `tuple[Path | None, Path | None]`：claims 和 receipt 输出路径。

    异常：
    - `ValueError`：批次参数不完整或输出路径重合时抛出。
    - `FileExistsError`：任一批次目标已经存在时抛出。
    """

    # 三个批次参数必须全部存在或全部缺失，禁止无 receipt 双工件。
    set_presence = {
        bool(obj_args.claims_map),  # 是否提供旧 claims 输入
        bool(obj_args.claims_output),  # 是否请求 Claims 3 输出
        bool(obj_args.receipt_output),  # 是否请求批次回执
    }  # 当前批次参数存在状态

    # 混合真假说明批次参数不完整。
    if len(set_presence) != 1:

        # 映射阶段必须总能取得同批次 receipt。
        raise ValueError(
            "> ERR: [Python] --claims-map、--claims-output 与 --receipt-output 必须同时提供。"
        )

    # 仅完整批次请求解析 companion 规范路径。
    path_claims_output = (
        Path(obj_args.claims_output).resolve()  # 当前 Claims 3 最终路径
        if obj_args.claims_output  # 完整批次请求才有值
        else None  # 单模型迁移不创建 companion
    )  # 可选 Claims 3 输出路径

    # receipt 与 companion 同生共灭。
    path_receipt_output = (
        Path(obj_args.receipt_output).resolve()  # 当前批次回执最终路径
        if obj_args.receipt_output  # 调用方显式指定回执目标时解析
        else None  # 无 companion 事务时不创建回执
    )  # 可选批次回执输出路径

    # 单模型迁移无需继续验证批次目标。
    if path_claims_output is None or path_receipt_output is None:

        # 两个空值保持返回合同稳定。
        return None, None

    # 主输入和主输出都属于 companion 与 receipt 的禁止覆盖集合。
    set_reserved_paths = {
        Path(obj_args.model).resolve(),  # 旧模型只读输入
        path_output,  # 新 Model 4 主工件输出路径
    }  # 批次输出禁止命中的输入和主目标集合

    # 旧 claims 输入也不得成为任何输出。
    if obj_args.claims_map:

        # 把实际 companion 输入加入只读集合。
        set_reserved_paths.add(Path(obj_args.claims_map).resolve())

    # Claims 3 不得覆盖输入或主模型输出。
    if path_claims_output in set_reserved_paths:

        # 在任何 staging 副作用前拒绝路径别名。
        raise ValueError("> ERR: [Python] --claims-output 不得覆盖迁移输入或模型输出。")

    # 既有 companion 属于其他事务。
    if path_claims_output.exists():

        # 无覆盖合同保持既有字节和审计历史。
        raise FileExistsError(
            f"> ERR: [Python] claims 输出已存在:{path_claims_output}"
        )

    # receipt 还不得与本批次 companion 使用同一路径。
    if path_receipt_output in set_reserved_paths | {path_claims_output}:

        # 回执和被证明工件必须是独立目录项。
        raise ValueError("> ERR: [Python] --receipt-output 不得覆盖迁移输入或双工件输出。")

    # 既有 receipt 不能被新批次复用或覆盖。
    if path_receipt_output.exists():

        # 保持旧批次证明不可变。
        raise FileExistsError(
            f"> ERR: [Python] receipt 输出已存在:{path_receipt_output}"
        )

    # 返回通过覆盖边界的两个批次目标。
    return path_claims_output, path_receipt_output

# 为 Model 和 Claims 写入同一批次与回执身份。
def bind_batch_identity(
    dict_model: dict[str, Any],
    dict_claims: dict[str, Any],
    path_receipt_output: Path,
) -> None:
    """绑定迁移双工件的共同批次身份。

    参数：
    - `dict_model`：待发布 Model 4。
    - `dict_claims`：待发布 Claims 3。
    - `path_receipt_output`：同事务 receipt 路径。

    返回：
    - `None`：两个迁移对象已写入相同身份。

    异常：
    - 缺失 migration 对象时由字典访问上抛。
    """

    # 随机批次身份阻止相同输入在不同运行间互换 receipt。
    str_batch_id = f"MB{uuid.uuid4().hex}"  # 当前唯一迁移批次身份

    # receipt 自身使用独立身份，避免把批次号兼作工件号。
    str_receipt_id = f"MR{uuid.uuid4().hex}"  # 当前唯一回执身份

    # 两份正式工件必须绑定完全相同的三个身份字段。
    for dict_artifact in (dict_model, dict_claims):

        # migration 对象是 batch identity 的唯一正式承载域。
        dict_artifact["migration"].update(
            {
                "batch_id": str_batch_id,
                "receipt_id": str_receipt_id,
                "receipt_file": path_receipt_output.name,
            }
        )

# 生成 receipt 并以三工件事务共同发布迁移批次。
def publish_migration_batch(
    path_model_output: Path,
    dict_model: dict[str, Any],
    path_claims_output: Path,
    dict_claims: dict[str, Any],
    path_receipt_output: Path,
) -> None:
    """验证、摘要并原子发布迁移批次。

    参数：
    - `path_model_output`：Model 4 最终路径。
    - `dict_model`：Model 4 候选。
    - `path_claims_output`：Claims 3 最终路径。
    - `dict_claims`：Claims 3 候选。
    - `path_receipt_output`：批次 receipt 最终路径。

    返回：
    - `None`：三份工件均已发布。

    异常：
    - schema、序列化或批次事务错误由正式实现上抛。
    """

    # 双工件 schema 必须在任何目录项可见前通过。
    validate_pair_schemas(dict_model, dict_claims)

    # 同一模块同时提供最终序列化和三工件事务。
    module_atomic = load_atomic_module()  # 当前批次事务与序列化模块

    # receipt 摘要绑定 Model 最终落盘的完全相同字节。
    bytes_model_output = module_atomic.serialize_json_bytes(dict_model)  # Model 最终原始字节

    # Claims 摘要同样不允许通过重读近似文本推导。
    bytes_claims_output = module_atomic.serialize_json_bytes(dict_claims)  # companion 哈希绑定载荷

    # receipt 记录批次身份、精确文件名和两份原始摘要。
    dict_receipt = {
        "receipt_version": "1.0",  # 当前回执合同版本
        "receipt_id": dict_model["migration"]["receipt_id"],  # 当前回执身份
        "batch_id": dict_model["migration"]["batch_id"],  # 当前共同批次身份
        "artifacts": {  # 两份已序列化工件的身份与摘要
            "model": {  # Model 4 最终文件身份
                "file": path_model_output.name,  # Model 精确文件名
                "sha256": hashlib.sha256(bytes_model_output).hexdigest(),  # Model 原始摘要
            },
            "claims": {  # 回执中 companion 文件名和哈希的命名空间
                "file": path_claims_output.name,  # companion 大小写敏感文件名
                "sha256": hashlib.sha256(bytes_claims_output).hexdigest(),  # companion 最终字节摘要
            },
        },
    }  # 当前 schema-compliant 批次回执

    # 任一 staging 或 link 失败时批次事务恢复零新增输出。
    module_atomic.write_json_batch_atomic(
        [
            (path_model_output, dict_model),  # 第一份正式主模型
            (path_claims_output, dict_claims),  # 第二份正式 companion
            (path_receipt_output, dict_receipt),  # 第三份批次证明
        ]
    )

# 执行迁移主入口并发布唯一新模型。
def main() -> int:
    """执行显式 Model 3.0 到 Model 4.0 迁移。

    参数：
    - 无。

    返回：
    - `int`：迁移成功时返回零。

    异常：
    - 输入、版本、写入或发布错误由专用函数上抛。
    """

    # 解析命令行参数，得到本轮输入和输出路径文本。
    obj_args = build_parser().parse_args()  # 当前迁移命令行参数

    # 加载并验证所有输入，任何错误都发生在输出写入前。
    tuple_inputs = load_migration_inputs(obj_args)  # 已验证迁移输入元组

    # 从已验证输入元组提取唯一输出路径。
    path_output = tuple_inputs[0]  # 新模型最终输出路径

    # 提取旧模型对象，供版本四构建器保留事实。
    dict_v3_model = tuple_inputs[1]  # 版本四构建器消费的旧事实主体

    # 提取旧模型字节，供迁移摘要绑定。
    bytes_model_input = tuple_inputs[2]  # 写入迁移审计的模型文件载荷

    # 提取可选旧 claims 对象。
    dict_v2_claims = tuple_inputs[3]  # 需要完整保留字段的可选权利要求映射

    # 提取可选旧 claims 字节。
    bytes_claims_input = tuple_inputs[4]  # 绑定 claims 审计摘要的可选载荷

    # 在构建候选前固定完整批次输出集合，防止路径别名绕过事务边界。
    tuple_batch_paths = resolve_batch_output_paths(  # companion 与 receipt 验证路径对
        obj_args,  # 当前命令行中的批次参数
        path_output,  # 已验证的新模型目标
    )  # 可选 companion 与 receipt 的已验证路径对

    # companion 路径为空时保持单工件迁移分支。
    path_claims_output = tuple_batch_paths[0]  # 可选 Claims 3 最终路径

    # receipt 路径与 companion 同生共灭。
    path_receipt_output = tuple_batch_paths[1]  # 可选批次回执最终路径

    # 构建仍显式保持 pending 的 Model 4.0。
    dict_v4_model = build_v4_model(  # 本轮待原子发布的版本四模型
        dict_v3_model,  # 旧模型可接纳事实
        bytes_model_input,  # 绑定主输入摘要的文件载荷
        dict_v2_claims,  # 需要保留的旧 claims 值
        bytes_claims_input,  # 需要独立摘要的 claims 字节
    )  # 完成待办和迁移审计对象装配

    # 默认不生成 claims companion，保持无 claims 输入的迁移最小化。
    dict_claims_v3 = None  # 可选独立 claims 3.0 工件

    # 有配对 claims 输入和输出时构建独立新合同。
    if (
        path_claims_output is not None
        and path_receipt_output is not None
        and dict_v2_claims is not None
    ):

        # 迁移 claims 时原样保留可解释字段并附加独立输入摘要。
        dict_claims_v3 = build_v3_claims_map(  # 保留旧字段但清空旧支撑结论的 companion
            dict_v2_claims,  # 旧 Claims Map 2 可接纳字段
            bytes_claims_input or b"",  # 绑定独立输入摘要的原始字节
        )  # 待原子发布的 claims companion

        # 主模型仅记录 companion 文件名，不再嵌入另一份合同副本。
        dict_v4_model["migration"]["claims_companion"] = path_claims_output.name  # 独立 companion 文件名

        # 两份候选必须在序列化前绑定同一不可变批次身份。
        bind_batch_identity(
            dict_v4_model,  # 本轮 Model 4 候选
            dict_claims_v3,  # 需要共享身份的 companion 候选
            path_receipt_output,  # 两份候选共同引用的回执
        )

    # companion 存在时必须先验证两个完整 schema，再按事务共同发布。
    if (
        path_claims_output is not None
        and path_receipt_output is not None
        and dict_claims_v3 is not None
    ):

        # 事务发布保证任一 staging/link 失败时不遗留半个批次。
        publish_migration_batch(
            path_output,  # Model 4 最终路径
            dict_v4_model,  # 已绑定批次身份的模型
            path_claims_output,  # 批次中 companion 的发布目标
            dict_claims_v3,  # 已绑定批次身份的 companion
            path_receipt_output,  # 记录最终原始字节摘要的回执
        )

    # 无 claims companion 时仍沿用单工件原子无覆盖发布。
    else:

        # 单模型迁移不需要双工件事务。
        write_json_atomic(path_output, dict_v4_model)

    # 输出符合项目日志合同的迁移结果路径。
    print(f"> INFO: [Python] 已写入待审查 Model 4.0 迁移工件:{path_output}")

    # 返回成功退出码。
    return 0

# 脚本直接执行时统一把受控错误转换为退出码二。
if __name__ == "__main__":

    # Windows 重定向输出时显式使用 UTF-8，避免中文诊断触发本地编码错误。
    configure_utf8_text_streams()

    # 捕获可预期输入和文件错误，保持 CLI 不输出堆栈噪声。
    try:

        # 执行迁移主流程并把返回码交给 shell。
        raise SystemExit(main())

    # 将可预期失败写到标准错误并返回稳定退出码。
    except (
        FileExistsError,
        OSError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as obj_error:

        # 错误消息已经带项目统一前缀，直接写到标准错误。
        print(
            f"> ERR: [Python] 迁移失败:{obj_error}",
            file=__import__("sys").stderr,
        )

        # 用退出码二表示参数、输入或发布边界失败。
        raise SystemExit(2) from obj_error
