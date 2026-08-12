#!/usr/bin/env python3
"""把瞬时语义审查记录原子嵌入新的 Model 4.0 权威工件。"""

# 延迟解析类型注解，保持技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库负责参数解析、动态模块加载、JSON 处理和原子文件发布。
import argparse
import importlib.util
import json
import os
import sys
import tempfile

# JSON 映射类型和路径对象用于模型合同与案件边界声明。
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 固定正式验证器路径，审查哈希和候选 schema 只读取这一规则来源。
PATH_VALIDATOR = Path(__file__).resolve().parent / "structured_contract_validator.py"  # Model 4.0 验证器路径

# 状态模块唯一负责活动态、历史态和待办闭包。
PATH_REVIEW_STATE = Path(__file__).resolve().parent / "model_review_state.py"  # 活动态与历史态模块

# 来源链模块唯一负责案件身份、内容摘要和父模型链。
PATH_PROVENANCE = Path(__file__).resolve().parents[1] / "support" / "model_provenance.py"  # 案件来源链模块

# 统一命令行文本流编码，保证中文诊断可被 UTF-8 调用方稳定读取。
def configure_utf8_text_streams() -> None:
    """把可重配置的标准文本流切换为 UTF-8。

    参数：
    - 无。

    返回：
    - `None`：完成可用文本流的编码配置。

    异常：
    - 无。
    """

    # 逐一处理标准输出和标准错误，兼容被测试捕获的替代流对象。
    for obj_stream in (sys.stdout, sys.stderr):

        # 仅对支持运行时重配置的文本流调用该接口。
        if hasattr(obj_stream, "reconfigure"):

            # 固定 UTF-8 编码，避免 Windows 本地代码页破坏中文消息。
            obj_stream.reconfigure(encoding="utf-8")

# 按正式文件路径加载 Model 4.0 验证器。
def load_validator() -> Any:
    """加载语义审查验证器。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的正式验证模块。

    异常：
    - `ImportError`：模块规格或加载器缺失时抛出。
    """

    # 根据正式路径创建隔离模块加载规格。
    obj_specification = importlib.util.spec_from_file_location(  # 验证器加载规格
        "patent_semantic_review_validator",  # 审查入口隔离模块名称
        PATH_VALIDATOR,  # 正式验证器文件路径
    )  # 完成正式审查规则的文件定位

    # 规格或加载器缺失时禁止继续计算审查哈希。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出符合项目日志合同的明确导入错误。
        raise ImportError("> ERR: [Python] 无法加载 structured_contract_validator.py。")

    # 根据已验证规格创建本次调用独享的模块对象。
    module_validator = importlib.util.module_from_spec(obj_specification)  # 正式验证模块对象

    # 执行验证器源码，使哈希、目标解析和 schema 校验函数可用。
    obj_specification.loader.exec_module(module_validator)

    # 返回已初始化模块，禁止调用方复制验证规则。
    return module_validator

# 按正式路径加载 recorder 的独立职责模块。
def load_support_module(str_name: str, path_module: Path) -> Any:
    """加载 recorder 使用的同技能职责模块。

    参数：
    - `str_name`：隔离模块名称。
    - `path_module`：正式模块路径。

    返回：
    - `Any`：已执行源码的模块对象。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 根据正式路径创建隔离加载规格。
    obj_specification = importlib.util.spec_from_file_location(str_name, path_module)  # 职责模块规格

    # 规格不可用时禁止跳过状态或来源链规则。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出包含真实路径的明确导入错误。
        raise ImportError(f"> ERR: [Python] 无法加载模块:{path_module}")

    # 创建并执行当前职责模块。
    module_support = importlib.util.module_from_spec(obj_specification)  # recorder 职责模块

    # 执行正式职责模块源码，使其受控入口可供 recorder 调用。
    obj_specification.loader.exec_module(module_support)

    # 返回已初始化模块供主流程复用。
    return module_support

# 读取顶层必须为对象的 UTF-8 JSON 文件。
def read_json_object(path_file: Path) -> dict[str, Any]:
    """读取 JSON 对象文件。

    参数：
    - `path_file`：模型或瞬时审查文件路径。

    返回：
    - `dict[str, Any]`：解析后的独立 JSON 对象。

    异常：
    - `json.JSONDecodeError`：输入不是合法 JSON 时抛出。
    - `ValueError`：JSON 顶层不是对象时抛出。
    """

    # 读取 UTF-8 文本并保留解析器提供的真实错误位置。
    obj_value = json.loads(path_file.read_text(encoding="utf-8"))  # 当前输入 JSON 值

    # 顶层数组或标量不能表达模型或审查记录。
    if not isinstance(obj_value, dict):

        # 抛出包含输入路径的明确结构错误。
        raise ValueError(f"> ERR: [Python] JSON 顶层必须为对象:{path_file}")

    # 返回通过顶层类型检查的对象。
    return obj_value

# 原子发布临时文件，并在目标已存在时保持目标内容不变。
def publish_no_clobber(path_temp: Path, path_output: Path) -> None:
    """原子发布审查模型临时文件。

    参数：
    - `path_temp`：已经完整写入并刷盘的同目录临时文件。
    - `path_output`：不得覆盖的最终权威模型路径。

    返回：
    - `None`：硬链接发布成功。

    异常：
    - `FileExistsError`：最终输出已经存在时抛出。
    - `OSError`：底层原子链接失败时抛出。
    """

    # 使用原子硬链接创建消除 exists-check 与替换之间的竞争窗口。
    try:

        # 只有目标此前不存在时，链接创建才会成功。
        os.link(path_temp, path_output)

    # 竞争方先创建目标时转换为稳定项目错误。
    except FileExistsError:

        # 保持竞争方字节不变并明确报告拒绝覆盖。
        raise FileExistsError(f"> ERR: [Python] 输出已存在，拒绝覆盖:{path_output}") from None

# 先在同目录完整写入临时文件，再执行原子无覆盖发布。
def write_json_atomic(path_output: Path, dict_model: Mapping[str, Any]) -> None:
    """原子且无覆盖地写出权威模型。

    参数：
    - `path_output`：最终权威模型路径。
    - `dict_model`：已经嵌入活动审查的 Model 4.0。

    返回：
    - `None`：完整模型成功发布。

    异常：
    - `FileExistsError`：输出已经存在或发生竞争创建时抛出。
    - `OSError`：目录、写入、刷盘或发布失败时抛出。
    """

    # 确保输出父目录存在，临时文件和最终文件位于同一文件系统。
    path_output.parent.mkdir(parents=True, exist_ok=True)

    # 固定缩进、UTF-8 和末尾换行，便于人工审阅与重复比较。
    str_text = json.dumps(dict_model, ensure_ascii=False, indent=2) + "\n"  # 权威模型 JSON 文本

    # 在输出目录创建唯一临时文件，避免跨卷移动破坏原子性。
    int_descriptor, str_temp_path = tempfile.mkstemp(  # 临时文件描述符和路径
        prefix=f".{path_output.name}.",  # 临时文件使用输出名作为前缀
        suffix=".tmp",  # 明确标识未发布临时文件
        dir=path_output.parent,  # 保证与最终文件位于同一目录
        text=True,  # 使用文本描述符写入 UTF-8 JSON
    )

    # 将临时路径转成 Path，供发布和清理逻辑共同复用。
    path_temp = Path(str_temp_path)  # 当前审查模型临时文件路径

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

            # 删除临时目录项；成功发布的最终链接仍保留完整内容。
            path_temp.unlink()

# 在模型中定位受管数据确认目标。
def resolve_data_target(
    dict_model: Mapping[str, Any],
    str_target_id: str,
) -> tuple[Any, list[str]] | None:
    """解析受管数据目标。

    参数：
    - `dict_model`：当前 Model 4.0。
    - `str_target_id`：需要确认的稳定数据编号。

    返回：
    - `tuple[Any, list[str]] | None`：当前内容和证据；目标不存在时为空。

    异常：
    - 无。
    """

    # 逐项扫描正式数据登记表，只接受映射记录。
    for dict_record in dict_model.get("data_registry", []):

        # 稳定编号完全相同时返回当前记录副本和证据集合。
        if isinstance(dict_record, Mapping) and str(dict_record.get("data_id", "")) == str_target_id:

            # 复制目标内容，避免嵌入记录与模型登记表共享可变引用。
            dict_content = dict(dict_record)  # 当前受管数据内容副本

            # 规范化当前数据证据编号供哈希绑定。
            list_evidence_ids = [
                str(obj_id)  # 当前受管数据证据编号
                for obj_id in dict_record.get("evidence_ids", [])  # 遍历数据记录证据
            ]  # 当前受管数据证据集合

            # 返回当前事实内容和证据绑定。
            return dict_content, list_evidence_ids

    # 未命中稳定编号时返回空标记。
    return None

# 解析技术效果确认即将写入的事实和当前证据。
def resolve_feature_effect_target(
    dict_model: Mapping[str, Any],
    dict_review: Mapping[str, Any],
    str_target_id: str,
) -> tuple[list[str], list[str]]:
    """解析技术效果确认目标。

    参数：
    - `dict_model`：当前 Model 4。
    - `dict_review`：瞬时人工确认输入。
    - `str_target_id`：稳定 feature_id。

    返回：
    - `tuple[list[str], list[str]]`：确认效果与当前特征证据。

    异常：
    - `ValueError`：效果为空或目标特征不存在时抛出。
    """

    # 技术效果必须来自明确人工内容，不能由状态模块猜测。
    obj_content = dict_review.get("target_content")  # 待确认技术效果根值

    # 空值或非数组不能形成因果效果事实。
    if not isinstance(obj_content, list) or not obj_content:

        # 阻断缺少实体效果内容的确认。
        raise ValueError("> ERR: [Python] 技术效果确认必须提供非空 target_content。")

    # 按稳定 feature_id 查找唯一目标。
    for dict_feature in dict_model.get("feature_registry", []):

        # 目标身份必须完全一致，禁止使用文本近似匹配。
        if (
            isinstance(dict_feature, Mapping)
            and str(dict_feature.get("feature_id", "")) == str_target_id
        ):

            # 过滤空白文本后再交给共享状态转换写回。
            list_effects = [
                str(obj_item)  # 当前非空人工效果文本
                for obj_item in obj_content  # 遍历人工提交的效果数组
                if str(obj_item).strip()  # 排除空白效果
            ]  # 当前规范技术效果数组

            # 证据继续取自父模型事实域，不信任瞬时输入。
            list_evidence_ids = [
                str(obj_id)  # 当前特征证据编号
                for obj_id in dict_feature.get("evidence_ids", [])  # 遍历正式证据绑定
            ]  # 当前目标证据集合

            # 返回参与 target_hash 的完整事实边界。
            return list_effects, list_evidence_ids

    # 悬空 feature_id 不能形成活动确认记录。
    raise ValueError(f"> ERR: [Python] 技术效果确认目标不存在:{str_target_id}")

# 从 Claims Map 3 和模型特征重建独立项确认目标。
def resolve_independent_claim_target(
    dict_model: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None,
    str_target_id: str,
) -> tuple[list[str], list[str]]:
    """解析独立权利要求的稳定特征和证据闭包。

    参数：
    - `dict_model`：当前 Model 4。
    - `dict_claims_map`：当前 Claims Map 3。
    - `str_target_id`：独立权利要求编号。

    返回：
    - `tuple[list[str], list[str]]`：稳定特征集合与证据并集。

    异常：
    - `ValueError`：companion、独立项或非空特征集合缺失时抛出。
    """

    # 独立项确认必须从当前 companion 重建，不能信任记录快照。
    if not isinstance(dict_claims_map, Mapping):

        # 缺失 companion 时无法证明当前保护范围。
        raise ValueError("> ERR: [Python] 独立项确认缺少当前案件 Claims Map 3。")

    # claim_no 与独立类型共同定位唯一目标。
    dict_claim = next(  # 当前独立权利要求对象
        (
            dict_item  # 当前匹配权利要求
            for dict_item in dict_claims_map.get("claims", [])  # 遍历当前 companion
            if isinstance(dict_item, Mapping)  # 排除坏类型 claim
            and str(dict_item.get("claim_no", "")) == str_target_id  # 匹配稳定编号
            and str(dict_item.get("claim_type", "")).startswith("independent_")  # 限定独立项
        ),
        None,  # 未命中时返回空标记
    )

    # 不存在的 claim_no 不能形成悬空确认。
    if dict_claim is None:

        # 错误保留真实编号供调用方修复。
        raise ValueError(f"> ERR: [Python] 独立项确认目标不存在:{str_target_id}")

    # 当前保护范围只由 companion 中稳定 feature_id 组成。
    list_feature_ids = [
        str(obj_id)  # 当前稳定特征编号
        for obj_id in dict_claim.get("feature_ids", [])  # 遍历独立项特征集合
    ]  # 当前独立项特征身份数组

    # 空集合不能进入人工确认白名单。
    if not list_feature_ids:

        # 要求先通过正式 mapping 阶段建立稳定特征。
        raise ValueError("> ERR: [Python] 独立项确认的当前特征集合为空。")

    # 建立稳定特征到完整事实的索引。
    dict_features = {
        str(dict_item.get("feature_id")): dict_item  # 稳定身份到特征事实
        for dict_item in dict_model.get("feature_registry", [])  # 遍历当前特征登记
        if isinstance(dict_item, Mapping) and dict_item.get("feature_id")  # 排除无身份记录
    }  # 当前模型稳定特征索引

    # 证据摘要绑定这些特征的实时证据确定性并集。
    list_evidence_ids = sorted(  # 当前独立项证据并集
        {
            str(obj_id)  # 当前证据编号
            for str_feature_id in list_feature_ids  # 遍历当前独立项特征
            for obj_id in dict_features.get(  # 读取模型中的实时特征
                str_feature_id,  # 当前稳定特征身份
                {},  # 缺失特征产生空证据并由完整校验阻断
            ).get("evidence_ids", [])  # 当前特征证据集合
        }
    )

    # 返回当前模型与 companion 共同证明的确认目标。
    return list_feature_ids, list_evidence_ids

# 解析人工确认当前绑定的真实目标内容和证据。
def resolve_human_target(
    dict_model: dict[str, Any],
    dict_review: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None = None,
) -> tuple[Any, list[str]]:
    """解析人工确认目标。

    参数：
    - `dict_model`：当前 Model 4.0。
    - `dict_review`：瞬时人工确认输入。
    - `dict_claims_map`：独立权利要求确认使用的当前 Claims Map 3。

    返回：
    - `tuple[Any, list[str]]`：当前目标内容和证据绑定。

    异常：
    - `ValueError`：目标不存在、类型不支持或独立项内容为空时抛出。
    """

    # 读取人工确认目标类型，后续按显式分支解析。
    str_target_type = str(dict_review.get("target_type", ""))  # 人工确认目标类型

    # 读取稳定目标编号，禁止用标题或文本相似度定位。
    str_target_id = str(dict_review.get("target_id", ""))  # 人工确认目标编号

    # 数据确认必须回到模型数据登记表解析当前值。
    if str_target_type == "data":

        # 调用专用数据定位器取得内容和证据。
        tuple_data_target = resolve_data_target(dict_model, str_target_id)  # 当前数据确认目标

        # 目标不存在时拒绝生成悬空确认记录。
        if tuple_data_target is None:

            # 抛出包含稳定编号的明确目标错误。
            raise ValueError(f"> ERR: [Python] 人工确认目标不存在:data:{str_target_id}")

        # 返回由模型登记表解析的真实目标。
        return tuple_data_target

    # AI 适用性由明确人工输入推进到正式规则域。
    if str_target_type == "ai_applicability" and str_target_id == "model":

        # 人工输入必须给出完整规则对象。
        obj_content = dict_review.get("target_content")  # 人工确认后的规则对象

        # 非对象内容不能形成明确适用性结论。
        if not isinstance(obj_content, Mapping):

            # 拒绝缺少实体规则结论的确认。
            raise ValueError("> ERR: [Python] AI 适用性确认缺少目标规则对象。")

        # 状态转换阶段将同一目标内容写入正式规则域。
        return dict(obj_content), []

    # 技术效果确认补齐指定稳定特征的因果效果。
    if str_target_type == "feature_technical_effect":

        # 专用解析器保持主分派函数只负责目标路由。
        return resolve_feature_effect_target(dict_model, dict_review, str_target_id)

    # 独立项确认由 claims 流程显式提供稳定特征集合。
    if str_target_type == "independent_claim":

        # 专用解析器重建实时保护范围和证据闭包。
        return resolve_independent_claim_target(
            dict_model,
            dict_claims_map,
            str_target_id,
        )

    # 其他目标类型不属于当前通用人工确认合同。
    raise ValueError(f"> ERR: [Python] 不支持的人工确认目标:{str_target_type}:{str_target_id}")

# 根据当前模型重算哈希并构造最终嵌入记录。
def build_embedded_review(
    dict_model: dict[str, Any],
    dict_review: Mapping[str, Any],
    str_reviewer_type: str,
    module_validator: Any,
    dict_claims_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """构造绑定当前模型内容的审查记录。

    参数：
    - `dict_model`：当前 Model 4.0。
    - `dict_review`：瞬时代理审查或人工确认输入。
    - `str_reviewer_type`：`agent` 或 `human`。
    - `module_validator`：正式 Model 4.0 验证模块。
    - `dict_claims_map`：独立权利要求目标使用的当前 Claims Map 3。

    返回：
    - `dict[str, Any]`：带当前内容、证据和确定性哈希的候选记录。

    异常：
    - `ValueError`：目标不存在或输入缺少必填字段时抛出。
    """

    # 读取稳定目标键，代理和人工记录共用同一身份边界。
    str_target_type = str(dict_review.get("target_type", ""))  # 审查目标类型

    # 读取稳定目标编号，禁止瞬时输入改用内容定位。
    str_target_id = str(dict_review.get("target_id", ""))  # 审查目标编号

    # 代理目标必须由正式验证器从当前模型解析。
    if str_reviewer_type == "agent":

        # 解析当前章节、特征或模型级目标。
        tuple_target = module_validator.resolve_review_target(  # 当前代理审查目标
            dict_model,  # 当前权威模型
            str_target_type,  # 当前代理目标类型
            str_target_id,  # 当前代理目标编号
        )  # 完成模型内目标解析

        # 不存在的目标不能形成活动审查。
        if tuple_target is None:

            # 抛出包含目标键的明确错误。
            raise ValueError(f"> ERR: [Python] 代理审查目标不存在:{str_target_type}:{str_target_id}")

        # 代理记录要求稳定编号、目标、裁决和五维覆盖。
        list_required = [
            "review_id",  # 代理审查稳定编号
            "target_type",  # 代理审查目标类型
            "target_id",  # 代理审查目标编号
            "verdict",  # 代理审查裁决
            "coverage",  # 五维覆盖结果
        ]  # 代理审查必填字段

    # 人工确认目标使用专用解析器并要求确认合同字段。
    else:

        # 从当前模型和显式独立项内容解析确认目标。
        tuple_target = resolve_human_target(dict_model, dict_review, dict_claims_map)  # 当前人工确认目标

        # 人工记录要求确认编号、确认类别、目标和决定。
        list_required = [
            "confirmation_id",  # 人工确认稳定编号
            "confirmation_type",  # 人工确认类别
            "target_type",  # 确认记录所指事实类别
            "target_id",  # 确认记录所指稳定身份
            "decision",  # 人工确认决定
        ]  # 人工确认必填字段

    # 汇总瞬时输入缺失的必填字段。
    list_missing = [
        str_key  # 当前缺失字段名
        for str_key in list_required  # 遍历当前记录类型必填字段
        if str_key not in dict_review  # 只保留瞬时输入未提供的字段
    ]  # 当前审查输入缺失字段

    # 任何必填字段缺失都在哈希计算前阻断。
    if list_missing:

        # 抛出可直接修复的字段列表。
        raise ValueError(f"> ERR: [Python] 审查文件缺少字段:{','.join(list_missing)}")

    # 复制瞬时输入但丢弃调用方自带哈希，禁止伪造可信摘要。
    dict_embedded = {
        str_key: obj_value  # 当前审查输入字段和值
        for str_key, obj_value in dict_review.items()  # 遍历瞬时输入全部字段
        if str_key != "target_hash"  # 排除调用方提供的非可信哈希
    }  # 待嵌入审查记录

    # 记录由当前模型解析的真实目标内容。
    dict_embedded["target_content"] = tuple_target[0]  # 当前目标内容快照

    # 证据作为集合排序去重，固定审查摘要输入边界。
    dict_embedded["evidence_bindings"] = sorted(  # 当前目标规范证据集合
        {
            str(obj_id)  # 当前目标证据编号
            for obj_id in tuple_target[1]  # 遍历当前模型解析的证据
        }
    )  # 完成证据排序去重

    # 使用正式验证器计算绑定目标、证据和合同版本的摘要。
    dict_embedded["target_hash"] = module_validator.calculate_semantic_review_hash(  # 当前审查确定性哈希
        str_target_type,  # 摘要绑定的目标类别
        str_target_id,  # 审查目标稳定编号
        tuple_target[0],  # 当前模型目标内容
        tuple_target[1],  # 当前模型证据绑定
        str(dict_model.get("contract_version", "")),  # 当前模型合同版本
    )  # 完成五项摘要输入绑定

    # 返回等待 schema 校验的完整候选记录。
    return dict_embedded

# 根据审查者类型选择模型中的正式记录数组。
def get_review_collection_name(str_reviewer_type: str) -> str:
    """返回审查记录集合名称。

    参数：
    - `str_reviewer_type`：`agent` 或 `human`。

    返回：
    - `str`：`agent_reviews` 或 `human_confirmations`。

    异常：
    - 无。
    """

    # 代理记录和人工确认使用不同数组，其他值已由 argparse 拒绝。
    if str_reviewer_type == "agent":

        # 返回代理审查数组键。
        return "agent_reviews"

    # 返回人工确认数组键。
    return "human_confirmations"

# 委托独立状态模块推进活动记录和不可变历史。
def replace_active_review(
    dict_model: dict[str, Any],
    str_reviewer_type: str,
    dict_embedded: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None = None,
) -> None:
    """推进活动记录并保留 supersession 历史。

    参数：
    - `dict_model`：待更新 Model 4。
    - `str_reviewer_type`：代理或人工记录类型。
    - `dict_embedded`：已通过候选 schema 的记录。
    - `dict_claims_map`：当前案件 Claims Map 3。

    返回：
    - `None`：活动态、历史态和待办已更新。

    异常：
    - 状态模块不可用或记录 ID 冲突时抛出。
    """

    # 加载唯一状态推进实现，避免 recorder 复制历史规则。
    module_state = load_support_module("patent_model_review_state", PATH_REVIEW_STATE)  # Model 4 状态模块

    # 由独立模块完成全局 ID、supersedes 和待办重算。
    module_state.replace_active_review(
        dict_model,
        str_reviewer_type,
        dict_embedded,
        dict_claims_map,
    )

# 发布前验证完整候选，而不是只验证新增单条记录。
def validate_candidate_model_for_publish(
    dict_model: Mapping[str, Any],
    module_validator: Any | None = None,
) -> None:
    """验证待发布 Model 4 候选的完整 schema。

    参数：
    - `dict_model`：已经完成状态和来源链推进的候选。
    - `module_validator`：可选正式验证器实例。

    返回：
    - `None`：候选 schema 合法。

    异常：
    - `ValueError`：完整候选存在 schema finding 时抛出。
    """

    # 未复用调用方模块时加载正式 schema 验证器。
    module_contract = module_validator or load_validator()  # 当前 Model 4 验证器

    # 对完整候选执行正式 schema，而非单条记录局部定义。
    list_findings = module_contract.validate_model_schema(dict_model)  # 候选模型结构问题

    # 任一结构问题都必须在发布前阻断。
    if list_findings:

        # 汇总全部消息供一次修复。
        str_messages = ";".join(str(dict_item.get("message", "")) for dict_item in list_findings)  # 候选问题文本

        # 抛出统一项目错误。
        raise ValueError(f"> ERR: [Python] Model 4 候选无效:{str_messages}")

# 构造原子审查记录命令行参数解析器。
def build_parser() -> argparse.ArgumentParser:
    """构造审查记录入口参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册模型、审查、类型和输出参数的解析器。

    异常：
    - 无。
    """

    # 初始化入口解析器，说明本工具只写出新的 Model 4.0。
    obj_parser = argparse.ArgumentParser(  # 审查记录入口参数解析器
        description="Embed a semantic review into a new Model 4.0 file."  # 入口用途说明
    )  # 完成新权威模型入口初始化

    # 注册当前案件根目录，用于约束模型和内容摘要。
    obj_parser.add_argument("--case-dir", required=True)

    # 注册只读输入模型路径。
    obj_parser.add_argument("--model", required=True)

    # 注册瞬时审查文件路径。
    obj_parser.add_argument("--review-file", required=True)

    # 注册受限审查者类型，禁止运行时猜测记录集合。
    obj_parser.add_argument(
        "--reviewer-type",
        required=True,
        choices=("agent", "human"),
    )

    # 注册不得覆盖的唯一输出模型路径。
    obj_parser.add_argument("--output", required=True)

    # 返回完成参数注册的解析器。
    return obj_parser

# 解析并验证审查入口的三个文件路径。
def resolve_paths(obj_args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    """解析审查入口路径。

    参数：
    - `obj_args`：命令行解析后的审查参数。

    返回：
    - `tuple[Path, Path, Path]`：模型、审查和输出绝对路径。

    异常：
    - `ValueError`：输出覆盖任一输入时抛出。
    """

    # 规范化当前案件根目录。
    path_case_dir = Path(obj_args.case_dir).resolve()  # 当前案件根目录

    # 规范化只读模型路径。
    path_model = Path(obj_args.model).resolve()  # Model 4.0 输入绝对路径

    # 规范化瞬时审查路径。
    path_review = Path(obj_args.review_file).resolve()  # 瞬时审查输入绝对路径

    # 规范化唯一输出路径。
    path_output = Path(obj_args.output).resolve()  # 新权威模型输出绝对路径

    # 输出不得与任一输入相同，避免反向修改来源。
    if path_output in {path_model, path_review}:

        # 抛出明确覆盖边界错误。
        raise ValueError("> ERR: [Python] --output 不得覆盖模型或瞬时审查输入。")

    # 返回三个完成规范化的路径。
    return path_case_dir, path_model, path_review, path_output

# 执行候选构建、schema 校验、活动态替换和原子发布。
def main() -> int:
    """执行语义审查记录主入口。

    参数：
    - 无。

    返回：
    - `int`：新权威模型发布成功时返回零。

    异常：
    - 输入、目标、schema、写入或发布错误由专用函数上抛。
    """

    # 解析本轮审查记录命令行参数。
    obj_args = build_parser().parse_args()  # 当前审查记录参数

    # 规范化三个路径并验证输入输出不重合。
    tuple_paths = resolve_paths(obj_args)  # 已验证审查入口路径元组

    # 提取当前案件根目录。
    path_case_dir = tuple_paths[0]  # 当前来源链案件目录

    # 提取只读模型输入路径。
    path_model = tuple_paths[1]  # 当前 Model 4.0 输入路径

    # 提取瞬时审查输入路径。
    path_review = tuple_paths[2]  # 当前瞬时审查路径

    # 提取唯一新权威模型路径。
    path_output = tuple_paths[3]  # 当前原子发布目标

    # 加载来源链模块并保留父模型原始字节。
    module_provenance = load_support_module("patent_model_provenance", PATH_PROVENANCE)  # Model 4 来源链模块

    # 父模型摘要必须基于完全相同的原始字节。
    bytes_parent_model = path_model.read_bytes()  # 当前父模型原始字节

    # 先读取父模型角色，reviewed 父节点必须执行完整有序链验证。
    dict_parent_probe = read_json_object(path_model)  # 当前父模型角色探测对象

    # 只有初始模型允许关闭 reviewed 链门。
    obj_parent_provenance = dict_parent_probe.get("provenance")  # 当前父模型来源链

    # reviewed 父节点继续记录前必须先证明其完整历史。
    bool_require_reviewed = (
        isinstance(obj_parent_provenance, Mapping)  # 父节点具备结构化来源信息
        and obj_parent_provenance.get("artifact_role") == "reviewed"  # 审查后父节点必须重放全链
    )  # 当前父节点是否要求完整链验证

    # 验证模型属于当前案件且绑定当前正文、预览和 claims。
    dict_model = module_provenance.validate_model_for_case(  # 通过案件和内容摘要边界的父模型
        path_case_dir,  # provenance 身份和内容摘要对应的案件根
        path_model,  # 调用方提供的父模型路径
        require_reviewed=bool_require_reviewed,  # reviewed 父节点必须先完成全链重放
    )  # 已通过案件边界的 Model 4

    # 读取当前案件 Claims Map 3，独立项确认不得信任瞬时输入。
    dict_claims_map = read_json_object(  # 独立项确认和待办重算使用的当前 claims
        path_case_dir / "03_drafts" / "claims_map.json"  # 当前案件正式 Claims Map 3
    )

    # 审查入口只接受明确的 Model 4.0。
    if dict_model.get("contract_version") != "4.0":

        # 旧模型必须先通过显式迁移入口。
        raise ValueError("> ERR: [Python] MIGRATION_REQUIRED:输入模型不是版本4.0。")

    # 读取瞬时审查输入，不把该文件直接当作可信记录。
    dict_review = read_json_object(path_review)  # 当前瞬时审查对象

    # 加载唯一正式验证器，供目标解析、哈希和 schema 校验共同使用。
    module_validator = load_validator()  # 当前 Model 4.0 验证模块

    # 根据当前模型重新解析目标并计算可信哈希。
    dict_embedded = build_embedded_review(  # 待校验嵌入候选
        dict_model,  # 作为哈希来源的权威模型
        dict_review,  # 不可信瞬时审查输入
        obj_args.reviewer_type,  # 代理或人工记录类型
        module_validator,  # 正式目标和哈希规则
        dict_claims_map,  # 当前独立项事实来源
    )  # 完成当前内容与可信哈希装配

    # 写入模型前执行单条候选 schema，禁止无效记录污染权威输出。
    list_candidate_findings = module_validator.validate_review_record_schema(  # 写入前候选结构问题
        dict_embedded,  # 已重算内容和哈希的候选
        obj_args.reviewer_type,  # 选择代理或人工 schema
    )  # 完成单条记录合同检查

    # 任一候选结构问题都必须在输出创建前阻断。
    if list_candidate_findings:

        # 汇总全部 schema 消息，便于一次修复候选。
        str_messages = ";".join(  # 候选无效消息文本
            str(dict_item["message"])  # 当前候选 schema 消息
            for dict_item in list_candidate_findings  # 遍历全部候选问题
        )  # 完成全部候选问题汇总

        # 抛出带统一日志前缀的候选错误。
        raise ValueError(f"> ERR: [Python] 审查候选无效:{str_messages}")

    # 由共享纯函数构造 recorder 除 provenance 外的唯一候选。
    module_state = load_support_module(  # 当前共享状态转换模块
        "patent_model_review_state",  # 隔离动态模块名称
        PATH_REVIEW_STATE,  # 受管状态转换实现的固定路径
    )  # provenance 重放复用的生产状态实现

    # recorder 和 provenance 必须消费同一纯候选构造器。
    dict_model = module_state.build_review_candidate(  # 除 provenance 外的完整唯一子候选
        dict_model,  # 当前已验证父模型
        dict_embedded,  # 已嵌入唯一记录身份的审查事实
        obj_args.reviewer_type,  # 决定 agent 或 confirmation 状态域
        dict_claims_map,  # 独立权利要求确认所需 companion
    )  # 当前唯一合法子候选

    # 提取本次审查记录的全局身份供来源链登记。
    str_record_id = str(  # 本轮来源链跳转绑定的全局审查记录身份
        dict_embedded.get("review_id")  # AI 审查记录身份
        or dict_embedded.get("confirmation_id")  # 人工确认记录身份
        or ""  # 缺失身份由候选 schema 阻断
    )

    # 来源链新增一跳并绑定父模型原始摘要。
    dict_model["provenance"] = module_provenance.build_review_provenance(  # 绑定真实父字节的新来源链
        dict_model,  # 已完成活动态推进的子模型
        bytes_parent_model,  # 当前父模型未重序列化字节
        str_record_id,  # 触发本跳的全局记录身份
        path_case_dir,  # 提供根锚点和内容工件边界
        path_model,  # 当前直接父文件
        path_output,  # 当前待发布子文件
    )  # 保留根锚点并新增一跳的 reviewed provenance

    # 完整候选 schema 通过后才允许原子发布。
    validate_candidate_model_for_publish(dict_model, module_validator)

    # 原子发布新的唯一权威模型，竞争输出存在时拒绝覆盖。
    write_json_atomic(path_output, dict_model)

    # 输出符合项目日志合同的成功路径。
    print(f"> INFO: [Python] 已写入新的 Model 4.0 权威工件:{path_output}")

    # 返回成功退出码。
    return 0

# 脚本直接执行时统一把受控错误转换为退出码二。
if __name__ == "__main__":

    # 在解析和错误输出前固定文本流编码。
    configure_utf8_text_streams()

    # 捕获可预期输入和文件错误，保持 CLI 不输出堆栈噪声。
    try:

        # 执行审查记录主流程并把返回码交给 shell。
        raise SystemExit(main())

    # 将可预期失败写到标准错误并返回稳定退出码。
    except (
        FileExistsError,
        ImportError,
        OSError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as obj_error:

        # 统一包装错误前缀，避免底层 JSON 消息违反日志合同。
        print(
            f"> ERR: [Python] 审查记录失败:{obj_error}",
            file=__import__("sys").stderr,
        )

        # 用退出码二表示参数、输入、候选或发布失败。
        raise SystemExit(2) from obj_error
