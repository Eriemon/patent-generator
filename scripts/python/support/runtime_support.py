#!/usr/bin/env python3
"""正文后链共用的轻量运行时支持。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入时间、序列化、正则和路径能力，供后链脚本共享基础读写与文本规整逻辑。
import datetime
import json
import re
from pathlib import Path
from typing import Any

# 固定 Windows 路径不允许出现的字符集合，避免标题直接落盘时创建失败。
ILLEGAL_TITLE_CHARACTERS = set('\\/:*?"<>|\n\r\t')  # Windows 路径非法字符集合

# 固定不应被正文查找逻辑识别为正文草稿的 Markdown 文件名。
EXCLUDED_DISCLOSURE_MARKDOWN = {  # 正文草稿查找时需要跳过的 Markdown 名称
    "research_inventory.md",  # 材料盘点报告不属于正文草稿
    "research_facts.md",  # 事实抽取报告不属于正文草稿
    "selected_invention_point.md",  # 主案选择说明不属于正文草稿
    "prior_art_query_plan.md",  # 查新规划说明不属于正文草稿
    "pre_draft_preview.md",  # 预览确认材料不属于正文草稿
    "claims_draft.md",  # 权利要求草稿不属于正文草稿
    "validation_report.md",  # 自检报告不属于正文草稿
    "figures_manifest.md",  # 附图清单不属于正文草稿
    "revision_log.md",  # 迭代日志不属于正文草稿
}  # 正文查找排除名单

# 返回 ISO 时间字符串，供草稿快照、日志和说明文件统一使用。
def iso_now() -> str:
    """返回精确到秒的本地 ISO 时间。

    参数：
    - 无。

    返回：
    - `str`：精确到秒的本地 ISO 时间字符串。

    异常：
    - 无。
    """

    # 生成当前本地时间对象，供后续统一格式化输出。
    datetime_dt_now: datetime.datetime = datetime.datetime.now()  # 当前本地时间对象

    # 输出统一的 ISO 时间文本，避免不同脚本各自拼接时间格式。
    return datetime_dt_now.isoformat(timespec="seconds")

# 返回紧凑时间戳，供正文快照和 HTML 快照命名使用。
def now_timestamp() -> str:
    """返回紧凑时间戳。

    参数：
    - 无。

    返回：
    - `str`：`YYYYMMDDHHMMSS` 形式的时间戳文本。

    异常：
    - 无。
    """

    # 读取当前本地时间对象，供文件名时间片段统一复用。
    datetime_dt_now: datetime.datetime = datetime.datetime.now()  # 文件命名时间对象

    # 输出没有空格和冒号的紧凑格式，便于直接写入文件名。
    return datetime_dt_now.strftime("%Y%m%d%H%M%S")

# 把任意标题规整为稳定路径片段，避免中英文标题直接落盘时产生非法文件名。
def sanitize_name(value: str, fallback: str = "patent_case", max_len: int = 80) -> str:
    """清洗标题并返回可用路径片段。

    参数：
    - `value`：原始标题、案件名或草稿名。
    - `fallback`：清洗后为空时使用的兜底值。
    - `max_len`：输出片段允许的最大长度。

    返回：
    - `str`：适合作为目录名或文件名前缀的稳定文本。

    异常：
    - 无。
    """

    # 先去掉标题首尾空白，避免目录名两端出现无意义空格。
    str_cleaned_value = (value or "").strip()  # 去首尾空白后的标题文本

    # 先准备合法字符列表，后续会把仍可用于路径的字符重新拼回标题文本。
    list_allowed_characters: list[str] = []  # 仍可保留在路径片段里的字符列表

    # 逐个检查标题字符，只把允许进入路径的字符收进暂存列表。
    for str_character in str_cleaned_value:

        # 在当前字符不属于非法路径字符时保留它，供后续重新拼成标题。
        if str_character not in ILLEGAL_TITLE_CHARACTERS:

            # 把当前合法字符加入暂存列表，供路径标题重建步骤复用。
            list_allowed_characters.append(str_character)  # 已保留的合法标题字符

    # 把合法字符重新拼接成标题文本，确保非法路径字符已经被剔除。
    str_cleaned_value = "".join(list_allowed_characters)  # 仅保留合法路径字符的标题文本

    # 把中间空白压缩成下划线，兼顾英文短语可读性和路径稳定性。
    str_cleaned_value = re.sub(r"\s+", "_", str_cleaned_value)  # 空白统一后的标题文本

    # 去掉标题两端容易导致歧义的装饰字符，避免路径名看起来像隐藏文件。
    str_cleaned_value = str_cleaned_value.strip("._- ")  # 删除首尾装饰字符后的标题文本

    # 在标题完全不可用时回退到默认名称，保证后续路径仍能创建。
    if not str_cleaned_value:

        # 把空标题替换成兜底名称，避免生成空目录名。
        str_cleaned_value = fallback  # 空标题兜底名称

    # 在标题超过长度上限时裁剪到受控范围，减少 Windows 深路径风险。
    if len(str_cleaned_value) > max_len:

        # 截断超长标题，并同步去掉尾部可能残留的装饰字符。
        str_cleaned_value = str_cleaned_value[:max_len].rstrip("-_ ")  # 截断后的标题片段

    # 再做一次兜底，防止截断后又变成空字符串。
    return str_cleaned_value or fallback

# 确保目录存在并把目录对象返回给调用方继续拼接子路径。
def ensure_dir(path_dir: Path) -> Path:
    """创建目录并返回目录对象。

    参数：
    - `path_dir`：需要存在的目录路径。

    返回：
    - `Path`：已经确保存在的目录路径对象。

    异常：
    - 目录创建失败时由底层文件系统异常上抛。
    """

    # 递归创建目录，允许调用方直接传入多级路径。
    path_dir.mkdir(parents=True, exist_ok=True)  # 已创建或已存在的目录路径

    # 返回目录对象，方便调用方继续拼接输出文件。
    return path_dir

# 统一写入 UTF-8 文本文件，避免多个入口重复处理父目录创建和编码细节。
def write_text_file(path_file: Path, str_text: str) -> None:
    """写入 UTF-8 文本文件。

    参数：
    - `path_file`：目标文本文件路径。
    - `str_text`：待写入的文本内容。

    返回：
    - `None`。

    异常：
    - 目录创建或文件写入失败时由底层异常上抛。
    """

    # 先确保目标文件父目录存在，避免调用方在写文件前重复建目录。
    path_parent_dir = ensure_dir(path_file.parent)  # 目标文本文件父目录

    # 按 UTF-8 编码把文本写入目标文件，保证中文材料直接可读。
    (path_parent_dir / path_file.name).write_text(str_text, encoding="utf-8")  # 已写入的目标文本文件

# 统一写入带缩进的 UTF-8 JSON 文件，方便人工审阅和后续脚本复读。
def write_json_file(path_file: Path, obj_data: Any) -> None:
    """写入 UTF-8 JSON 文件。

    参数：
    - `path_file`：目标 JSON 文件路径。
    - `obj_data`：可被 `json.dumps` 序列化的数据对象。

    返回：
    - `None`。

    异常：
    - JSON 序列化、目录创建或文件写入失败时由底层异常上抛。
    """

    # 先把结构化对象序列化成带缩进的可读 JSON 文本。
    str_json_text = json.dumps(obj_data, ensure_ascii=False, indent=2)  # 可读 JSON 文本

    # 复用统一文本写入入口，把 JSON 文本写到目标文件。
    write_text_file(path_file, str_json_text)  # 已写入的 JSON 文件

# 统一读取 UTF-8 JSON 文件，保证后链脚本解释中间件的方式一致。
def read_json_file(path_file: Path) -> Any:
    """读取 UTF-8 JSON 文件。

    参数：
    - `path_file`：待读取的 JSON 文件路径。

    返回：
    - `Any`：反序列化后的 Python 数据结构。

    异常：
    - 文件不存在、编码错误或 JSON 格式错误时由底层异常上抛。
    """

    # 先读取原始 JSON 文本，供统一反序列化处理。
    str_json_text = path_file.read_text(encoding="utf-8")  # JSON 原始文本

    # 返回解析后的数据对象，供调用方继续读取字段。
    return json.loads(str_json_text)

# 加载案件配置文件，在配置缺失时返回空字典，方便只读工具安全降级。
def load_case_config(path_case_dir: Path) -> dict[str, Any]:
    """读取案件配置文件。

    参数：
    - `path_case_dir`：案件根目录路径。

    返回：
    - `dict[str, Any]`：案件配置字典；配置缺失时返回空字典。

    异常：
    - 配置文件存在但 JSON 非法时由底层异常上抛。
    """

    # 固定案件配置文件路径，保持各入口对配置入口的一致约定。
    path_case_config = path_case_dir / "case_config.json"  # 案件配置文件路径

    # 在配置文件缺失时返回空配置，让只读工具能够继续安全降级。
    if not path_case_config.exists():

        # 对未建案或配置暂缺的场景返回空字典，避免只读工具直接崩溃。
        return {}  # 缺少配置时的空配置

    # 读取现有案件配置，供正文、导出和检索工具复用案件元信息。
    return read_json_file(path_case_config)

# 把任意值规整为单行可读文本，供摘要句、权利要求和自检报告共用。
def clean_text(obj_value: Any) -> str:
    """清洗任意值并返回单行文本。

    参数：
    - `obj_value`：待清洗的任意 Python 值。

    返回：
    - `str`：删除多余空白与装饰符后的单行文本。

    异常：
    - 无。
    """

    # 先把输入值转成单行文本，减少后续各类摘要拼装中的换行噪声。
    str_cleaned_value = re.sub(r"\s+", " ", str(obj_value or "")).strip()  # 压缩空白后的文本

    # 去掉长编号样式的书名号片段，减少原始资料里的噪声标记。
    str_cleaned_value = re.sub(r"【[^】]{4,}】", "", str_cleaned_value)  # 去除长编号标记后的文本

    # 去掉常见句尾标点与分隔符，让摘要句更便于二次拼接。
    return str_cleaned_value.strip(" ，,。；;：:")

# 按句号、分号和换行切分文本，供正文和自检步骤提炼短句摘要。
def split_sentences(str_text: str, limit: int = 12) -> list[str]:
    """切分文本并返回句子列表。

    参数：
    - `str_text`：待切分的原始文本。
    - `limit`：最多保留的句子数量。

    返回：
    - `list[str]`：清洗后的句子列表。

    异常：
    - 无。
    """

    # 先按中文句号、问号、分号和换行切开原始文本片段。
    list_parts = re.split(r"(?<=[。！？；!?;])\s*|\n+", str_text or "")  # 原始句子片段列表

    # 把各片段清洗成可复用的单行句子文本。
    list_cleaned_parts = [clean_text(str_part) for str_part in list_parts]  # 清洗后的句子候选列表

    # 过滤掉空片段，仅保留真正可用的句子文本。
    list_sentences = [str_part for str_part in list_cleaned_parts if str_part]  # 有效句子列表

    # 按上限返回句子列表，避免后续报告和草稿被长材料撑爆。
    return list_sentences[:limit]

# 聚合主案和 facts 中已有的技术术语，供正文、附图和权利要求入口复用。
def collect_terms(
    dict_selected: dict[str, Any],
    dict_facts: dict[str, Any],
    limit: int = 12,
) -> list[str]:
    """聚合已有技术术语。

    参数：
    - `dict_selected`：主案选择结果字典。
    - `dict_facts`：事实抽取结果字典。
    - `limit`：最多保留的术语数量。

    返回：
    - `list[str]`：去重并清洗后的技术术语列表。

    异常：
    - 无。
    """

    # 先准备候选术语列表，后续会逐批追加主案和 facts 的来源术语。
    list_candidate_terms: list[str] = []  # 术语候选列表

    # 收下主案选择阶段已经整理的技术术语，优先保留人工已审阅过的词。
    list_candidate_terms.extend(dict_selected.get("technical_terms", []))  # 主案术语候选

    # 继续补入事实抽取阶段的技术术语，补齐正文构思时的词汇覆盖面。
    list_candidate_terms.extend(dict_facts.get("technical_terms", []))  # facts 术语候选

    # 读取主案保护策略字典，补入独立项和从属项关注特征。
    dict_strategy = dict_selected.get("protection_strategy", {})  # 主案保护策略字典

    # 把独立项关注特征补进候选列表，方便正文和权利要求共享术语。
    list_candidate_terms.extend(dict_strategy.get("independent_claim_focus", []))  # 独立项关注特征候选

    # 把可选技术特征补进候选列表，方便后续形成从属保护方向。
    list_candidate_terms.extend(dict_strategy.get("optional_features", []))  # 可选技术特征候选

    # 准备用于大小写无关去重的键集合，避免同词反复进入结果。
    set_seen_terms: set[str] = set()  # 已收录术语键集合

    # 准备最终术语结果列表，后续按顺序保留首个可用术语。
    list_terms: list[str] = []  # 去重后的术语结果列表

    # 逐条整理候选术语，确保输出结果稳定且可读。
    for str_raw_value in list_candidate_terms:

        # 先把当前候选术语清洗成单行文本，便于统一比较和去重。
        str_term = clean_text(str_raw_value)  # 当前候选术语文本

        # 在清洗后为空时直接跳过，避免空壳条目继续参与去重判断。
        if not str_term:

            # 继续处理下一条候选术语，把结果名额留给真实技术词。
            continue

        # 构造当前术语的去重键，压平大小写和空格差异。
        str_term_key = str_term.lower().replace(" ", "")  # 当前术语去重键

        # 在当前术语已经收录过时直接跳过，保持结果顺序和内容稳定。
        if str_term_key in set_seen_terms:

            # 继续处理下一条候选术语，避免重复词再次进入结果。
            continue

        # 先登记当前术语去重键，保证后续重复词不会再次进入结果。
        set_seen_terms.add(str_term_key)  # 已登记的术语去重键

        # 把当前可用术语加入最终列表，供正文与附图入口复用。
        list_terms.append(str_term)  # 已收录的术语文本

        # 在结果达到上限后立即停止遍历，避免低优先级术语继续挤入。
        if len(list_terms) >= limit:

            # 达到术语数量上限后立即返回，保持输出长度受控。
            return list_terms

    # 返回已经整理好的术语列表，供正文、附图和权利要求入口共享。
    return list_terms

# 读取并筛选已核验的查新记录，避免正文阶段直接消费不完整的查新样本。
def read_verified_prior_art_records(path_case_dir: Path) -> list[dict[str, Any]]:
    """读取已核验的查新记录列表。

    参数：
    - `path_case_dir`：案件根目录路径。

    返回：
    - `list[dict[str, Any]]`：通过基本字段核验的查新记录列表。

    异常：
    - 查新记录文件存在但 JSON 非法时由底层异常上抛。
    """

    # 固定查新记录文件路径，保持正文和自检对查新证据入口的一致理解。
    path_records = path_case_dir / "02_facts" / "prior_art_records.json"  # 查新记录 JSON 路径

    # 在查新记录文件缺失时返回空列表，让正文入口安全降级。
    if not path_records.exists():

        # 对尚未补齐查新记录的案件返回空列表，避免后续逻辑伪造记录。
        return []  # 缺少查新记录时的空列表

    # 读取原始查新记录载荷，兼容字典包裹和直接列表两种轻量结构。
    obj_records_source = read_json_file(path_records)  # 原始查新记录载荷

    # 在字典包裹结构下优先读取 records 字段，兼容当前测试夹具格式。
    if isinstance(obj_records_source, dict):

        # 从字典载荷中取出 records 列表，供后续统一筛选。
        list_records = list(obj_records_source.get("records", []))  # 字典载荷中的 records 列表

    # 在直接列表结构下直接沿用列表内容，兼容更轻量的手工样例。
    else:

        # 将原始载荷视作记录列表，交给后续类型检查继续筛选。
        list_records = list(obj_records_source) if isinstance(obj_records_source, list) else []  # 兼容直接列表的查新记录列表

    # 准备最终通过核验的记录列表，后续逐条补充符合条件的查新记录。
    list_verified_records: list[dict[str, Any]] = []  # 已通过核验的查新记录列表

    # 逐条核对查新记录的关键字段，避免正文阶段误用残缺记录。
    for obj_record in list_records:

        # 在当前条目不是字典时直接跳过，避免脏数据继续参与字段核验。
        if not isinstance(obj_record, dict):

            # 继续处理下一条原始记录，把结果名额留给结构正确的查新项。
            continue

        # 读取公开号或文献标题字段，确保记录具备最基本的引用标识。
        str_publication = clean_text(obj_record.get("publication_no_or_title"))  # 公开号或标题文本

        # 读取公开日期字段，确保记录能够支撑时间维度说明。
        str_publication_date = clean_text(obj_record.get("publication_date"))  # 公开日期文本

        # 读取来源字段，确保记录具备可追溯的数据库或 URL 来源。
        str_source = clean_text(obj_record.get("source_url_or_database"))  # 查新来源文本

        # 旧版记录未声明来源类型时按专利处理，保持历史案件向后兼容。
        str_source_type = clean_text(obj_record.get("source_type", "patent")).lower()  # 规范化来源类型

        # 非专利来源必须携带人工核验的完整著录文本，禁止生成器猜测书目信息。
        str_reference_text = clean_text(obj_record.get("reference_text"))  # 人工核验的参考文献文本

        # 读取相同特征列表，确保记录能支撑“已公开特征”对比说明。
        list_same_features = list(obj_record.get("same_features", []))  # 相同特征列表

        # 读取区别特征列表，确保记录能支撑“差异特征”对比说明。
        list_different_features = list(obj_record.get("different_features", []))  # 差异特征列表

        # 在关键字段不齐时直接跳过当前记录，避免正文引用缺口证据。
        if not (str_publication and str_publication_date and str_source):

            # 继续处理下一条记录，保持输出只包含可追溯的完整条目。
            continue

        # 只接受合同声明的来源类型，避免未知类型误入正式引用链。
        if str_source_type not in {"patent", "paper", "standard", "other"}:

            # 跳过未受支持的来源类型，由案件补录阶段修正原始记录。
            continue

        # 论文、标准及其他来源没有稳定的自动著录规则，必须提供人工著录文本。
        if str_source_type != "patent" and not str_reference_text:

            # 缺少人工著录文本的非专利记录不能视为可核验引用来源。
            continue

        # 在相同特征或区别特征缺失时直接跳过，避免正文形成失衡对比。
        if not (list_same_features and list_different_features):

            # 继续处理下一条记录，把结果名额留给字段完整的查新项。
            continue

        # 把通过核验的完整记录加入结果列表，供正文和自检入口复用。
        list_verified_records.append(obj_record)  # 已收录的完整查新记录

    # 返回通过核验的查新记录列表，供正文与自检逻辑共享。
    return list_verified_records

# 优先定位稳定正文草稿路径，否则退回最近一次可疑似正文的 Markdown 文件。
def find_disclosure_draft(path_case_dir: Path, path_input: Path | None = None) -> Path | None:
    """定位正文草稿文件。

    参数：
    - `path_case_dir`：案件根目录路径。
    - `path_input`：调用方显式指定的正文草稿路径。

    返回：
    - `Path | None`：命中的正文草稿路径；找不到时返回 `None`。

    异常：
    - 读取文件修改时间时若底层文件系统报错，则异常继续上抛。
    """

    # 在调用方显式给定输入路径时，优先直接返回该路径的绝对形式。
    if path_input is not None:

        # 返回调用方指定的输入路径，避免正文查找逻辑覆盖人工显式选择。
        return path_input.resolve()

    # 固定稳定正文草稿路径，优先命中正式正文主文件。
    path_stable_draft = path_case_dir / "03_drafts" / "disclosure_draft.md"  # 正式稳定正文草稿路径

    # 在稳定正文草稿已经存在时直接返回，避免退回到历史快照。
    if path_stable_draft.exists():

        # 返回稳定正文草稿绝对路径，供导出和自检直接复用。
        return path_stable_draft.resolve()

    # 先收集 drafts 目录中的 Markdown 候选文件，供后续按时间排序。
    list_markdown_files = list((path_case_dir / "03_drafts").glob("*.md"))  # drafts 目录里的 Markdown 候选文件列表

    # 按最近修改时间倒序排列候选文件，优先命中最新的正文类草稿。
    list_markdown_files.sort(key=lambda path_file: path_file.stat().st_mtime, reverse=True)  # 已按修改时间倒序排列的 Markdown 候选文件列表

    # 逐条检查候选 Markdown，找到第一份真正可能作为正文的文件。
    for path_markdown in list_markdown_files:

        # 只有在文件名不属于排除名单时，当前 Markdown 才可能是真正正文。
        if path_markdown.name not in EXCLUDED_DISCLOSURE_MARKDOWN:

            # 继续排除修订请求说明文件，避免把请求单误判为正文草稿。
            if not path_markdown.name.endswith("_revision_request.md"):

                # 返回命中的历史正文快照路径，供导出和迭代流程继续使用。
                return path_markdown.resolve()

    # 在 drafts 目录里找不到正文类 Markdown 时返回空值，由调用方决定如何提示。
    return None

# 把单条查新记录规整成可直接写入正文的摘要句，减少正文入口的格式拼接负担。
def summarize_prior_art(dict_record: dict[str, Any], int_citation_index: int) -> str:
    """生成单条查新记录摘要句。

    参数：
    - `dict_record`：单条查新记录字典。
    - `int_citation_index`：正文与参考文献共享的一基序号。

    返回：
    - `str`：适合直接写入正文背景技术段落的摘要句。

    异常：
    - 无。
    """

    # 读取文献标题或公开号字段，作为摘要句的主体标识。
    str_title = clean_text(dict_record.get("publication_no_or_title"))  # 文献标题或公开号文本

    # 读取文献公开日期字段，供摘要句标出时间维度。
    str_date = clean_text(dict_record.get("publication_date"))  # 文献公开日期文本

    # 先准备相同特征文本列表，后续逐条收录可直接写入摘要句的特征文本。
    list_same_feature_texts: list[str] = []  # 已清洗的相同特征文本列表

    # 逐条清洗相同特征原文，只保留真正可写入摘要句的非空文本。
    for str_item in dict_record.get("same_features", []):

        # 把当前相同特征清洗成单行文本，便于统一判断和拼接。
        str_same_feature = clean_text(str_item)  # 当前相同特征的单行文本

        # 在当前相同特征清洗后仍有内容时才把它加入摘要候选列表。
        if str_same_feature:

            # 把当前可用的相同特征文本加入列表，供摘要句后续拼接。
            list_same_feature_texts.append(str_same_feature)  # 已收录的相同特征文本

    # 把相同特征列表拼成单行摘要，供正文直接引用现有技术已公开内容。
    str_same_features = "、".join(list_same_feature_texts)  # 现有技术已公开相同特征摘要文本

    # 先准备区别特征文本列表，后续逐条收录可直接写入差异说明的文本。
    list_different_feature_texts: list[str] = []  # 已清洗的区别特征文本列表

    # 逐条清洗区别特征原文，只保留真正可写入差异说明的非空文本。
    for str_item in dict_record.get("different_features", []):

        # 把当前区别特征清洗成单行文本，便于统一判断和拼接。
        str_different_feature = clean_text(str_item)  # 当前区别特征的单行文本

        # 仅当当前区别特征不是空串时才把它收进差异说明候选列表。
        if str_different_feature:

            # 把当前可用的区别特征文本加入列表，供差异说明后续拼接。
            list_different_feature_texts.append(str_different_feature)  # 已收录的区别特征文本

    # 把区别特征列表拼成单行摘要，供正文直接引用本案差异点说明。
    str_different_features = "、".join(list_different_feature_texts)  # 本案区别特征摘要文本

    # 返回可直接插入正文背景技术段落的查新记录摘要句。
    return (
        f"{str_title}（公开日：{str_date}）公开了 {str_same_features}；"
        f"与本案相比，主要区别在于 {str_different_features}。[{int_citation_index}]"
    )

# 根据受控来源类型生成文末著录项，保证正文序号与参考文献列表一致。
def format_prior_art_reference(dict_record: dict[str, Any], int_citation_index: int) -> str:
    """生成单条先技术参考文献。

    参数：
    - `dict_record`：已经通过核验的单条查新记录。
    - `int_citation_index`：正文与参考文献共享的一基序号。

    返回：
    - `str`：带方括号序号的参考文献条目。

    异常：
    - 非专利记录缺少 `reference_text` 时抛出 `ValueError`。
    """

    # 旧版记录未声明类型时按专利格式处理，避免破坏现有案件数据。
    str_source_type = clean_text(dict_record.get("source_type", "patent")).lower()  # 当前著录规则选择键

    # 非专利来源直接复用人工核验著录文本，禁止补写未知作者、期刊或页码。
    if str_source_type != "patent":

        # 读取人工核验的完整著录文本，作为非专利条目的唯一正文来源。
        str_reference_text = clean_text(dict_record.get("reference_text"))  # 非专利参考文献文本

        # 调用方绕过记录筛选时仍要阻止生成不完整的非专利参考文献。
        if not str_reference_text:

            # 明确指出合同缺口，便于调用方定位并补录人工著录文本。
            raise ValueError("> ERR: [Python] 非专利先技术记录缺少 reference_text")

        # 只附加稳定序号，其余著录内容保持人工核验原文。
        return f"[{int_citation_index}] {str_reference_text}"

    # 专利条目使用旧合同中已核验的公开号、日期和来源字段安全组装。
    str_publication = clean_text(dict_record.get("publication_no_or_title"))  # 专利公开号或标题

    # 读取公开日期，避免引用条目丢失时间维度。
    str_publication_date = clean_text(dict_record.get("publication_date"))  # 专利公开日期

    # 读取核验数据库或 URL，保留来源可追溯性。
    str_source = clean_text(dict_record.get("source_url_or_database"))  # 专利核验来源

    # 返回不猜测申请人或发明人的最小专利著录项。
    return f"[{int_citation_index}] {str_publication}. 公开日：{str_publication_date}. 来源：{str_source}."
