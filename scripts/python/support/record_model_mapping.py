#!/usr/bin/env python3
"""把 pending Model 4 与 Claims 3 映射为新的双工件；stdout 仅输出简短状态。"""

# 延迟解析类型注解，保持技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库负责参数、动态模块加载、JSON 读取和路径边界。
import argparse
import hashlib
import importlib.util
import json
import re
import sys

# 抽象集合和路径类型支撑结构验证与边界检查。
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 三个共享模块分别提供稳定身份、事务发布和正式 schema。
PATH_SUPPORT_DIR = Path(__file__).resolve().parent  # 当前 support 模块目录

# 稳定特征身份与正文生成端使用同一实现。
PATH_FEATURE_IDENTITY = PATH_SUPPORT_DIR / "feature_identity.py"  # 稳定特征身份模块

# 双工件必须通过共享无覆盖事务共同发布。
PATH_ATOMIC_PAIR = PATH_SUPPORT_DIR / "atomic_json_pair.py"  # 双 JSON 事务模块

# 正式结构验证器负责发布前完整 schema 检查。
PATH_VALIDATOR = PATH_SUPPORT_DIR.parent / "review" / "structured_contract_validator.py"  # 主模型与权利要求结构验证器

# 从固定文件路径加载共享实现，避免复制身份或事务规则。
def load_module(str_name: str, path_module: Path) -> Any:
    """加载当前技能内的共享 Python 模块。

    参数：
    - `str_name`：隔离模块名称。
    - `path_module`：正式源码文件路径。

    返回：
    - `Any`：已经执行的模块对象。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 文件位置规格不会依赖工作目录或全局安装状态。
    obj_specification = importlib.util.spec_from_file_location(str_name, path_module)  # 当前模块加载规格

    # 缺少加载器时禁止使用本地替代逻辑。
    if obj_specification is None or obj_specification.loader is None:

        # 错误指出无法加载的正式模块路径。
        raise ImportError(f"> ERR: [Python] 无法加载正式模块:{path_module}")

    # 根据已验证规格创建隔离模块对象。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 当前共享模块对象

    # 执行共享源码后才允许调用其公开函数。
    obj_specification.loader.exec_module(obj_module)

    # 返回本次调用独享的模块实例。
    return obj_module

# 读取 JSON 对象并拒绝数组或标量输入。
def read_json_object(path_file: Path) -> dict[str, Any]:
    """读取顶层为对象的 UTF-8 JSON 文件。

    参数：
    - `path_file`：待读取文件路径。

    返回：
    - `dict[str, Any]`：解析后的独立对象。

    异常：
    - `ValueError`：顶层不是对象时抛出。
    """

    # 直接解析完整 UTF-8 文本。
    obj_value = json.loads(path_file.read_text(encoding="utf-8"))  # 当前 JSON 根值

    # 双工件和映射都必须使用版本化对象合同。
    if not isinstance(obj_value, dict):

        # 拒绝无法表达字段合同的数组或标量。
        raise ValueError(f"> ERR: [Python] JSON 顶层必须为对象:{path_file}")

    # 返回供纯构造阶段修改的对象。
    return obj_value

# 验证 receipt 的封闭结构、文件身份和最终原始字节摘要。
def validate_receipt_artifacts(
    path_model: Path,
    path_claims: Path,
    dict_receipt: Mapping[str, Any],
) -> None:
    """验证 receipt 对两份迁移输入的精确绑定。

    参数：
    - `path_model`：待映射 Model 4 原始文件。
    - `path_claims`：待映射 Claims 3 原始文件。
    - `dict_receipt`：迁移批次回执对象。

    返回：
    - `None`：receipt 结构和两份原始字节摘要完全匹配。

    异常：
    - `ValueError`：结构、文件名或摘要不匹配时抛出。
    """

    # schema 封闭根字段防止未知扩展改变回执解释。
    if dict_receipt.get("receipt_version") != "1.0":

        # mapping 只接受当前原子批次合同。
        raise ValueError("> ERR: [Python] migration receipt 版本无效。")

    # receipt 根键必须与 schema 完全一致。
    if set(dict_receipt) != {"receipt_version", "receipt_id", "batch_id", "artifacts"}:

        # 拒绝缺失字段和 schema 外字段。
        raise ValueError("> ERR: [Python] migration receipt 根字段无效。")

    # 批次身份格式阻止空值和非规范身份串联。
    if re.fullmatch(r"MR[0-9a-f]{32}", str(dict_receipt.get("receipt_id", ""))) is None:

        # 非规范 receipt 身份不能参与跨工件关联。
        raise ValueError("> ERR: [Python] migration receipt_id 无效。")

    # 批次身份格式必须与迁移器的随机标识合同一致。
    if re.fullmatch(r"MB[0-9a-f]{32}", str(dict_receipt.get("batch_id", ""))) is None:

        # 非规范 batch 身份无法证明同一次迁移。
        raise ValueError("> ERR: [Python] migration batch_id 无效。")

    # artifacts 必须是封闭的 model/claims 二元对象。
    obj_artifacts = dict_receipt.get("artifacts")  # 回执中的双工件索引

    # 数组或不完整对象不满足回执 schema。
    if not isinstance(obj_artifacts, Mapping):

        # 缺少索引时无法校验任何原始字节。
        raise ValueError("> ERR: [Python] migration receipt 缺少 artifacts。")

    # 额外角色会让批次边界不再唯一。
    if set(obj_artifacts) != {"model", "claims"}:

        # receipt 只允许两份受管迁移工件。
        raise ValueError("> ERR: [Python] migration receipt artifacts 字段无效。")

    # 分别校验 Model 和 Claims 的大小写敏感文件名及原始字节。
    for str_role, path_input in (("model", path_model), ("claims", path_claims)):

        # 当前角色必须提供封闭 file/sha256 对象。
        obj_artifact = obj_artifacts.get(str_role)  # 当前工件回执项

        # 非对象条目不能表达文件身份。
        if not isinstance(obj_artifact, Mapping):

            # 拒绝缺少任一批次成员。
            raise ValueError(f"> ERR: [Python] migration receipt 缺少 {str_role}。")

        # artifact schema 禁止未知字段或缺少摘要。
        if set(obj_artifact) != {"file", "sha256"}:

            # 封闭结构避免其他字段覆盖核心身份语义。
            raise ValueError(f"> ERR: [Python] migration receipt 工件字段无效:{str_role}")

        # Path.name 保留调用方实际大小写，不做平台宽松比较。
        if obj_artifact.get("file") != path_input.name:

            # 错误大小写或跨批次文件名都必须拒绝。
            raise ValueError(f"> ERR: [Python] migration receipt 文件身份不匹配:{str_role}")

        # 对调用方提供文件的最终原始字节重新计算摘要。
        str_hash = hashlib.sha256(path_input.read_bytes()).hexdigest()  # 当前输入真实 SHA-256

        # JSON 重排、空白变化或内容篡改均改变原始摘要。
        if obj_artifact.get("sha256") != str_hash:

            # 不允许以语义等价替代 receipt 绑定的准确字节。
            raise ValueError(f"> ERR: [Python] migration receipt 原始字节不匹配:{str_role}")

# 验证双工件的迁移身份、待办和初始来源状态。
def validate_migration_state(
    path_claims: Path,
    path_receipt: Path,
    dict_model: Mapping[str, Any],
    dict_claims: Mapping[str, Any],
    dict_receipt: Mapping[str, Any],
) -> None:
    """验证双工件仍属于 receipt 声明的未完成迁移批次。

    参数：
    - `path_claims`：Claims 3 输入路径。
    - `path_receipt`：批次回执输入路径。
    - `dict_model`：Model 4 输入对象。
    - `dict_claims`：Claims 3 输入对象。
    - `dict_receipt`：已验证结构的批次回执。

    返回：
    - `None`：身份、待办和来源状态均允许 mapping。

    异常：
    - `ValueError`：输入已完成、跨批次或不是初始迁移候选时抛出。
    """

    # 两份工件都必须保留独立 migration 对象。
    obj_model_migration = dict_model.get("migration")  # Model 4 迁移元数据

    # Claims companion 的身份必须独立读取，禁止借用模型值。
    obj_claims_migration = dict_claims.get("migration")  # companion 独立保存的批次关联域

    # 非对象迁移域无法证明批次关联。
    if not isinstance(obj_model_migration, Mapping) or not isinstance(
        obj_claims_migration,  # Claims 迁移域候选
        Mapping,  # 两份工件都要求对象合同
    ):

        # 拒绝原生工件或已删除迁移元数据的候选。
        raise ValueError("> ERR: [Python] migration 元数据必须为对象。")

    # receipt 是批次身份的唯一外部锚点。
    str_batch_id = str(dict_receipt.get("batch_id", ""))  # 回执声明的共同批次身份

    # 两份工件必须同时引用同一 receipt 身份。
    str_receipt_id = str(dict_receipt.get("receipt_id", ""))  # 回执声明的自身身份

    # Model 和 Claims 的三项迁移身份逐项与 receipt 对齐。
    for obj_migration in (obj_model_migration, obj_claims_migration):

        # 任一身份偏差都表示跨批次拼接或篡改。
        if (
            obj_migration.get("batch_id") != str_batch_id
            or obj_migration.get("receipt_id") != str_receipt_id
            or obj_migration.get("receipt_file") != path_receipt.name
        ):

            # mapping 不接受跨批次或错误回执文件名。
            raise ValueError("> ERR: [Python] migration 批次或 receipt 身份不匹配。")

    # map_features 只能从双工件共同 pending 状态关闭。
    if (
        obj_model_migration.get("state") != "pending"
        or obj_claims_migration.get("state") != "pending"
        or "map_features" not in obj_model_migration.get("pending_actions", [])
        or obj_model_migration.get("claims_companion") != path_claims.name
    ):

        # 拒绝原生、已完成、错误 companion 或缺失待办的输入。
        raise ValueError("> ERR: [Python] mapping 只接受等待 map_features 的 pending 双工件。")

    # 迁移模型必须仍是未封印初始候选，不能二次 mapping。
    obj_provenance = dict_model.get("provenance")  # Model 4 当前来源状态

    # producer 和 artifact_role 一起区分迁移初始工件与普通原生工件。
    if not isinstance(obj_provenance, Mapping) or (
        obj_provenance.get("state"),
        obj_provenance.get("artifact_role"),
        obj_provenance.get("producer"),
    ) != ("pending", "initial", "model4_pipeline"):

        # 已封印或来源角色不同的模型不能重复消费 receipt。
        raise ValueError("> ERR: [Python] mapping 输入必须是未封印迁移初始模型。")

# 验证 mapping 输入确属同一未完成迁移批次。
def validate_migration_batch(
    path_model: Path,
    path_claims: Path,
    path_receipt: Path,
    dict_model: Mapping[str, Any],
    dict_claims: Mapping[str, Any],
    dict_receipt: Mapping[str, Any],
) -> None:
    """验证 mapping 输入确属同一未完成迁移批次。

    参数：
    - `path_model`：Model 4 输入路径。
    - `path_claims`：Claims 3 输入路径。
    - `path_receipt`：migration receipt 输入路径。
    - `dict_model`：Model 4 输入对象。
    - `dict_claims`：Claims 3 输入对象。
    - `dict_receipt`：migration receipt 对象。

    返回：
    - `None`：三份输入可进入 mapping。

    异常：
    - `ValueError`：receipt 或迁移状态不符合合同时抛出。
    """

    # 先验证外部 receipt 与两个磁盘文件的字节绑定。
    validate_receipt_artifacts(
        path_model,  # Model 4 原始输入
        path_claims,  # receipt 必须绑定的 companion 原始文件
        dict_receipt,  # 待验证批次回执
    )

    # 再验证两份 JSON 内部身份与待办状态。
    validate_migration_state(
        path_claims,  # companion 文件名身份来源
        path_receipt,  # 两份工件共同引用的回执文件
        dict_model,  # Model 4 迁移状态
        dict_claims,  # companion 自身保存的迁移身份
        dict_receipt,  # 外部批次身份锚点
    )

# 根据模型章节与证据事实判断技术特征支撑闭包。
def feature_has_closure(
    dict_feature: Mapping[str, Any],
    dict_sections: Mapping[str, set[str]],
    set_evidence_ids: set[str],
) -> bool:
    """判断一个技术特征是否具备章节、证据和技术效果闭包。

    参数：
    - `dict_feature`：当前稳定技术特征。
    - `dict_sections`：章节到证据编号的索引。
    - `set_evidence_ids`：模型正式证据编号集合。

    返回：
    - `bool`：全部闭包条件成立时为真。

    异常：
    - 无。
    """

    # 规范当前特征声明的章节和证据集合。
    set_section_ids = {str(obj_id) for obj_id in dict_feature.get("section_ids", [])}  # 当前特征章节集合

    # 当前特征证据必须来自正式登记表。
    set_feature_evidence = {str(obj_id) for obj_id in dict_feature.get("evidence_ids", [])}  # 当前特征证据集合

    # 每个章节都必须存在且至少绑定一项当前特征证据。
    bool_sections_supported = bool(set_section_ids) and all(  # 当前特征章节证据是否闭包
        str_section_id in dict_sections  # 当前章节必须存在
        and bool(dict_sections[str_section_id] & set_feature_evidence)  # 当前章节必须共享特征证据
        for str_section_id in set_section_ids  # 遍历特征展开章节
    )  # 章节级证据闭包

    # 三类事实和非空技术效果必须同时成立。
    return (
        bool_sections_supported
        and bool(set_feature_evidence)  # 特征必须声明证据
        and set_feature_evidence <= set_evidence_ids  # 证据必须已正式登记
        and bool(dict_feature.get("technical_effects"))  # 特征必须声明技术效果
    )

# 把瞬时特征数组转换为稳定登记表和权利要求引用索引。
def build_feature_registry(
    obj_features: list[Any],
    module_identity: Any,
) -> tuple[list[dict[str, Any]], dict[int, list[str]]]:
    """构造稳定特征登记表和 claim_no 引用索引。

    参数：
    - `obj_features`：瞬时映射特征数组。
    - `module_identity`：正式稳定身份模块。

    返回：
    - `tuple`：特征登记表和权利要求引用索引。

    异常：
    - `ValueError`：任一映射项缺少正式字段时抛出。
    """

    # 输出特征登记按映射顺序构造，但身份不依赖位置。
    list_registry: list[dict[str, Any]] = []  # 新主模型技术特征登记表

    # claim_no 到稳定 feature_id 的多值索引。
    dict_claim_features: dict[int, list[str]] = {}  # 新权利要求特征引用索引

    # 逐项验证瞬时映射并建立稳定身份。
    for dict_source in obj_features:

        # 非对象特征无法表达正式映射字段。
        if not isinstance(dict_source, Mapping):

            # 坏项必须在任何输出发布前阻断。
            raise ValueError("> ERR: [Python] 映射 features 每项必须为对象。")

        # 使用共享规范化规则生成完整 SHA-256 身份。
        str_feature_id = str(module_identity.build_stable_feature_id(dict_source))  # 当前稳定特征编号

        # 正式特征登记只保存 Model 4 schema 字段。
        dict_feature = {
            "feature_id": str_feature_id,  # 当前稳定技术特征身份
            "text": str(dict_source.get("text", dict_source.get("feature", ""))).strip(),  # 当前技术特征正文
            "section_ids": sorted({str(obj_id) for obj_id in dict_source.get("section_ids", [])}),  # 当前展开章节
            "evidence_ids": sorted({  # 当前特征规范证据集合
                str(obj_id)  # 规范化当前证据编号
                for obj_id in dict_source.get(  # 兼容旧证据字段
                    "evidence_ids",  # 首选正式证据字段
                    dict_source.get("support_ids", []),  # 回退旧证据字段
                )
            }),  # 当前支撑证据
            "technical_effects": [  # 当前特征规范效果数组
                str(obj_text)  # 规范化当前效果文本
                for obj_text in dict_source.get("technical_effects", [])  # 遍历映射效果
            ],  # 当前技术效果
        }

        # 空文本、章节或证据留给明确映射错误而非后置 schema 噪声。
        if not dict_feature["text"] or not dict_feature["section_ids"] or not dict_feature["evidence_ids"]:

            # 映射必须足以建立真实支撑闭包。
            raise ValueError("> ERR: [Python] 每项映射必须包含文本、章节和证据。")

        # 保存当前正式特征登记。
        list_registry.append(dict_feature)

        # 同一特征可以进入多个权利要求。
        for obj_claim_no in dict_source.get("claim_nos", []):

            # 权利要求编号必须可稳定转换为正整数。
            int_claim_no = int(obj_claim_no)  # 当前被映射权利要求编号

            # 按映射顺序追加稳定特征编号。
            dict_claim_features.setdefault(int_claim_no, []).append(str_feature_id)

    # 返回主模型登记和 companion 引用的共同来源。
    return list_registry, dict_claim_features

# 把瞬时映射转换为稳定 feature_registry 和 claim 引用。
def build_mapped_pair(
    dict_model: dict[str, Any],
    dict_claims: dict[str, Any],
    dict_mapping: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """构建完成特征映射的新 Model 4 与 Claims 3。

    参数：
    - `dict_model`：pending Model 4。
    - `dict_claims`：pending Claims Map 3。
    - `dict_mapping`：瞬时特征到 claim 编号映射。

    返回：
    - `tuple[dict[str, Any], dict[str, Any]]`：相互引用的新双工件。

    异常：
    - `ValueError`：输入状态或映射结构不符合要求时抛出。
    """

    # 入口只接受明确的 pending 迁移合同。
    if dict_model.get("contract_version") != "4.0" or dict_claims.get("contract_version") != "3.0":

        # 旧版本必须先走正式迁移入口。
        raise ValueError("> ERR: [Python] 映射入口只接受 Model 4 和 Claims 3。")

    # 即使版本正确，已完成工件也不得再次关闭 mapping 待办。
    if (
        dict_model.get("migration", {}).get("state") != "pending"
        or dict_claims.get("migration", {}).get("state") != "pending"
    ):

        # 双工件必须同时保持 pending，禁止半完成组合。
        raise ValueError("> ERR: [Python] 映射入口只接受 pending 迁移双工件。")

    # 映射根必须提供非空特征数组。
    obj_features = dict_mapping.get("features")  # 当前瞬时映射特征根

    # 空映射不能关闭 map_features 待办。
    if not isinstance(obj_features, list) or not obj_features:

        # 要求调用方显式提供每项技术特征。
        raise ValueError("> ERR: [Python] 映射文件必须包含非空 features 数组。")

    # 稳定身份由共享模块统一计算。
    module_identity = load_module("patent_mapping_feature_identity", PATH_FEATURE_IDENTITY)  # 当前稳定身份模块

    # 共享构造器同时产生主模型登记和 companion 引用索引。
    tuple_registry = build_feature_registry(  # 当前登记表和权利要求引用索引
        obj_features,  # 提供已经验证非空的瞬时特征数组
        module_identity,  # 提供正文生成端一致的稳定身份规则
    )  # 当前稳定登记表和引用索引元组

    # 拆出待写入主模型的稳定登记表。
    list_registry = tuple_registry[0]  # 当前稳定技术特征登记表

    # 拆出按权利要求编号组织的特征引用。
    dict_claim_features = tuple_registry[1]  # 当前权利要求特征引用索引

    # 新模型替换空特征登记表。
    dict_model["feature_registry"] = list_registry  # 保存正式稳定特征登记

    # 建立章节到证据的闭包索引。
    dict_sections = {
        str(dict_section.get("id")): {  # 当前章节稳定编号
            str(obj_id)  # 规范化当前章节证据编号
            for obj_id in dict_section.get("evidence_ids", [])  # 遍历章节证据
        }
        for dict_section in dict_model.get("sections", [])  # 遍历主模型章节
        if isinstance(dict_section, Mapping) and dict_section.get("id")  # 排除无身份坏章节
    }  # 当前模型章节证据索引

    # 模型证据登记同时兼容 evidence_id 和旧 id 键。
    set_evidence_ids = {
        str(dict_record.get("evidence_id", dict_record.get("id", "")))  # 兼容正式和旧证据身份
        for dict_record in dict_model.get("evidence_registry", {}).get("records", [])  # 遍历证据登记
        if isinstance(dict_record, Mapping)  # 排除非对象坏记录
    }  # 当前模型正式证据编号

    # 特征身份索引用于逐 claim 派生支撑状态。
    dict_registry = {
        str(dict_item["feature_id"]): dict_item  # 保存当前完整特征记录
        for dict_item in list_registry  # 遍历新稳定特征登记
    }  # 当前稳定特征索引

    # 每条 claim 只从瞬时映射派生 feature_ids 和 support_status。
    for dict_claim in dict_claims.get("claims", []):

        # 非对象记录由发布前 schema 阻断。
        if not isinstance(dict_claim, dict):

            # 跳过坏记录以便 schema 汇总。
            continue

        # 规范去重当前 claim 的稳定特征引用。
        list_feature_ids = list(dict.fromkeys(dict_claim_features.get(int(dict_claim.get("claim_no", 0)), [])))  # 当前 claim 特征编号

        # 写回唯一稳定 feature_ids。
        dict_claim["feature_ids"] = list_feature_ids  # 保存当前 claim 稳定特征引用

        # 收集不满足三层闭包的特征身份。
        list_unsupported = [
            str_feature_id  # 保留当前无支撑特征身份
            for str_feature_id in list_feature_ids  # 遍历当前 claim 特征
            if not feature_has_closure(dict_registry[str_feature_id], dict_sections, set_evidence_ids)  # 排除已闭包特征
        ]  # 当前 claim 无支撑特征

        # 支撑状态完全由当前闭包派生。
        dict_claim["support_status"] = (
            "supported"  # 当前全部特征闭包
            if list_feature_ids and not list_unsupported  # 存在特征且没有缺口
            else "unsupported"  # 空特征或任一缺口
        )  # 当前 claim 派生支撑状态

        # 只在真实缺口存在时保留派生缺口身份。
        if list_unsupported:

            # 无支撑特征用于后续精确补料。
            dict_claim["unsupported_feature_ids"] = list_unsupported  # 保存派生无支撑特征身份

        # 已闭包 claim 不保留旧缺口字段。
        else:

            # 清除迁移阶段可能残留的派生缺口。
            dict_claim.pop("unsupported_feature_ids", None)

    # Claims 只有全部非空且 supported 才完成映射迁移。
    bool_claims_complete = bool(dict_claims.get("claims")) and all(  # 当前权利要求映射是否全部闭包
        isinstance(dict_claim, Mapping)  # 当前 claim 必须可解释
        and bool(dict_claim.get("feature_ids"))  # 当前 claim 必须包含稳定特征
        and dict_claim.get("support_status") == "supported"  # 当前 claim 支撑必须闭包
        for dict_claim in dict_claims.get("claims", [])  # 遍历全部权利要求
    )  # 当前 Claims 3 映射是否闭包

    # Claims 迁移状态由当前闭包派生。
    dict_claims.setdefault("migration", {})["state"] = (  # 保存 companion 派生迁移状态
        "complete" if bool_claims_complete else "pending"  # 根据全部 claim 支撑状态派生
    )

    # 主模型迁移元数据同步 Claims 事实状态。
    obj_migration = dict_model.get("migration")  # 当前 Model 4 迁移对象

    # 迁移对象必须可变，坏类型由 schema 阻断。
    if isinstance(obj_migration, dict):

        # 当前 claims_state 只取决于 companion 闭包。
        obj_migration["claims_state"] = (  # 同步主模型的 companion 闭包事实
            "complete" if bool_claims_complete else "pending"  # 与 companion 当前闭包保持一致
        )

        # map_features 在非空 registry 建立后不再属于待办。
        obj_migration["pending_actions"] = [
            str_action  # 保留映射之外的审查动作
            for str_action in obj_migration.get("pending_actions", [])  # 遍历当前迁移动作
            if str_action != "map_features"  # 排除已完成特征映射
        ]

    # 返回等待完整 schema 和事务发布的双工件。
    return dict_model, dict_claims

# 构造命令行参数解析器。
def build_parser() -> argparse.ArgumentParser:
    """构造正式映射入口参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已经注册五个路径参数的解析器。

    异常：
    - 无。
    """

    # 映射入口只接受显式输入和两个新输出。
    obj_parser = argparse.ArgumentParser(description="Map pending Model 4 and Claims 3 into new artifacts.")  # 当前映射参数解析器

    # 注册 pending Model 4 输入。
    obj_parser.add_argument("--model", required=True)

    # companion 输入必须与主模型迁移工件来自同一批次。
    obj_parser.add_argument("--claims-map", required=True)

    # 批次回执是 pending 双工件的强制信任锚。
    obj_parser.add_argument("--receipt", required=True)

    # 注册瞬时人工或代理映射文件。
    obj_parser.add_argument("--mapping-file", required=True)

    # 注册新的 Model 4 输出。
    obj_parser.add_argument("--model-output", required=True)

    # 第二输出用于承载与新主模型一致的特征引用。
    obj_parser.add_argument("--claims-output", required=True)

    # 返回已完成参数注册的解析器。
    return obj_parser

# 执行构造、完整 schema 和双输出事务发布。
def main() -> int:
    """执行正式 Model 4 特征映射阶段。

    参数：
    - 无。

    返回：
    - `int`：双工件成功发布时为零。

    异常：
    - 输入、schema 或事务发布错误由底层实现上抛。
    """

    # 所有工件位置均由调用方显式给出，禁止依赖工作目录猜测迁移批次。
    obj_args = build_parser().parse_args()  # 本次映射的完整路径合同

    # 主模型保留调用方指定的案件边界，不从 receipt 内容反推实际文件位置。
    path_model = Path(obj_args.model).resolve()  # 待验证的 Model 4 工件

    # companion 必须与主模型分别指定，receipt 同时核对文件名、原始字节、批次身份和待办角色。
    path_claims = Path(obj_args.claims_map).resolve()  # 与主模型成对的 Claims 3 工件

    # 回执是迁移三件套的批次清单，不能由任一待验证工件自行替代。
    path_receipt = Path(obj_args.receipt).resolve()  # 原始字节与批次身份的核对依据

    # 瞬时映射不属于 receipt 保护的迁移三件套，仅在批次通过后参与状态推进。
    path_mapping = Path(obj_args.mapping_file).resolve()  # 本轮特征到 claim 的临时关系

    # 主模型输出使用独立位置，确保失败时原迁移工件保持不可变。
    path_model_output = Path(obj_args.model_output).resolve()  # new-only Model 4 发布目标

    # companion 输出与主模型共享一次原子发布，不允许形成单边映射状态。
    path_claims_output = Path(obj_args.claims_output).resolve()  # 与主工件同步落盘的权利要求结果

    # 碰撞检查覆盖受信任迁移工件和瞬时映射，封闭全部覆盖写入口。
    set_inputs = {path_model, path_claims, path_receipt, path_mapping}  # 不得被发布目标占用的位置

    # 读取前先排除输入输出别名；既有输出由后续原子发布继续执行 new-only 检查。
    if path_model_output in set_inputs or path_claims_output in set_inputs or path_model_output == path_claims_output:

        # 任一别名都会破坏原迁移批次或双工件事务的一致性。
        raise ValueError("> ERR: [Python] 映射输出不得覆盖输入或彼此重合。")

    # 排除输出别名后再读取主模型；批次身份与状态由 receipt 校验阶段统一确认。
    dict_model = read_json_object(path_model)  # receipt 绑定的 Model 4 内容

    # companion 独立解析，防止主模型中的引用替代其真实文件内容。
    dict_claims = read_json_object(path_claims)  # 独立文件声明的 pending companion 状态

    # 回执先于 mapping 读取，确保无效迁移批次不能触发任何状态转换。
    dict_receipt = read_json_object(path_receipt)  # 两份输入的原始字节清单

    # 此门同时绑定 basename、原始 SHA-256、批次身份及 pending/role 合同。
    validate_migration_batch(
        path_model,  # 主工件原始字节来源
        path_claims,  # companion 原始字节来源
        path_receipt,  # 批次清单自身的位置
        dict_model,  # 主工件内部迁移状态
        dict_claims,  # companion 内部迁移状态
        dict_receipt,  # 跨工件身份与摘要合同
    )

    # 只有迁移三件套通过验证后才接纳外部映射，防止旁路推进无效批次。
    dict_mapping = read_json_object(path_mapping)  # 不写回正式工件的转换指令

    # 构建相互引用且状态派生的新双工件。
    tuple_mapped_pair = build_mapped_pair(  # 当前相互引用且状态派生的双工件
        dict_model,  # 提供待映射主模型
        dict_claims,  # 提供待映射权利要求
        dict_mapping,  # 提供本轮特征到 claim 关系
    )  # 当前映射双工件元组

    # 拆出待发布主模型。
    dict_model_output = tuple_mapped_pair[0]  # 映射后主模型候选

    # 拆出待发布 companion。
    dict_claims_output = tuple_mapped_pair[1]  # 映射后权利要求候选

    # 主模型记录新的 companion 文件名。
    dict_model_output["migration"]["claims_companion"] = path_claims_output.name  # 绑定实际 companion 文件名

    # 加载正式验证器并执行两个完整 schema。
    module_validator = load_module("patent_mapping_validator", PATH_VALIDATOR)  # 当前正式结构验证器

    # Model 4 schema finding 在发布前全部阻断。
    list_model_findings = module_validator.validate_model_schema(dict_model_output)  # 映射后主模型结构问题

    # Claims 验证包含业务确认，本阶段只提取 schema finding。
    list_claims_findings = module_validator.validate_claims_map(  # 映射后权利要求完整问题
        dict_claims_output,  # 提供待发布权利要求
        dict_model_output,  # 提供稳定特征事实来源
    )

    # Claims 结构错误使用稳定代码。
    list_claim_schema = [
        dict_item  # 保留当前权利要求结构问题
        for dict_item in list_claims_findings  # 遍历完整权利要求问题
        if dict_item.get("code") == "CLM_SCHEMA"  # 排除待后续审查的业务问题
    ]  # 权利要求结构问题

    # 任一结构错误都禁止双输出事务开始。
    if list_model_findings or list_claim_schema:

        # 映射候选必须完整符合两个 schema。
        raise ValueError("> ERR: [Python] 映射候选未通过完整 schema。")

    # 双工件都准备完成后执行共享无覆盖事务。
    module_atomic = load_module("patent_mapping_atomic_pair", PATH_ATOMIC_PAIR)  # 当前双 JSON 事务模块

    # 第二份冲突会回滚第一份。
    module_atomic.write_json_pair_atomic(path_model_output, dict_model_output, path_claims_output, dict_claims_output)

    # 终端只报告简短成功路径摘要。
    print(f"> INFO: [Python] 已发布映射后的 Model 4 与 Claims 3:{path_model_output}")

    # 返回成功退出码。
    return 0

# 脚本入口把受控输入和事务错误转换为稳定退出码。
if __name__ == "__main__":

    # Windows 重定向输出时固定 UTF-8。
    for obj_stream in (sys.stdout, sys.stderr):

        # 测试替身可能不支持 reconfigure。
        obj_reconfigure = getattr(obj_stream, "reconfigure", None)  # 当前标准流重配置函数

        # 真实文本流可用时统一编码。
        if callable(obj_reconfigure):

            # 中文诊断不得依赖本地代码页。
            obj_reconfigure(encoding="utf-8")

    # 捕获可预期错误并避免输出 Python traceback。
    try:

        # 执行正式映射入口。
        raise SystemExit(main())

    # 输入、模块、JSON 和事务错误统一返回二。
    except (FileExistsError, ImportError, OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as obj_error:

        # stderr 使用项目固定错误前缀。
        print(f"> ERR: [Python] Model 4 映射失败:{obj_error}", file=sys.stderr)

        # 非零退出码表示没有发布双工件。
        raise SystemExit(2) from obj_error
