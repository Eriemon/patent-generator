"""建立并验证 Model 4 工件与案件内容之间的不可混用来源链。"""

# 延迟解析类型注解，保持当前技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库负责摘要、JSON、原子替换、路径边界和类型判断。
import hashlib
import importlib.util
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# Recorder 和 provenance 必须加载同一状态转换实现。
PATH_REVIEW_STATE = Path(__file__).resolve().parents[1] / "review" / "model_review_state.py"  # 共享纯状态转换实现

# 按固定路径加载共享 recorder 状态模块。
def load_review_state_module() -> Any:
    """加载 recorder 使用的唯一状态转换模块。

    参数：
    - 无。

    返回：
    - `Any`：已加载的共享状态转换模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 固定模块位置避免 provenance 复制另一套状态规则。
    obj_spec = importlib.util.spec_from_file_location(  # 当前共享模块规格
        "patent_provenance_review_state",  # 隔离动态模块名称
        PATH_REVIEW_STATE,  # recorder 同源实现路径
    )

    # 无法加载共享实现时必须失败关闭。
    if obj_spec is None or obj_spec.loader is None:

        # 禁止回退到 provenance 私有的近似转换。
        raise ImportError("> ERR: [Python] 无法加载 Model 4 状态转换模块。")

    # 每次验证使用独立模块对象，避免跨案件状态残留。
    obj_module = importlib.util.module_from_spec(obj_spec)  # 当前共享状态模块

    # 由受管加载器执行模块初始化。
    obj_spec.loader.exec_module(obj_module)

    # 返回 recorder 与重放共同消费的实现。
    return obj_module

# 计算文件原始字节摘要，避免文本规范化改变来源链身份。
def calculate_file_sha256(path_file: Path) -> str:
    """计算文件原始字节摘要。

    参数：
    - `path_file`：需要绑定到来源链的现有文件。

    返回：
    - `str`：小写六十四位 SHA-256。

    异常：
    - 文件读取错误由底层实现上抛。
    """

    # 直接读取原始字节，使摘要与磁盘工件一一对应。
    bytes_content = path_file.read_bytes()  # 当前工件原始字节

    # 返回固定小写十六进制摘要供 schema 和链验证复用。
    return hashlib.sha256(bytes_content).hexdigest()

# 读取顶层为对象的 UTF-8 JSON，拒绝无法作为模型处理的标量根。
def load_json_object(path_file: Path) -> dict[str, Any]:
    """读取顶层为对象的 UTF-8 JSON。

    参数：
    - `path_file`：待解析模型或案件配置路径。

    返回：
    - `dict[str, Any]`：独立 JSON 对象。

    异常：
    - `ValueError`：顶层不是对象时抛出。
    """

    # 用固定 UTF-8 解析来源链工件，避免本地代码页改变内容。
    obj_value = json.loads(path_file.read_text(encoding="utf-8"))  # 当前文件 JSON 根值

    # 顶层不是对象时无法继续读取模型或案件字段。
    if not isinstance(obj_value, dict):

        # 抛出包含真实路径的类型边界错误。
        raise ValueError(f"> ERR: [Python] JSON 顶层必须为对象:{path_file}")

    # 返回独立对象供调用方验证或更新。
    return obj_value

# 同目录原子替换内部模型，避免来源链写入留下半文件。
def write_json_replace(path_output: Path, dict_payload: Mapping[str, Any]) -> None:
    """同目录原子替换尚未发布的内部模型。

    参数：
    - `path_output`：pipeline 初始模型或测试隔离输出。
    - `dict_payload`：已经完成来源链更新的模型。

    返回：
    - `None`：替换完成。

    异常：
    - 文件系统错误由底层实现上抛。
    """

    # 固定缩进、Unicode 和结尾换行，保证同一载荷序列化稳定。
    str_text = json.dumps(dict_payload, ensure_ascii=False, indent=2) + "\n"  # 待发布 JSON 文本

    # 在目标目录创建临时文件，使最终替换保持同一文件系统原子性。
    int_descriptor, str_temp_path = tempfile.mkstemp(  # 临时描述符和路径
        prefix=f".{path_output.name}.",  # 与目标关联的临时文件前缀
        suffix=".tmp",  # 明确标识未发布临时文件
        dir=path_output.parent,  # 与目标同目录以支持原子替换
        text=True,  # 以文本模式写入规范 JSON
    )  # 同目录临时文件

    # 把临时路径转为 Path，供替换和失败清理共同使用。
    path_temp = Path(str_temp_path)  # 尚未发布的临时工件路径

    # 无论写入或替换是否失败都必须清理残留临时文件。
    try:

        # 用固定 UTF-8 和 LF 写入完整载荷。
        with os.fdopen(int_descriptor, "w", encoding="utf-8", newline="\n") as obj_file:

            # 一次写入完整规范文本。
            obj_file.write(str_text)

            # 刷新 Python 缓冲区后再同步操作系统文件缓冲。
            obj_file.flush()

            # 确保替换前内容已经持久化。
            os.fsync(obj_file.fileno())

        # 完整临时文件落盘后原子替换内部目标。
        os.replace(path_temp, path_output)

    # 失败或成功后统一清理仍存在的临时路径。
    finally:

        # 替换成功时路径已不存在，失败时删除不完整临时文件。
        if path_temp.exists():

            # 移除未发布临时工件，不影响原目标。
            path_temp.unlink()

# 从案件配置读取稳定身份，阻止相似目录名之间混用模型。
def resolve_case_id(path_case_dir: Path) -> str:
    """读取当前案件稳定身份。

    参数：
    - `path_case_dir`：当前案件根目录。

    返回：
    - `str`：case_slug 优先的稳定身份。

    异常：
    - `ValueError`：案件配置没有稳定身份时抛出。
    """

    # 读取当前案件配置作为身份唯一来源。
    dict_case_config = load_json_object(path_case_dir / "case_config.json")  # 当前案件配置对象

    # 优先使用稳定 slug，旧案件缺失时才退回明确名称。
    str_case_id = str(  # 当前案件稳定身份文本
        dict_case_config.get("case_slug")  # 首选稳定案件 slug
        or dict_case_config.get("case_name")  # 兼容旧案件名称
        or ""  # 缺失身份时保留空值供下方阻断
    ).strip()  # 当前案件稳定标识

    # 空身份无法形成可靠案件绑定。
    if not str_case_id:

        # 明确指出案件配置缺少两个允许的身份字段。
        raise ValueError("> ERR: [Python] case_config.json 缺少 case_slug 或 case_name。")

    # 返回已经去除首尾空白的稳定身份。
    return str_case_id

# 计算正文、预览和 claims 三个固定案件工件摘要。
def build_case_content_hashes(path_case_dir: Path) -> dict[str, str]:
    """计算正文、预览和 claims 的案件内容摘要。

    参数：
    - `path_case_dir`：当前案件根目录。

    返回：
    - `dict[str, str]`：三个固定案件工件的 SHA-256。

    异常：
    - 任一工件缺失时由文件读取上抛。
    """

    # 固定从案件草稿目录读取三类权威内容。
    path_drafts_dir = path_case_dir / "03_drafts"  # 当前案件草稿目录

    # 返回键名与 provenance schema 一致的内容摘要集合。
    return {
        "draft_sha256": calculate_file_sha256(  # 正文原始字节摘要
            path_drafts_dir / "disclosure_draft.md"  # 当前正式交底正文
        ),
        "preview_sha256": calculate_file_sha256(  # 预览原始字节摘要
            path_drafts_dir / "pre_draft_preview.md"  # 当前确认预览
        ),
        "claims_sha256": calculate_file_sha256(  # claims 原始字节摘要
            path_drafts_dir / "claims_map.json"  # 当前 Claims Map 3
        ),
    }

# 把 pipeline 初始模型与当前案件内容一次性封印。
def seal_initial_model_artifact(
    path_case_dir: Path,
    path_model: Path,
    path_draft: Path,
    path_preview: Path,
    path_claims: Path,
) -> dict[str, Any]:
    """封印 pipeline 生成的初始 Model 4。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `path_model`：尚未审查的初始模型。
    - `path_draft`：与模型对应的正文。
    - `path_preview`：当前已确认预览。
    - `path_claims`：当前 Claims Map 3。

    返回：
    - `dict[str, Any]`：已写回来源链的初始模型。

    异常：
    - 路径不属于当前案件或工件缺失时抛出。
    """

    # 规范案件根目录，消除相对路径和父目录跳转差异。
    path_case_resolved = path_case_dir.resolve()  # 当前案件规范根目录

    # 固定允许封印工件所在的草稿目录边界。
    path_drafts_resolved = (path_case_resolved / "03_drafts").resolve()  # 当前规范草稿目录

    # 四个输入都必须真实位于当前案件草稿目录。
    for path_artifact in (path_model, path_draft, path_preview, path_claims):

        # 规范路径不在允许父目录时拒绝跨案件封印。
        if path_drafts_resolved not in path_artifact.resolve().parents:

            # 错误包含越界工件路径，便于定位调用方混用。
            raise ValueError(f"> ERR: [Python] 初始 Model 4 工件不属于当前案件:{path_artifact}")

    # 读取 provenance 写入前的生成器模型，作为根摘要锚点。
    bytes_parent = path_model.read_bytes()  # 初始模型未封印原始字节

    # 根摘要和首个父摘要都绑定同一生成器工件。
    str_parent_hash = hashlib.sha256(bytes_parent).hexdigest()  # 初始生成器模型摘要

    # 从完全相同的父字节解析待封印模型。
    dict_model = json.loads(bytes_parent.decode("utf-8"))  # 待封印 Model 4 对象

    # 非对象模型不能附加 provenance 合同。
    if not isinstance(dict_model, dict):

        # 阻止把数组或标量伪装成 Model 4。
        raise ValueError("> ERR: [Python] 初始 Model 4 顶层必须为对象。")

    # 写入案件身份、三类内容摘要和空审查链，形成初始来源锚点。
    dict_model["provenance"] = {
        "state": "sealed",  # 来源链已经封印
        "artifact_role": "initial",  # pipeline 初始工件角色
        "producer": "model4_pipeline",  # 唯一初始生产者
        "case_id": resolve_case_id(path_case_resolved),  # 当前案件稳定身份
        "parent_model_sha256": str_parent_hash,  # 封印前父模型摘要
        "root_model_sha256": str_parent_hash,  # 全链根模型摘要
        "draft_sha256": calculate_file_sha256(path_draft),  # 当前正文摘要
        "preview_sha256": calculate_file_sha256(path_preview),  # 当前预览摘要
        "claims_sha256": calculate_file_sha256(path_claims),  # 当前 claims 摘要
        "chain": [],  # 初始模型尚无审查跳转
    }  # 初始案件来源链

    # 原子写回已封印模型，避免半写 provenance。
    write_json_replace(path_model, dict_model)

    # 返回与磁盘内容一致的已封印对象。
    return dict_model

# 从已封印父模型推进一跳 recorder 来源链。
def build_review_provenance(
    dict_parent_model: Mapping[str, Any],
    bytes_parent: bytes,
    str_record_id: str,
    path_case_dir: Path,
    path_parent_model: Path,
    path_output_model: Path,
) -> dict[str, Any]:
    """为 recorder 子模型推进一跳来源链。

    参数：
    - `dict_parent_model`：已经封印的父模型。
    - `bytes_parent`：父模型原始字节。
    - `str_record_id`：本次活动记录身份。
    - `path_case_dir`：当前案件根目录。
    - `path_parent_model`：本跳直接父模型路径。
    - `path_output_model`：本跳待发布子模型路径。

    返回：
    - `dict[str, Any]`：子模型应嵌入的来源链。

    异常：
    - `ValueError`：父模型未封印时抛出。
    """

    # 读取父模型来源链，后续只在副本上追加审查跳转。
    obj_provenance = dict_parent_model.get("provenance")  # 父模型来源链值

    # recorder 只能消费已经由 pipeline 封印的父模型。
    if not isinstance(obj_provenance, Mapping) or obj_provenance.get("state") != "sealed":

        # 未封印父模型没有可信案件和内容边界。
        raise ValueError("> ERR: [Python] recorder 输入模型缺少 sealed provenance。")

    # 复制父来源链，禁止 recorder 反向修改调用方对象。
    dict_provenance = dict(obj_provenance)  # 当前子模型来源链副本

    # 复制已有跳转历史，保持前序记录不可变。
    list_chain = list(obj_provenance.get("chain", []))  # 前序审查跳转历史副本

    # 当前新增跳转必须绑定实际父文件原始字节。
    str_parent_hash = hashlib.sha256(bytes_parent).hexdigest()  # 当前父模型摘要

    # 每一跳显式记录父子相对路径，避免把目录内任意 JSON 当作父节点。
    str_parent_path = path_parent_model.resolve().relative_to(path_case_dir.resolve()).as_posix()  # 当前直接父路径

    # 当前输出路径标识本跳唯一子节点。
    str_child_path = path_output_model.resolve().relative_to(path_case_dir.resolve()).as_posix()  # 当前直接子路径

    # 追加本轮记录身份、父路径和父摘要，形成可回放的一跳。
    list_chain.append(
        {
            "record_id": str_record_id,  # 触发本跳的审查记录身份
            "parent_model_path": str_parent_path,  # 本跳直接父文件相对路径
            "parent_model_sha256": str_parent_hash,  # 本跳真实父模型摘要
            "child_model_path": str_child_path,  # 本跳子文件相对路径
        }
    )

    # reviewed 根摘要必须锚定当前案件实际 latest 文件，而非继承自报值。
    path_initial = path_case_dir.resolve() / "03_drafts" / "latest_disclosure_model.json"  # 当前案件实际根模型

    # 子模型角色和生产者切换为 recorder，同时保留根和案件摘要。
    dict_provenance.update(
        {
            "artifact_role": "reviewed",  # recorder 审查后工件角色
            "producer": "record_semantic_review",  # 唯一审查生产者
            "root_model_path": "03_drafts/latest_disclosure_model.json",  # 固定根模型相对路径
            "root_model_sha256": calculate_file_sha256(path_initial),  # 当前根文件原始摘要
            "parent_model_path": str_parent_path,  # 当前直接父文件相对路径
            "parent_model_sha256": str_parent_hash,  # 当前直接父模型摘要
            "chain": list_chain,  # 包含本轮的完整审查链
        }
    )

    # 返回供子模型嵌入的独立来源链。
    return dict_provenance

# 通过真实父文件构造 recorder 子模型，供测试和受控调用复用。
def advance_review_provenance(
    path_parent_model: Path,
    path_output_model: Path,
    str_record_id: str,
) -> dict[str, Any]:
    """通过真实父文件构造一个 recorder 子模型。

    参数：
    - `path_parent_model`：已封印父模型路径。
    - `path_output_model`：测试或 recorder 的新模型路径。
    - `str_record_id`：当前审查记录身份。

    返回：
    - `dict[str, Any]`：已写出的子模型。

    异常：
    - 父模型或输出写入错误由底层实现上抛。
    """

    # 读取真实父文件原始字节，不能从重序列化对象推导父摘要。
    bytes_parent = path_parent_model.read_bytes()  # 当前父模型原始字节

    # 从相同父字节解析子模型基础对象。
    dict_model = json.loads(bytes_parent.decode("utf-8"))  # 待推进的模型对象

    # 测试推进也必须构造 recorder 可接纳的完整审查事实。
    dict_record = {  # 当前测试审查记录
        "review_id": str_record_id,  # 链项声明的稳定身份
        "target_type": "model",  # 覆盖整个模型
        "target_id": "model",  # 模型级固定目标
        "target_hash": "0" * 64,  # 测试记录的确定摘要
        "verdict": "pass",  # 推进链所需通过结论
        "coverage": {  # 五个强制语义覆盖项
            "enablement": True,  # 可实施性已覆盖
            "mechanism": True,  # 机制已覆盖
            "causal_effect": True,  # 因果效果已覆盖
            "terminology": True,  # 术语已覆盖
            "evidence_consistency": True,  # 证据一致性已覆盖
        },
    }

    # 案件根决定独立 Claims companion 的唯一位置。
    path_case_dir = path_parent_model.resolve().parents[1]  # 当前案件根目录

    # 真实 companion 参与共享转换，避免测试绕开 claims 状态规则。
    dict_claims_map = load_json_object(  # 当前案件权利要求 companion
        path_case_dir / "03_drafts" / "claims_map.json"  # recorder 的固定 companion 位置
    )

    # 测试辅助器直接复用生产 recorder 的纯状态转换。
    dict_model = load_review_state_module().build_review_candidate(  # 来源链测试推进后的完整模型状态
        dict_model,  # 已从父字节解析的模型
        dict_record,  # 本跳唯一新增审查记录
        "agent",  # 测试推进使用 agent 审查域
        dict_claims_map,  # 同一案件的权利要求确认 companion
    )

    # 从父文件和输出路径推进一跳来源链。
    dict_model["provenance"] = build_review_provenance(  # 推进后的子模型来源链
        dict_model,  # 已封印父模型对象
        bytes_parent,  # 与父摘要绑定的原始字节
        str_record_id,  # 当前审查记录身份
        path_case_dir,  # 由 03_drafts 父目录定位案件根
        path_parent_model,  # 当前直接父文件
        path_output_model,  # 当前直接子文件
    )  # 子模型完整来源链

    # 原子写入新路径，保持父模型字节不变。
    write_json_replace(path_output_model, dict_model)

    # 返回与输出文件一致的子模型对象。
    return dict_model

# 判断规范子路径是否严格位于允许父目录内。
def is_path_within(path_child: Path, path_parent: Path) -> bool:
    """判断规范路径是否位于指定父目录内。

    参数：
    - `path_child`：待验证工件路径。
    - `path_parent`：允许的目录边界。

    返回：
    - `bool`：路径位于父目录内时为真。

    异常：
    - 无。
    """

    # 同时规范父子路径，拒绝相对跳转和把父目录本身当作文件。
    return path_parent.resolve() in path_child.resolve().parents

# 收集模型四个活动态和历史态数组中的全部记录身份。
def collect_review_record_ids(dict_model: Mapping[str, Any]) -> set[str]:
    """收集模型嵌入的全局审查记录身份。

    参数：
    - `dict_model`：待读取的父或子模型。

    返回：
    - `set[str]`：全部代理审查和人工确认身份。

    异常：
    - 无。
    """

    # 非结构化审查容器没有可验证记录。
    obj_review = dict_model.get("semantic_review")  # 当前语义审查根值

    # 坏类型由 schema 负责，本层返回空集合使链校验失败关闭。
    if not isinstance(obj_review, Mapping):

        # 返回空集合表示当前模型没有可证明的记录转换。
        return set()

    # 四个集合共同构成记录身份的完整审计域。
    tuple_collections = (
        ("agent_reviews", "review_id"),  # 代理活动记录
        ("agent_review_history", "review_id"),  # 代理历史记录
        ("human_confirmations", "confirmation_id"),  # 人工活动确认
        ("human_confirmation_history", "confirmation_id"),  # 人工历史确认
    )  # 记录集合与身份字段

    # 聚合所有结构化记录中的非空身份。
    return {
        str(dict_record.get(str_id_key))  # 当前记录稳定身份
        for str_collection, str_id_key in tuple_collections  # 遍历四类记录集合
        for dict_record in obj_review.get(str_collection, [])  # 遍历当前集合记录
        if isinstance(dict_record, Mapping) and dict_record.get(str_id_key)  # 只接纳结构化非空身份
    }

# 核对单个父子文件只新增链声明的 recorder 记录。
def validate_record_transition(
    dict_parent: Mapping[str, Any],
    dict_child: Mapping[str, Any],
    str_record_id: str,
    dict_claims_map: Mapping[str, Any] | None = None,
) -> None:
    """验证父子模型之间的 recorder 状态转换。

    参数：
    - `dict_parent`：当前跳转父模型。
    - `dict_child`：当前跳转子模型。
    - `str_record_id`：链项声明的新增记录身份。
    - `dict_claims_map`：共享状态转换需要的 Claims companion；可选。

    返回：
    - `None`：子模型恰好新增声明记录且未改写受保护事实域。

    异常：
    - `ValueError`：记录身份或受保护事实域不符合 recorder 转换时抛出。
    """

    # 父子记录集合差集必须恰好等于链项声明身份。
    set_parent_ids = collect_review_record_ids(dict_parent)  # 父模型全部记录身份

    # 子模型集合包含活动态和不可变历史态。
    set_child_ids = collect_review_record_ids(dict_child)  # 子模型全部记录身份

    # recorder 每一跳只能引入一个新的全局记录身份。
    if set_child_ids - set_parent_ids != {str_record_id}:

        # 拒绝伪造 record_id、漏记记录或一跳注入多条记录。
        raise ValueError("> ERR: [Python] reviewed model 链记录转换不匹配。")

    # 子模型必须提供可定位新记录的语义审查域。
    obj_review = dict_child.get("semantic_review")  # 子模型语义审查对象

    # 非对象审查域无法证明记录归属。
    if not isinstance(obj_review, Mapping):

        # 拒绝缺失或类型错误的状态容器。
        raise ValueError("> ERR: [Python] recorder 子模型缺少 semantic_review。")

    # 收集声明身份在四个集合中的全部命中，随后要求唯一。
    list_matches: list[tuple[str, Mapping[str, Any]]] = []  # 新记录集合命中

    # 活动态和历史态全部纳入唯一性检查。
    for str_collection, str_id_key in (
        ("agent_reviews", "review_id"),
        ("agent_review_history", "review_id"),
        ("human_confirmations", "confirmation_id"),
        ("human_confirmation_history", "confirmation_id"),
    ):

        # 遍历当前集合的实际记录。
        for obj_record in obj_review.get(str_collection, []):

            # 只接纳身份与链项声明完全一致的对象。
            if (
                isinstance(obj_record, Mapping)
                and str(obj_record.get(str_id_key, "")) == str_record_id
            ):

                # 保留集合名用于拒绝直接写入历史态。
                list_matches.append((str_collection, obj_record))

    # 一个链项不得零命中或跨集合重复命中。
    if len(list_matches) != 1:

        # 集合归属不唯一会使重放 reviewer type 不确定。
        raise ValueError("> ERR: [Python] recorder 新记录集合归属不唯一。")

    # 唯一命中决定生产转换的 reviewer type。
    str_collection, dict_record = list_matches[0]  # 新记录集合和完整事实

    # agent 活动态映射到 agent 转换。
    if str_collection == "agent_reviews":

        # 活动 agent 记录只能由自动审查状态分支产生。
        str_reviewer_type = "agent"  # 共享转换的自动审查分支选择值

    # human 活动态映射到人工确认转换。
    elif str_collection == "human_confirmations":

        # 活动确认记录只能由人工确认状态分支产生。
        str_reviewer_type = "human"  # 共享转换的人工确认分支选择值

    # 新记录直接进入历史态属于伪造转换。
    else:

        # 历史记录只能由共享转换替代旧活动记录产生。
        raise ValueError("> ERR: [Python] recorder 新记录不得直接进入历史集合。")

    # 重放必须加载 recorder 同源实现，禁止本地近似规则。
    module_state = load_review_state_module()  # 用于来源链重放的受管状态模块

    # 父模型加唯一审查事实应确定除 provenance 外的完整子模型。
    dict_expected = module_state.build_review_candidate(  # 父状态和审查事实确定的规范子模型
        dict_parent,  # 当前磁盘父模型
        dict_record,  # 子模型唯一新增记录
        str_reviewer_type,  # 由集合归属确定的审查域
        dict_claims_map,  # 独立权利要求状态的重放输入
    )

    # provenance 由链封印器独立生成，不属于状态转换比较域。
    dict_expected.pop("provenance", None)

    # 复制观测子模型，避免验证过程改写调用方对象。
    dict_observed = dict(dict_child)  # 待规范比较的实际子模型

    # 从观测值移除同一独立来源域。
    dict_observed.pop("provenance", None)

    # 任何旧活动态、历史、feature 或 migration 篡改都会导致全对象不等。
    if dict_observed != dict_expected:

        # 只新增正确 ID 不足以掩盖其他状态漂移。
        raise ValueError("> ERR: [Python] recorder 子模型不等于共享状态转换结果。")

# 按链项路径回读父子文件并验证有序连续性。
def validate_ordered_chain(
    path_case_dir: Path,
    path_model: Path,
    dict_model: Mapping[str, Any],
    obj_provenance: Mapping[str, Any],
) -> None:
    """验证 reviewed 模型的完整有序父子链。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `path_model`：最终 reviewed 模型路径。
    - `dict_model`：最终 reviewed 模型对象。
    - `obj_provenance`：最终模型来源链。

    返回：
    - `None`：根、每一跳和直接父均可由磁盘重放。

    异常：
    - `ValueError`：任一链路路径、摘要或记录转换不一致时抛出。
    """

    # 固定根节点只能是当前案件实际 latest 文件。
    path_root = path_case_dir.resolve() / "03_drafts" / "latest_disclosure_model.json"  # 当前实际根模型

    # reviewed 自报根路径和摘要必须同时匹配实际根文件。
    if (
        obj_provenance.get("root_model_path") != "03_drafts/latest_disclosure_model.json"
        or obj_provenance.get("root_model_sha256") != calculate_file_sha256(path_root)
    ):

        # 拒绝复制、替换或自报的根锚点。
        raise ValueError("> ERR: [Python] reviewed model 实际根模型锚点不匹配。")

    # 来源链必须是非空数组。
    obj_chain = obj_provenance.get("chain")  # 当前完整链值

    # 非数组或空链不能证明 recorder 产物。
    if not isinstance(obj_chain, list) or not obj_chain:

        # reviewed 工件必须至少包含一个有序跳转。
        raise ValueError("> ERR: [Python] reviewed model 缺少有序来源链。")

    # 第一跳父节点必须从实际根文件开始。
    path_expected_parent = path_root  # 当前跳转预期父文件

    # 逐跳回读磁盘父子工件并验证摘要和转换。
    for dict_link in obj_chain:

        # 每个链项都必须声明完整父子路径、父摘要和记录身份。
        if not isinstance(dict_link, Mapping):

            # 非对象链项没有可验证边。
            raise ValueError("> ERR: [Python] reviewed model 来源链项必须为对象。")

        # 从案件根解析链项相对路径。
        path_parent = path_case_dir.resolve() / str(dict_link.get("parent_model_path", ""))  # 当前链项父文件

        # 当前链项子路径决定下一跳父节点。
        path_child = path_case_dir.resolve() / str(dict_link.get("child_model_path", ""))  # 当前链项子文件

        # 路径必须连续且严格位于当前案件草稿目录。
        if (
            path_parent.resolve() != path_expected_parent.resolve()
            or not is_path_within(path_parent, path_case_dir / "03_drafts")
            or not is_path_within(path_child, path_case_dir / "03_drafts")
        ):

            # 拒绝链重排、路径跳跃和跨案件文件。
            raise ValueError("> ERR: [Python] reviewed model 来源链路径不连续。")

        # 链项摘要必须来自声明的直接父文件原始字节。
        if dict_link.get("parent_model_sha256") != calculate_file_sha256(path_parent):

            # 拒绝借用目录内无关 JSON 的摘要。
            raise ValueError("> ERR: [Python] reviewed model 直接父文件摘要不匹配。")

        # 回读本跳父模型和子模型，验证实际记录转换。
        dict_parent = load_json_object(path_parent)  # 当前跳转父模型

        # 最后一跳子对象使用调用方已读取对象，其余跳转回读磁盘。
        dict_child = (
            dict(dict_model)  # 最终子模型已由入口读取
            if path_child.resolve() == path_model.resolve()  # 当前链项到达最终 reviewed 工件
            else load_json_object(path_child)  # 中间子模型必须仍在磁盘
        )  # 当前跳转子模型

        # 链项记录身份必须对应共享生产状态转换。
        dict_claims_map = load_json_object(  # 当前链重放的同案件 companion
            path_case_dir.resolve() / "03_drafts" / "claims_map.json"  # 案件固定 companion 位置
        )

        # 每一跳都执行完整共享状态重放，而非仅比较记录差集。
        validate_record_transition(
            dict_parent,
            dict_child,
            str(dict_link.get("record_id", "")),
            dict_claims_map,
        )

        # 当前子节点成为下一跳唯一父节点。
        path_expected_parent = path_child  # 下一跳预期父文件

    # 最后一跳必须落到当前待验证文件。
    if path_expected_parent.resolve() != path_model.resolve():

        # 拒绝截断链或把另一子文件冒充最终工件。
        raise ValueError("> ERR: [Python] reviewed model 来源链未到达当前文件。")

    # 顶层直接父字段必须与最后一跳完全一致。
    dict_last = obj_chain[-1]  # 最后一跳链项

    # 路径和摘要双重核对禁止顶层字段与链分叉。
    if (
        obj_provenance.get("parent_model_path") != dict_last.get("parent_model_path")
        or obj_provenance.get("parent_model_sha256") != dict_last.get("parent_model_sha256")
    ):

        # 直接父元数据必须是有序链最后一跳的同一事实。
        raise ValueError("> ERR: [Python] reviewed model 直接父字段与最终链项不一致。")

# 核对模型路径、案件身份、内容摘要和可选 recorder 父链。
def validate_model_for_case(
    path_case_dir: Path,
    path_model: Path,
    *,
    require_reviewed: bool,
) -> dict[str, Any]:
    """核对模型路径、案件身份和内容摘要。

    参数：
    - `path_case_dir`：当前 pipeline 或 recorder 案件目录。
    - `path_model`：待接受的初始或 reviewed 模型。
    - `require_reviewed`：是否要求 recorder 子工件。

    返回：
    - `dict[str, Any]`：通过全部来源链检查的模型。

    异常：
    - `ValueError`：任一信任边界不匹配时抛出。
    """

    # 固定当前案件允许模型所在的规范草稿目录。
    path_drafts_dir = path_case_dir.resolve() / "03_drafts"  # 当前案件模型信任边界

    # 模型必须严格位于当前案件草稿目录，禁止跨案件绝对路径。
    if not is_path_within(path_model, path_drafts_dir):

        # 拒绝当前案件目录外的 reviewed model。
        raise ValueError("> ERR: [Python] reviewed model 必须位于当前案件 03_drafts。")

    # 读取待验证模型根对象。
    dict_model = load_json_object(path_model)  # 当前待验证 Model 4

    # 提取来源链，后续逐项验证其信任边界。
    obj_provenance = dict_model.get("provenance")  # 当前模型来源链值

    # 未封印或错误类型的来源链不能进入案件流水线。
    if not isinstance(obj_provenance, Mapping) or obj_provenance.get("state") != "sealed":

        # 明确拒绝旧合同或人工拼接的未封印模型。
        raise ValueError("> ERR: [Python] Model 4 provenance 未封印。")

    # 来源链案件身份必须与当前案件配置实时一致。
    if str(obj_provenance.get("case_id", "")) != resolve_case_id(path_case_dir):

        # 拒绝从其他案件复制来的模型。
        raise ValueError("> ERR: [Python] Model 4 provenance 案件身份不匹配。")

    # 重新计算当前磁盘正文、预览和 claims 摘要。
    dict_expected_hashes = build_case_content_hashes(path_case_dir)  # 当前案件实时内容摘要

    # 逐项核对来源链登记摘要，任何内容漂移都阻断。
    for str_key, str_expected in dict_expected_hashes.items():

        # 当前登记值必须与实时磁盘内容完全一致。
        if obj_provenance.get(str_key) != str_expected:

            # 错误指出发生漂移的具体摘要字段。
            raise ValueError(f"> ERR: [Python] Model 4 provenance 内容摘要不匹配:{str_key}")

    # pipeline 重入还需验证 recorder 角色、根锚点和每个父工件。
    if require_reviewed:

        # reviewed 模型必须由 recorder 生成且至少包含一跳。
        if (
            obj_provenance.get("artifact_role") != "reviewed"  # 必须是审查后角色
            or obj_provenance.get("producer") != "record_semantic_review"  # 必须来自 recorder
            or not obj_provenance.get("chain")  # 必须至少登记一跳
        ):

            # 拒绝初始模型或伪造 reviewed 标志的模型。
            raise ValueError("> ERR: [Python] pipeline 只接受 recorder reviewed model。")

        # 逐跳回读声明的父子文件，核对路径、原始摘要和 recorder 状态转换。
        validate_ordered_chain(
            path_case_dir,
            path_model,
            dict_model,
            obj_provenance,
        )

    # 返回通过路径、案件、内容和父链全部检查的模型。
    return dict_model

# 为 pipeline 提供只接受 recorder reviewed model 的窄入口。
def validate_reviewed_model_for_case(
    path_case_dir: Path,
    path_reviewed_model: Path,
) -> dict[str, Any]:
    """验证 pipeline 重入使用的 recorder 权威模型。

    参数：
    - `path_case_dir`：当前 pipeline 案件目录。
    - `path_reviewed_model`：调用方给出的 reviewed model。

    返回：
    - `dict[str, Any]`：来源链有效的 Model 4。

    异常：
    - `ValueError`：路径、案件、内容或父链不匹配时抛出。
    """

    # 强制开启 reviewed 父链检查，调用方不能降级为初始模型验证。
    return validate_model_for_case(
        path_case_dir,  # 当前 pipeline 案件目录
        path_reviewed_model,  # 调用方提供的审查后模型
        require_reviewed=True,  # 强制 recorder 角色和父链证明
    )
