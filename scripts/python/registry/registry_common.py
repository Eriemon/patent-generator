"""提供自包含注册表的加载、校验、摘要与 SQLite 公共能力。"""

# 启用延迟注解，保持公共库类型标注在 Python 3.10 及以上版本稳定可用。
from __future__ import annotations

# 标准库
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

# 请求、无命中和注册表状态分别使用稳定退出码供上层自动化判断。
INT_EXIT_OK = 0  # 成功退出码

# 无命中不是注册表损坏，保留独立退出码供查询调用方判断。
INT_EXIT_NO_HIT = 1  # 查询无命中退出码

# 请求错误表示调用方参数或动作不合规。
INT_EXIT_REQUEST = 2  # 请求参数或动作错误退出码

# 注册表错误表示来源或派生索引不可用。
INT_EXIT_REGISTRY = 3  # 注册表缺失、损坏、陈旧或不兼容退出码

# 当前运行时只接受 schema_version 1，防止静默读取未来不兼容结构。
INT_SUPPORTED_SCHEMA_VERSION = 1  # 受支持的注册表 schema 版本

# 注册表需要进入摘要和结构校验的 JSON 权威文件集合。
TUPLE_AUTHORITY_FILES = (  # 相对于 config/registry 的权威文件
    Path("manifest.json"),  # 注册表来源与派生数据库总清单
    Path("commands") / "catalog.json",  # 公共命令权威目录
    Path("workflows") / "catalog.json",  # 组合工作流权威目录
    Path("documents") / "catalog.json",  # Markdown 文档注册元数据
    Path("knowledge") / "index.json",  # 可检索知识结论索引
    Path("governance") / "config.json",  # 文档注册治理配置
    Path("governance") / "reviews.json",  # 当前语义去重审查结论
)

# 注册表协议错误
class RegistryError(Exception):
    """保存可直接映射到 CLI 的注册表错误。

    参数：
    - `str_message`：面向调用方的中文错误正文。
    - `int_exit_code`：稳定 CLI 退出码，默认表示注册表状态错误。

    返回：
    - 无；异常对象由调用方捕获并输出。

    异常：
    - 无。
    """

    # 记录错误正文和对应退出码，供三个 CLI 共享。
    def __init__(self, str_message: str, int_exit_code: int = INT_EXIT_REGISTRY) -> None:
        """初始化注册表错误。

        参数：
        - `str_message`：不含固定日志前缀的错误正文。
        - `int_exit_code`：调用方应返回的退出码。

        返回：
        - 无。

        异常：
        - 无。
        """

        # 将错误正文交给基础异常类，保留标准字符串行为。
        super().__init__(str_message)

        # 保存 CLI 映射所需退出码，避免调用端通过文本猜测错误类型。
        self.int_exit_code = int_exit_code  # 当前错误对应的稳定退出码

# 从 registry 入口文件位置推导正式技能根。
def resolve_skill_root(path_script: Path) -> Path:
    """根据 registry 脚本路径定位技能根。

    参数：
    - `path_script`：位于 `scripts/python/registry/` 的入口文件路径。

    返回：
    - `Path`：包含 `SKILL.md` 与 `config/registry/` 的技能根。

    异常：
    - `RegistryError`：入口不符合预期目录结构时抛出。
    """

    # 解析绝对路径，确保源码副本和安装副本使用同一定位算法。
    path_resolved = path_script.resolve()  # 当前入口的规范绝对路径

    # registry 文件到技能根固定跨越 registry、python、scripts 三层目录。
    path_skill_root = path_resolved.parents[3]  # 当前入口所属技能根目录

    # 以 SKILL.md 和注册表 manifest 双重确认根边界。
    if not (path_skill_root / "SKILL.md").is_file():

        # 阻止异常路径把查询范围扩大到技能目录之外。
        raise RegistryError("> ERR: [Python] 无法从 registry 入口定位技能根")

    # 返回经过结构确认的技能根。
    return path_skill_root

# 返回技能内唯一受管注册表配置根。
def registry_root(path_skill_root: Path) -> Path:
    """构造注册表配置根路径。

    参数：
    - `path_skill_root`：正式技能源码或安装副本根目录。

    返回：
    - `Path`：`config/registry` 目录路径。

    异常：
    - 无。
    """

    # 注册表位置是技能内部固定合同，不从环境变量扩大范围。
    path_registry_root = path_skill_root / "config" / "registry"  # 技能注册表配置根

    # 返回固定位置供加载、查询和治理入口复用。
    return path_registry_root

# 读取 UTF-8 JSON 对象并把解析异常归一化为稳定状态错误。
def read_json_object(path_json: Path) -> dict[str, Any]:
    """读取一个必须为对象的 JSON 文件。

    参数：
    - `path_json`：待读取 JSON 路径。

    返回：
    - `dict[str, Any]`：解析后的顶层对象。

    异常：
    - `RegistryError`：文件缺失、编码错误、JSON 损坏或顶层非对象时抛出。
    """

    # 缺失权威文件时给出相对明确的状态诊断。
    if not path_json.is_file():

        # 缺少事实源属于注册表不完整，不能降级为空对象继续查询。
        raise RegistryError(f"> ERR: [Python] 缺少注册表 JSON：{path_json.as_posix()}")

    # 读取并解析 JSON，统一捕获文件和语法错误。
    try:

        # JSON 权威统一使用 UTF-8，避免平台默认编码影响摘要和解析。
        dict_payload = json.loads(path_json.read_text(encoding="utf-8"))  # 当前 JSON 顶层载荷

    # 文件系统或 JSON 解析失败都表示事实源不可用。
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:

        # 保留文件位置但不暴露无关堆栈，便于 CLI 使用稳定协议报告。
        raise RegistryError(f"> ERR: [Python] 注册表 JSON 无法读取：{path_json.as_posix()}：{exc}") from exc

    # 所有权威文件都要求顶层对象，避免不同入口产生不一致解释。
    if not isinstance(dict_payload, dict):

        # 顶层类型不兼容时阻止继续构建派生索引。
        raise RegistryError(f"> ERR: [Python] 注册表 JSON 顶层必须是对象：{path_json.as_posix()}")

    # 返回通过基础结构检查的对象。
    return dict_payload

# 将 JSON 对象编码为跨换行风格稳定的规范字节。
def canonical_json_bytes(dict_payload: dict[str, Any]) -> bytes:
    """生成确定性的 UTF-8 JSON 字节。

    参数：
    - `dict_payload`：已解析的 JSON 顶层对象。

    返回：
    - `bytes`：排序键、紧凑分隔符和 UTF-8 编码的规范字节。

    异常：
    - `TypeError`：对象包含不可序列化值时传播。
    """

    # 规范序列化忽略原文件 CRLF/LF 与缩进差异，只对语义内容计算摘要。
    str_canonical = json.dumps(  # 当前对象的规范 JSON 文本
        dict_payload,  # 待规范化的权威对象
        ensure_ascii=False,  # 保留中文语义供人工诊断
        sort_keys=True,  # 键顺序稳定以支持可复现摘要
        separators=(",", ":"),  # 移除非语义空白
    )

    # 编码为 UTF-8，形成跨平台一致的摘要输入。
    return str_canonical.encode("utf-8")

# 计算忽略 CRLF/LF 平台差异的 Markdown 内容哈希。
def calculate_markdown_hash(path_document: Path) -> str:
    """返回已注册 Markdown 的规范 SHA-256。

    参数：
    - `path_document`：技能内已注册 Markdown 文件路径。

    返回：
    - `str`：以 UTF-8 和 LF 规范化后的六十四位 SHA-256。

    异常：
    - `RegistryError`：文档无法按 UTF-8 读取时抛出。
    """

    # 读取正文时显式归一化所有常见换行序列。
    try:

        # UTF-8 文本是 Markdown 注册的唯一编码合同。
        str_text = path_document.read_text(encoding="utf-8")  # 当前 Markdown 正文

    # 文件系统和编码错误统一进入注册表状态协议。
    except (OSError, UnicodeError) as exc:

        # 诊断只暴露受管文档路径和底层错误摘要。
        raise RegistryError(f"> ERR: [Python] 已注册 Markdown 无法读取：{path_document.as_posix()}：{exc}") from exc

    # Python 通用换行通常已转为 LF，显式替换保证算法合同自说明。
    str_normalized = str_text.replace("\r\n", "\n").replace("\r", "\n")  # LF 规范正文

    # 规范文本按 UTF-8 编码后计算稳定摘要。
    return hashlib.sha256(str_normalized.encode("utf-8")).hexdigest()

# 校验列表字段并返回对象记录，集中阻断空项与错误类型。
def require_object_list(
    dict_payload: dict[str, Any],
    str_key: str,
    path_source: Path,
) -> list[dict[str, Any]]:
    """读取必须由对象组成的列表字段。

    参数：
    - `dict_payload`：包含目标字段的 JSON 对象。
    - `str_key`：待读取列表字段名。
    - `path_source`：用于错误诊断的事实源路径。

    返回：
    - `list[dict[str, Any]]`：通过类型检查的记录列表。

    异常：
    - `RegistryError`：字段缺失、非列表或包含非对象元素时抛出。
    """

    # 读取原始字段，不以空列表掩盖缺失合同。
    obj_records = dict_payload.get(str_key)  # 当前字段原始值

    # 顶层集合必须真实存在且为列表。
    if not isinstance(obj_records, list):

        # 明确指出来源和字段，缩短权威 JSON 修复路径。
        raise RegistryError(f"> ERR: [Python] 注册字段错误：{path_source.as_posix()} 的 {str_key} 必须是列表")

    # 逐项确认对象类型，防止后续字段访问产生非治理异常。
    if any(not isinstance(obj_record, dict) for obj_record in obj_records):

        # 非对象成员会破坏统一记录协议，必须阻断索引构建。
        raise RegistryError(f"> ERR: [Python] 注册字段错误：{path_source.as_posix()} 的 {str_key} 只能包含对象")

    # 类型收窄后返回列表副本，避免调用方修改解析对象的原始容器。
    list_records = [dict(obj_record) for obj_record in obj_records]  # 通过类型检查的记录副本

    # 返回供标识和关系检查使用的对象集合。
    return list_records

# 校验记录必需文本字段并提取稳定标识集合。
def validate_record_ids(
    list_records: list[dict[str, Any]],
    str_kind: str,
    tuple_required_fields: tuple[str, ...],
) -> set[str]:
    """验证记录字段与标识唯一性。

    参数：
    - `list_records`：同类注册记录列表。
    - `str_kind`：用于诊断的记录类型。
    - `tuple_required_fields`：每条记录必须具备的非空字段。

    返回：
    - `set[str]`：当前类型全部稳定标识。

    异常：
    - `RegistryError`：字段缺失、文本为空或标识重复时抛出。
    """

    # 逐项收集标识，使用集合检测重复。
    set_record_ids: set[str] = set()  # 当前记录类型的稳定标识集合

    # 每条记录都必须满足相同的最小可检索合同。
    for dict_record in list_records:

        # 逐字段检查存在性与非空语义。
        for str_field in tuple_required_fields:

            # 字符串字段必须包含可见文本，列表字段必须至少有一个成员。
            obj_field = dict_record.get(str_field)  # 当前必需字段原始值

            # 空值或空容器不能进入派生索引。
            if obj_field is None or obj_field == "" or obj_field == []:

                # 诊断包含记录类型和字段名，便于直接修复 JSON 权威。
                raise RegistryError(f"> ERR: [Python] 记录字段缺失：{str_kind} 记录缺少非空字段 {str_field}")

        # 稳定标识必须是非空字符串。
        str_record_id = dict_record.get("id", "")  # 当前记录稳定标识

        # 非字符串标识无法作为 SQLite 主键或关系目标。
        if not isinstance(str_record_id, str) or not str_record_id:

            # 阻止隐式字符串转换掩盖 JSON 类型错误。
            raise RegistryError(f"> ERR: [Python] 记录标识错误：{str_kind} 记录 id 必须是非空字符串")

        # 同类标识不得重复，否则查询命中和工作流引用会产生歧义。
        if str_record_id in set_record_ids:

            # 重复标识属于事实源冲突，不能靠数据库覆盖解决。
            raise RegistryError(f"> ERR: [Python] 记录标识重复：{str_kind} 标识 {str_record_id}")

        # 登记已验证标识，供后续记录和关系检查复用。
        set_record_ids.add(str_record_id)

    # 返回完整标识集合供跨目录关系校验使用。
    return set_record_ids

# 读取七份固定 JSON 权威，保持路径选择集中且不可由查询参数改写。
def load_authorities(path_root: Path) -> dict[str, dict[str, Any]]:
    """读取注册表全部 JSON 权威对象。

    参数：
    - `path_root`：技能内固定注册表配置根。

    返回：
    - `dict[str, dict[str, Any]]`：按职责命名的七份 JSON 对象。

    异常：
    - `RegistryError`：任一权威文件不可读或顶层非对象时抛出。
    """

    # 键名对应内存模型职责，值始终来自受管固定路径。
    return {
        "manifest": read_json_object(path_root / "manifest.json"),  # 注册表总清单
        "commands": read_json_object(path_root / "commands" / "catalog.json"),  # 命令目录
        "workflows": read_json_object(path_root / "workflows" / "catalog.json"),  # 工作流目录
        "documents": read_json_object(path_root / "documents" / "catalog.json"),  # 文档目录
        "knowledge": read_json_object(path_root / "knowledge" / "index.json"),  # 知识索引
        "governance": read_json_object(path_root / "governance" / "config.json"),  # 治理配置
        "reviews": read_json_object(path_root / "governance" / "reviews.json"),  # 治理评审
    }

# 校验公共命令入口边界和文件存在性。
def validate_command_entries(path_skill_root: Path, list_commands: list[dict[str, Any]]) -> None:
    """阻断越界或缺失的公共命令入口。

    参数：
    - `path_skill_root`：当前技能副本根目录。
    - `list_commands`：已通过基础字段检查的命令记录。

    返回：
    - 无。

    异常：
    - `RegistryError`：入口越界或文件缺失时抛出。
    """

    # 每个入口都必须是技能内真实 Python 文件。
    for dict_command in list_commands:

        # 入口使用技能内 POSIX 相对路径。
        str_entrypoint = str(dict_command["entrypoint"])  # 当前命令入口

        # 父级穿越和非 Python 脚本根都超出执行边界。
        tuple_entry_parts = Path(str_entrypoint).parts  # 当前入口路径组成部分

        # 入口前两级必须精确匹配 scripts/python。
        bool_python_entry = tuple_entry_parts[:2] == ("scripts", "python")  # Python 入口根判定

        # 最终边界判定同时阻断根目录不符和父级穿越。
        if not bool_python_entry or ".." in tuple_entry_parts:

            # 越界目录不能进入能力发现结果。
            raise RegistryError(f"> ERR: [Python] 命令入口越出技能 Python 边界：{str_entrypoint}")

        # 源码、dist 和安装副本都必须携带登记入口。
        if not (path_skill_root / str_entrypoint).is_file():

            # 命令标识连接目录事实和缺失路径。
            raise RegistryError(f"> ERR: [Python] 命令入口不存在：{dict_command['id']} -> {str_entrypoint}")

# 校验工作流仅组合已注册公共命令。
def validate_workflow_steps(list_workflows: list[dict[str, Any]], set_command_ids: set[str]) -> None:
    """阻断工作流中的未知命令关系。

    参数：
    - `list_workflows`：已通过基础字段检查的工作流记录。
    - `set_command_ids`：全部已注册命令标识。

    返回：
    - 无。

    异常：
    - `RegistryError`：工作流引用未知命令时抛出。
    """

    # 逐个工作流保留未知步骤的完整诊断。
    for dict_workflow in list_workflows:

        # 过滤未出现在命令目录中的步骤标识。
        list_unknown_steps = [  # 当前工作流未知步骤
            str_step  # 原始命令标识
            for str_step in dict_workflow["steps"]  # 声明顺序中的步骤
            if str_step not in set_command_ids  # 未注册关系目标
        ]

        # 任一断裂关系都会使组合流程不可用。
        if list_unknown_steps:

            # 报告工作流和全部未知步骤。
            raise RegistryError(f"> ERR: [Python] 工作流引用未知命令：{dict_workflow['id']} -> {list_unknown_steps}")

# 校验 Markdown 注册边界、存在性和逐字节哈希。
def validate_documents(path_skill_root: Path, list_documents: list[dict[str, Any]]) -> None:
    """阻断越界、缺失或哈希陈旧的已注册文档。

    参数：
    - `path_skill_root`：当前技能副本根目录。
    - `list_documents`：已通过基础字段检查的文档记录。

    返回：
    - 无。

    异常：
    - `RegistryError`：文档越界、缺失或哈希陈旧时抛出。
    """

    # 文档事实逐项匹配目录元数据。
    for dict_document in list_documents:

        # 文档仅允许 SKILL.md 和 references 子树。
        str_document_path = str(dict_document["path"])  # 当前文档相对路径

        # 组合允许根判定，避免长条件降低可读性。
        bool_allowed_root = (  # 文档是否位于允许根
            str_document_path == "SKILL.md"  # 技能入口文档
            or str_document_path.startswith("references/")  # 受管参考文档
        )

        # 父级穿越或其他根目录都违反自包含边界。
        if ".." in Path(str_document_path).parts or not bool_allowed_root:

            # 报告越界相对路径，不扩大文件读取范围。
            raise RegistryError(f"> ERR: [Python] 文档路径越出允许范围：{str_document_path}")

        # 将已验证相对路径定位到当前技能副本。
        path_document = path_skill_root / str_document_path  # 当前 Markdown 真实路径

        # 缺失正文不能继续被视为已注册事实。
        if not path_document.is_file():

            # 稳定 id 和路径共同定位缺失项。
            raise RegistryError(f"> ERR: [Python] 已注册文档不存在：{dict_document['id']} -> {str_document_path}")

        # 规范文本哈希忽略 Git 跨平台换行转换，但保留全部语义字符。
        str_actual_hash = calculate_markdown_hash(path_document)  # 当前正文规范 SHA-256

        # 正文变化必须经显式文档治理刷新。
        if str_actual_hash != dict_document["sha256"]:

            # 查询和构建均 fail closed，避免静默更新元数据。
            raise RegistryError(f"> ERR: [Python] 已注册文档哈希陈旧：{dict_document['id']}")

# 校验知识条目的来源文档关系。
def validate_knowledge_sources(list_knowledge: list[dict[str, Any]], set_document_ids: set[str]) -> None:
    """阻断知识条目中的未知文档关系。

    参数：
    - `list_knowledge`：已通过基础字段检查的知识记录。
    - `set_document_ids`：全部已注册文档标识。

    返回：
    - 无。

    异常：
    - `RegistryError`：知识条目引用未知文档时抛出。
    """

    # 每条结论必须追溯到现有文档标识。
    for dict_entry in list_knowledge:

        # 收集目录中不存在的来源目标。
        list_unknown_documents = [  # 当前知识条目的断裂来源
            str_document_id  # 原始来源文档标识
            for str_document_id in dict_entry["document_ids"]  # 声明的来源关系
            if str_document_id not in set_document_ids  # 未注册文档目标
        ]

        # 任一断裂来源都会使结论不可追溯。
        if list_unknown_documents:

            # 报告知识标识和全部未知来源。
            raise RegistryError(f"> ERR: [Python] 知识条目引用未知文档：{dict_entry['id']} -> {list_unknown_documents}")

# 从权威对象收窄四类可检索记录。
def extract_registry_records(
    path_root: Path,
    dict_authorities: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """提取四类通过容器类型检查的注册记录。

    参数：
    - `path_root`：技能内固定注册表配置根。
    - `dict_authorities`：按职责命名的 JSON 权威对象。

    返回：
    - `dict[str, list[dict[str, Any]]]`：四类对象记录列表。

    异常：
    - `RegistryError`：记录字段不是对象列表时抛出。
    """

    # 每类记录保留自身事实源路径供错误诊断。
    return {
        "commands": require_object_list(
            dict_authorities["commands"], "commands", path_root / "commands" / "catalog.json"
        ),  # 公共命令记录
        "workflows": require_object_list(
            dict_authorities["workflows"], "workflows", path_root / "workflows" / "catalog.json"
        ),  # 组合工作流记录
        "documents": require_object_list(
            dict_authorities["documents"], "documents", path_root / "documents" / "catalog.json"
        ),  # Markdown 文档记录
        "knowledge": require_object_list(
            dict_authorities["knowledge"], "entries", path_root / "knowledge" / "index.json"
        ),  # 可检索知识记录
    }

# 校验四类记录字段并收集稳定标识。
def collect_registry_ids(
    dict_records: dict[str, list[dict[str, Any]]],
) -> dict[str, set[str]]:
    """返回通过必需字段与唯一性检查的标识集合。

    参数：
    - `dict_records`：四类已经收窄容器类型的注册记录。

    返回：
    - `dict[str, set[str]]`：按类型命名的稳定标识集合。

    异常：
    - `RegistryError`：必需字段缺失、为空或标识重复时抛出。
    """

    # 各类型字段合同保持在一个映射中便于审阅。
    dict_required_fields = {  # 四类记录必需字段
        "command": ("id", "category", "title", "summary", "aliases", "entrypoint"),  # 命令字段
        "workflow": ("id", "title", "summary", "aliases", "steps", "boundaries"),  # 工作流字段
        "document": ("id", "path", "title", "kind", "summary", "keywords", "sha256"),  # 文档字段
        "knowledge": ("id", "title", "summary", "keywords", "document_ids"),  # 知识字段
    }

    # 统一验证器返回每类稳定标识集合。
    return {
        "command": validate_record_ids(
            dict_records["commands"], "command", dict_required_fields["command"]
        ),  # 命令关系目标
        "workflow": validate_record_ids(
            dict_records["workflows"], "workflow", dict_required_fields["workflow"]
        ),  # 工作流唯一标识
        "document": validate_record_ids(
            dict_records["documents"], "document", dict_required_fields["document"]
        ),  # 文档关系目标
        "knowledge": validate_record_ids(
            dict_records["knowledge"], "knowledge", dict_required_fields["knowledge"]
        ),  # 知识唯一标识
    }

# 加载并验证注册表全部权威对象。
def load_registry(path_skill_root: Path) -> dict[str, Any]:
    """加载注册表并执行结构、路径、哈希与关系校验。

    参数：
    - `path_skill_root`：正式技能源码、dist 或安装副本根目录。

    返回：
    - `dict[str, Any]`：通过全部检查的完整注册表模型。

    异常：
    - `RegistryError`：来源、入口、文档或关系不合规时抛出。
    """

    # 固定配置根决定全部权威读取位置。
    path_root = registry_root(path_skill_root)  # 当前注册表配置根

    # 一次读取七份 JSON，后续只在内存中收窄字段。
    dict_authorities = load_authorities(path_root)  # 注册表 JSON 权威对象

    # 运行时拒绝未来或旧版 schema。
    if dict_authorities["manifest"].get("schema_version") != INT_SUPPORTED_SCHEMA_VERSION:

        # 不兼容 schema 不能由当前运行时猜测解释。
        raise RegistryError("> ERR: [Python] 注册表 schema_version 不受当前运行时支持")

    # 收窄记录容器并验证各类字段和标识唯一性。
    dict_records = extract_registry_records(path_root, dict_authorities)  # 四类注册记录

    # 标识映射供数量、入口和跨目录关系检查复用。
    dict_ids = collect_registry_ids(dict_records)  # 四类稳定标识集合

    # manifest 声明数量必须匹配真实公共命令目录。
    if dict_authorities["manifest"].get("public_entrypoint_count") != len(dict_records["commands"]):

        # 数量漂移会误导能力发现。
        raise RegistryError("> ERR: [Python] manifest public_entrypoint_count 与命令目录不一致")

    # 校验每个公共命令入口的技能内文件事实。
    validate_command_entries(path_skill_root, dict_records["commands"])

    # 校验工作流步骤只引用已注册命令。
    validate_workflow_steps(dict_records["workflows"], dict_ids["command"])

    # 校验 Markdown 路径、存在性和正文哈希。
    validate_documents(path_skill_root, dict_records["documents"])

    # 校验知识条目保留可追溯文档来源。
    validate_knowledge_sources(dict_records["knowledge"], dict_ids["document"])

    # 返回完整且经过验证的内存模型。
    return {
        "manifest": dict_authorities["manifest"],  # schema 与派生数据库总清单
        "commands": dict_records["commands"],  # 可直接发现的公共命令
        "workflows": dict_records["workflows"],  # 串联命令的组合流程
        "documents": dict_records["documents"],  # 受管 Markdown 注册元数据
        "knowledge": dict_records["knowledge"],  # 带来源关系的治理结论
        "governance": dict_authorities["governance"],  # 权威边界与重复规则
        "reviews": dict_authorities["reviews"],  # 当前语义审查证据
        "ids": dict_ids,  # 供关系校验复用的标识映射
    }

# 计算全部 JSON 权威与 Markdown 正文的可复现摘要。
def calculate_source_digest(path_skill_root: Path) -> str:
    """计算注册表权威源摘要。

    参数：
    - `path_skill_root`：正式技能源码或安装副本根目录。

    返回：
    - `str`：六十四位小写 SHA-256。

    异常：
    - `RegistryError`：权威 JSON 或文档无法读取时抛出。
    """

    # 使用 SHA-256 累积带路径边界的规范内容。
    obj_digest = hashlib.sha256()  # 注册表来源摘要累加器

    # 注册表配置根用于定位固定权威文件集合。
    path_root = registry_root(path_skill_root)  # 来源摘要使用的配置根

    # JSON 通过解析后规范编码消除 CRLF、缩进和键顺序差异。
    for path_relative in TUPLE_AUTHORITY_FILES:

        # 加入路径名可防止内容相同的不同来源互换位置。
        obj_digest.update(path_relative.as_posix().encode("utf-8"))

        # 读取对象并加入规范 JSON 字节。
        dict_payload = read_json_object(path_root / path_relative)  # 当前权威 JSON 对象

        # 规范内容决定数据库新鲜度。
        obj_digest.update(canonical_json_bytes(dict_payload))

    # 文档正文变化也必须使派生数据库变为陈旧。
    dict_documents = read_json_object(path_root / "documents" / "catalog.json")  # 文档目录对象

    # 遍历目录声明顺序，将文档路径与规范换行正文加入摘要。
    for dict_document in require_object_list(dict_documents, "documents", path_root / "documents" / "catalog.json"):

        # 文档相对路径参与边界摘要。
        str_document_path = str(dict_document.get("path", ""))  # 摘要中的 Markdown 相对路径

        # 路径先于正文进入累加器，避免正文互换位置保持同摘要。
        obj_digest.update(str_document_path.encode("utf-8"))

        # 读取 UTF-8 Markdown 并统一 CRLF/LF，使发布平台换行转换不误报陈旧。
        try:

            # 规范化换行但保留全部语义字符和空白。
            str_document_text = (path_skill_root / str_document_path).read_text(encoding="utf-8")  # 摘要输入正文

        # 文档读取失败时注册表来源摘要不可用。
        except (OSError, UnicodeError) as exc:

            # 提升为统一状态错误供 CLI 返回退出码 3。
            raise RegistryError(f"> ERR: [Python] 无法读取已注册文档：{str_document_path}：{exc}") from exc

        # 所有平台使用 LF 参与摘要，避免仅换行风格造成假陈旧。
        str_normalized_text = str_document_text.replace("\r\n", "\n").replace("\r", "\n")  # 规范换行正文

        # 将规范正文加入最终来源摘要。
        obj_digest.update(str_normalized_text.encode("utf-8"))

    # 返回小写十六进制摘要供 metadata 表和检查命令比较。
    return obj_digest.hexdigest()

# 将单个权威对象转换为统一 SQLite 检索行。
def create_search_record(
    dict_source: dict[str, Any],
    str_kind: str,
    str_category: str,
    str_aliases: str,
    str_source: str,
    str_extra_text: str = "",
) -> dict[str, str]:
    """构造不包含执行行为的统一文本检索记录。

    参数：
    - `dict_source`：包含 id、title 和 summary 的权威记录。
    - `str_kind`：统一实体类型。
    - `str_category`：类型内分类。
    - `str_aliases`：展平的别名或关键词。
    - `str_source`：可追溯来源文本。
    - `str_extra_text`：类型特有的补充检索文本。

    返回：
    - `dict[str, str]`：SQLite 主表和 FTS5 共用记录。

    异常：
    - `KeyError`：调用方传入未验证权威记录时传播。
    """

    # 提取三项所有实体共有的可读字段。
    str_record_id = str(dict_source["id"])  # 当前实体稳定标识

    # 标题用于人类展示和全文检索。
    str_title = str(dict_source["title"])  # 当前实体展示标题

    # 摘要承载能力或知识结论的主要语义。
    str_summary = str(dict_source["summary"])  # 当前实体检索摘要

    # 合并结构化字段供 FTS5 与 LIKE 使用。
    str_search_text = " ".join((  # 当前实体完整检索文本
        str_record_id,  # 稳定标识
        str_title,  # 可读标题
        str_summary,  # 能力或知识摘要
        str_aliases,  # 别名或关键词
        str_source,  # 入口、步骤、路径或来源
        str_extra_text,  # 类型特有补充边界
    ))

    # 统一字段使查询层无需理解四份 JSON 的差异。
    return {
        "id": str_record_id,  # 结构化稳定标识
        "kind": str_kind,  # 实体类型过滤值
        "category": str_category,  # 类型内分类过滤值
        "title": str_title,  # 结构化展示标题
        "summary": str_summary,  # 结构化摘要
        "aliases": str_aliases,  # 展平别名或关键词
        "source": str_source,  # 可追溯来源
        "search_text": str_search_text,  # 完整检索文本
    }

# 将四类权威记录归一化为 SQLite 检索行。
def build_search_records(dict_registry: dict[str, Any]) -> list[dict[str, str]]:
    """构造固定类别顺序的统一检索记录。

    参数：
    - `dict_registry`：经过完整校验的注册表模型。

    返回：
    - `list[dict[str, str]]`：命令、工作流、文档、知识检索行。

    异常：
    - 无；输入已经由 `load_registry` 验证。
    """

    # 命令保留真实分类、别名和 Python 入口。
    list_commands = [  # 命令检索行
        create_search_record(  # 当前命令转换结果
            dict_command, "command", str(dict_command["category"]),  # 命令类型与真实分类
            " ".join(str(item) for item in dict_command["aliases"]),  # 命令别名文本
            str(dict_command["entrypoint"]),  # Python 入口来源
        )
        for dict_command in dict_registry["commands"]  # 按权威目录顺序遍历命令
    ]

    # 工作流使用步骤作为来源，并把不执行边界加入检索文本。
    list_workflows = [  # 工作流检索行
        create_search_record(  # 当前工作流转换结果
            dict_workflow, "workflow", "workflow",  # 工作流固定类型和分类
            " ".join(str(item) for item in dict_workflow["aliases"]),  # 工作流别名文本
            " | ".join(str(item) for item in dict_workflow["steps"]),  # 已注册命令步骤
            " ".join(str(item) for item in dict_workflow["boundaries"]),  # 不执行边界
        )
        for dict_workflow in dict_registry["workflows"]  # 按声明顺序遍历工作流
    ]

    # 文档以关键词和 Markdown 相对路径支持主题发现。
    list_documents = [  # 文档检索行
        create_search_record(  # 当前文档转换结果
            dict_document, "document", str(dict_document["kind"]),  # 文档类型和治理种类
            " ".join(str(item) for item in dict_document["keywords"]),  # 文档主题词
            str(dict_document["path"]),  # Markdown 相对路径来源
        )
        for dict_document in dict_registry["documents"]  # 按注册顺序遍历文档
    ]

    # 知识条目以来源文档 id 保持结论可追溯。
    list_knowledge = [  # 知识检索行
        create_search_record(  # 当前知识条目转换结果
            dict_entry, "knowledge", "knowledge",  # 知识固定类型和分类
            " ".join(str(item) for item in dict_entry["keywords"]),  # 知识主题词
            " ".join(str(item) for item in dict_entry["document_ids"]),  # 来源文档标识
        )
        for dict_entry in dict_registry["knowledge"]  # 按索引顺序遍历知识条目
    ]

    # 固定拼接顺序保证相同来源重建获得稳定 rowid。
    return list_commands + list_workflows + list_documents + list_knowledge

# 原子构建 SQLite 主表、FTS5 索引与来源摘要元数据。
def write_database(path_skill_root: Path, dict_registry: dict[str, Any]) -> dict[str, Any]:
    """原子重建派生 SQLite 注册表。

    参数：
    - `path_skill_root`：正式技能源码、dist 或隔离副本根目录。
    - `dict_registry`：已经通过完整校验的注册表模型。

    返回：
    - `dict[str, Any]`：数据库路径、来源摘要与记录数量。

    异常：
    - `RegistryError`：SQLite 不支持 FTS5 trigram 或写入失败时抛出。
    """

    # 从 manifest 读取固定派生数据库文件名。
    path_root = registry_root(path_skill_root)  # SQLite 构建使用的配置根

    # 数据库目标不得由命令行改写，保持技能自包含边界。
    path_database = path_root / str(dict_registry["manifest"]["generated_database"])  # 派生 SQLite 路径

    # 临时文件位于同一目录，确保 os.replace 在同一文件系统内原子完成。
    path_temp_database = path_database.with_suffix(path_database.suffix + ".tmp")  # 原子构建临时数据库路径

    # 清理上次异常中断遗留的同名临时文件。
    if path_temp_database.exists():

        # 仅删除精确受管临时目标，不使用通配符扩大范围。
        path_temp_database.unlink()

    # 计算权威来源摘要并构造统一检索行。
    str_source_digest = calculate_source_digest(path_skill_root)  # 当前权威来源摘要

    # 统一记录模型供主表与 FTS5 表使用。
    list_records = build_search_records(dict_registry)  # 待写入的四类检索记录

    # 主表结构保存结构化返回和完整检索文本。
    str_create_items_sql = (  # SQLite 主表建表语句
        "CREATE TABLE items (id TEXT PRIMARY KEY, kind TEXT NOT NULL, "
        "category TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL, "
        "aliases TEXT NOT NULL, source TEXT NOT NULL, search_text TEXT NOT NULL)"
    )

    # FTS5 trigram 表保存中英文子串检索字段。
    str_create_fts_sql = (  # SQLite FTS5 建表语句
        "CREATE VIRTUAL TABLE registry_fts USING fts5("
        "id UNINDEXED, kind UNINDEXED, category UNINDEXED, title, summary, "
        "aliases, search_text, tokenize='trigram')"
    )

    # 主表写入参数与统一记录字典键完全对应。
    str_insert_items_sql = (  # SQLite 主表批量写入语句
        "INSERT INTO items (id, kind, category, title, summary, aliases, source, search_text) "
        "VALUES (:id, :kind, :category, :title, :summary, :aliases, :source, :search_text)"
    )

    # FTS 表写入排除非检索来源字段。
    str_insert_fts_sql = (  # SQLite FTS5 批量写入语句
        "INSERT INTO registry_fts (id, kind, category, title, summary, aliases, search_text) "
        "VALUES (:id, :kind, :category, :title, :summary, :aliases, :search_text)"
    )

    # 保存临时数据库连接，确保成功替换和异常清理前都能显式释放 Windows 文件句柄。
    connection: sqlite3.Connection | None = None  # 当前临时 SQLite 连接

    # 打开临时数据库并在单一事务中建立完整结构。
    try:

        # 上下文管理器只负责事务提交或回滚，文件句柄在块后显式关闭。
        with sqlite3.connect(path_temp_database) as connection:

            # 主表保存结构化返回字段并以稳定 id 为主键。
            connection.execute(str_create_items_sql)

            # 元数据表保存 schema、来源摘要与记录数量，用于默认只读新鲜度检查。
            connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

            # FTS5 trigram 提供中英文子串检索；缺失扩展时必须显式失败。
            connection.execute(str_create_fts_sql)

            # 按固定记录顺序写入主表。
            connection.executemany(
                str_insert_items_sql,
                list_records,
            )

            # FTS 表与主表保存相同 id 和可检索文本，不存放可执行指令。
            connection.executemany(
                str_insert_fts_sql,
                list_records,
            )

            # 写入来源摘要、schema 与记录数量三项新鲜度元数据。
            connection.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                [
                    ("schema_version", str(INT_SUPPORTED_SCHEMA_VERSION)),  # 运行时兼容版本
                    ("source_digest", str_source_digest),  # JSON 与 Markdown 来源摘要
                    ("record_count", str(len(list_records))),  # 四类检索记录总数
                    ("fts_tokenizer", "trigram"),  # 实际使用的 FTS5 tokenizer
                ],
            )

            # 提交完整事务后才允许替换现有数据库。
            connection.commit()

        # sqlite3 上下文只管理事务，Windows 原子替换前必须显式关闭文件句柄。
        connection.close()

        # 同目录原子替换保证查询方不会观察到半成品数据库。
        os.replace(path_temp_database, path_database)

    # SQLite、文件系统或编码问题统一映射为注册表状态错误。
    except (OSError, sqlite3.Error) as exc:

        # 构建中途失败时先释放可能仍占用临时文件的 SQLite 连接。
        if connection is not None:

            # close 可重复调用，确保后续精确清理不再触发共享冲突。
            connection.close()

        # 失败后移除精确临时文件，保留既有数据库供诊断或回退。
        if path_temp_database.exists():

            # 删除未完成的受管临时数据库。
            path_temp_database.unlink()

        # 提升为稳定错误协议，明确可能涉及 FTS5 trigram 支持。
        raise RegistryError(f"> ERR: [Python] SQLite 注册表构建失败：{exc}") from exc

    # 返回可审计构建结果，不向终端打印完整数据库内容。
    dict_result = {  # SQLite 构建结果
        "status": "written",  # 已完成原子替换
        "database": path_database.as_posix(),  # 派生数据库路径
        "source_digest": str_source_digest,  # 写入元数据的来源摘要
        "record_count": len(list_records),  # 四类记录总数
        "written": True,  # 显式写入标记
    }

    # 返回给 CLI 生成 JSON 协议或简短摘要。
    return dict_result

# 检查 SQLite 是否存在、完整并与当前权威摘要一致。
def inspect_database(path_skill_root: Path, dict_registry: dict[str, Any]) -> dict[str, Any]:
    """只读检查派生 SQLite 新鲜度与兼容性。

    参数：
    - `path_skill_root`：正式技能源码、dist 或安装副本根目录。
    - `dict_registry`：已经通过完整校验的注册表模型。

    返回：
    - `dict[str, Any]`：数据库路径、摘要、记录数量与只读状态。

    异常：
    - `RegistryError`：数据库缺失、损坏、陈旧或不兼容时抛出。
    """

    # 根据 manifest 固定派生数据库路径。
    path_database = registry_root(path_skill_root) / str(dict_registry["manifest"]["generated_database"])  # 待检查 SQLite 路径

    # 默认 build 不创建缺失数据库，只报告状态错误。
    if not path_database.is_file():

        # 明确提示需要显式 --write，保持写入授权可见。
        raise RegistryError("> ERR: [Python] 派生 SQLite 注册表缺失；请显式运行 registry.build --write")

    # 当前权威摘要用于与数据库 metadata 比较。
    str_expected_digest = calculate_source_digest(path_skill_root)  # 当前 JSON 与 Markdown 来源摘要

    # 只读 URI 防止检查路径意外创建 journal 或修改数据库。
    str_uri = path_database.resolve().as_uri() + "?mode=ro"  # SQLite 只读连接 URI

    # 打开只读连接并校验完整性、schema 与元数据。
    try:

        # URI 模式确保 SQLite 按只读方式连接现有文件。
        with sqlite3.connect(str_uri, uri=True) as connection:

            # quick_check 必须返回 ok，才能信任后续 metadata 查询。
            tuple_integrity = connection.execute("PRAGMA quick_check").fetchone()  # SQLite 完整性检查结果

            # 缺失或非 ok 表示数据库损坏。
            if not tuple_integrity or tuple_integrity[0] != "ok":

                # 阻止查询损坏索引并返回不完整结果。
                raise RegistryError("> ERR: [Python] 派生 SQLite 注册表完整性检查失败")

            # 读取全部 metadata 键值并转换为字符串映射。
            dict_metadata = {  # SQLite 注册表元数据
                str_key: str_value  # 保留数据库记录的文本值
                for str_key, str_value in connection.execute("SELECT key, value FROM metadata")  # 遍历元数据表
            }

            # 主表计数用于核对 metadata 没有漂移。
            int_record_count = int(connection.execute("SELECT COUNT(*) FROM items").fetchone()[0])  # SQLite 主表记录数

    # 数据库结构缺失、损坏或只读打开失败统一报告状态错误。
    except (OSError, sqlite3.Error, TypeError, ValueError) as exc:

        # 不把底层异常当作请求错误，调用方应重建受管数据库。
        raise RegistryError(f"> ERR: [Python] 派生 SQLite 注册表无法读取：{exc}") from exc

    # schema 不兼容时不得继续查询。
    if dict_metadata.get("schema_version") != str(INT_SUPPORTED_SCHEMA_VERSION):

        # 未来或旧版数据库都必须显式重建。
        raise RegistryError("> ERR: [Python] 派生 SQLite 注册表 schema 不兼容")

    # 摘要不一致证明 JSON 或 Markdown 已变化。
    if dict_metadata.get("source_digest") != str_expected_digest:

        # 查询入口必须 fail closed，不能使用陈旧索引。
        raise RegistryError("> ERR: [Python] 派生 SQLite 注册表已陈旧；请显式运行 registry.build --write")

    # metadata 数量必须与主表事实一致。
    if dict_metadata.get("record_count") != str(int_record_count):

        # 计数漂移表明数据库结构被非受管修改。
        raise RegistryError("> ERR: [Python] 派生 SQLite 注册表记录数不一致")

    # 返回只读检查证据。
    dict_result = {  # SQLite 只读检查结果
        "status": "ready",  # 数据库完整且新鲜
        "database": path_database.as_posix(),  # 当前派生数据库路径
        "source_digest": str_expected_digest,  # 与 metadata 匹配的权威摘要
        "record_count": int_record_count,  # 完整性校验后的主表计数
        "written": False,  # 默认检查未执行写入
    }

    # 返回供 build 和 ask 入口复用的状态载荷。
    return dict_result
