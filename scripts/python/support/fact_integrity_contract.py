"""集中执行专利交底书事实进入正文前的确定性完整性门禁。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 标准库负责日期比较、数值识别和只读映射类型约束。
import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

# 只识别可能表达技术数据的数字，不把编号本身直接视为批准事实。
PATTERN_NUMBER = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:%|％)?")  # 正文数值候选模式

# 删除专利流程中允许直接出现的编号和日期，避免把结构标识误报为技术数据。
PATTERN_EXEMPT_NUMBER = re.compile(  # 可豁免结构编号和日期模式
    r"(?:步骤|图|公式|文献|引用)\s*[A-Za-z]?\d+(?:[.-]\d+)*"  # 步骤、附图、公式和引用编号
    r"|(?:申请号|公开号|专利号)[:：]?\s*[A-Za-z]{0,3}\d[\dA-Za-z.-]*"  # 专利申请及公开编号
    r"|\d{4}年\d{1,2}月\d{1,2}日"  # 中文完整日期
    r"|\d{4}-\d{1,2}-\d{1,2}"  # ISO 格式公开日期
    r"|\[\d+\]"  # 方括号参考文献引用序号
)  # 编译后的豁免模式供数值正文预处理复用

# 独立专利公开号仍是文献身份，不能因缺少“公开号”前缀而误入数据队列。
PATTERN_PATENT_IDENTIFIER = re.compile(r"\b(?:CN|US|EP|WO|JP|KR)\d{6,}[A-Z]\d?\b", re.I)  # 专利公开号模式

# 中文语义出现时不把整句等号表达式自动当作纯公式。
PATTERN_CJK_CHARACTER = re.compile(r"[\u3400-\u9fff]")  # 中日韩统一表意字符模式

# 纯公式至少包含运算符或常用 LaTeX 运算命令。
PATTERN_FORMULA_OPERATOR = re.compile(r"[=+*/^_{}]|\\(?:frac|sum|prod|sqrt|int)\b")  # 公式运算信号模式

# 公式变量限定为独立单字母或 LaTeX 命令，避免把 accuracy=95% 误判为公式。
PATTERN_FORMULA_VARIABLE = re.compile(r"(?<![A-Za-z])[A-Za-z](?![A-Za-z])|\\[A-Za-z]+")  # 公式变量模式

# 中文连续重合阈值用于阻止整句搬运用户材料。
MIN_CHINESE_OVERLAP = 24  # 连续中文字符阻断阈值

# 英文连续重合阈值与中文阈值共同覆盖双语研究材料。
MIN_ENGLISH_OVERLAP = 15  # 连续英文单词阻断阈值

# 版本三把每类事实拆成独立登记表，任何顶层字段缺失都要求重新生成。
REQUIRED_MODEL_KEYS = {
    "contract_version",  # 结构化模型合同版本
    "source_manifest",  # 材料来源及实际用途
    "evidence_registry",  # 技术事实证据登记表
    "data_registry",  # 数值事实及批准状态
    "formula_registry",  # 正文公式语义登记表
    "term_registry",  # 术语定义和允许别名
    "figure_registry",  # 附图来源及正文引用
    "sections",  # 合同章节记录
    "cross_references",  # 章节交叉引用
    "pending_items",  # 未关闭人工处理项
}  # 版本三模型必填顶层字段

# 获准进入正文的材料只能明确归为发明事实或现有技术。
APPROVED_CONTENT_SOURCE_ROLES = {"invention_evidence", "prior_art"}  # 可贡献正式正文的材料角色

# 统一构造可被现有状态机直接消费的 blocker。
def build_blocker(str_code: str, str_message: str, str_suggestion: str) -> dict[str, str]:
    """构造事实完整性阻断记录。

    参数：
    - `str_code`：稳定规则代码。
    - `str_message`：可定位的问题说明。
    - `str_suggestion`：不虚构事实的修复建议。

    返回：
    - `dict[str, str]`：验证报告兼容的 blocker。

    异常：
    - 无。
    """

    # 返回统一字段，避免各入口自行解释严重级别。
    return {
        "level": "blocker",  # 正式交付阻断级别
        "code": str_code,  # 稳定机器规则代码
        "message": str_message,  # 面向审阅人的定位消息
        "suggestion": str_suggestion,  # 保持事实边界的修复动作
    }

# 校验材料来源具有单一、明确且可审计的实际用途角色。
def validate_source_manifest(list_sources: Any) -> list[dict[str, str]]:
    """检查材料角色缺失、非法或相互冲突的问题。

    参数：
    - `list_sources`：来源登记记录数组。

    返回：
    - `list[dict[str, str]]`：材料角色 findings。

    异常：
    - 无。
    """

    # 正式合同只允许四类角色，unknown 必须留给人工确认而不能进入正文。
    set_allowed_roles = {
        "invention_evidence",  # 本发明事实证据
        "prior_art",  # 参考日前现有技术候选
        "template_admin",  # 模板和行政说明材料
        "unknown",  # 尚未完成人工分类的材料
    }  # 合法材料角色集合

    # 容器损坏时无法建立来源边界，直接返回阻断。
    if not isinstance(list_sources, list):

        # 明确要求重建登记表，禁止把错误输入当作空材料。
        return [build_blocker("SRC001", "source_manifest 必须为数组", "重新扫描材料并确认每个来源角色")]

    # 保存每个来源已经声明的角色，用于检测跨记录冲突。
    dict_roles_by_source: dict[str, set[str]] = {}  # 来源编号到角色集合

    # 汇总全部材料问题，确保一次审阅能看到所有冲突。
    list_findings: list[dict[str, str]] = []  # 材料角色 findings

    # 逐项检查来源编号和角色，不根据文件名猜测真实用途。
    for dict_source in list_sources:

        # 非对象记录不能提供稳定来源编号。
        if not isinstance(dict_source, Mapping):

            # 将损坏记录作为独立问题保留。
            list_findings.append(build_blocker("SRC001", f"材料记录不是对象:{dict_source}", "重建来源登记记录"))

            # 当前记录无法继续做字段检查。
            continue

        # 读取显式来源编号，不用路径或标题代替身份。
        str_source_id = str(dict_source.get("source_id", "")).strip()  # 当前材料来源编号

        # 读取显式角色，空值保持未确认状态。
        str_role = str(dict_source.get("role", "")).strip()  # 当前材料用途角色

        # 来源编号或角色缺失都会破坏后续证据追踪。
        if not str_source_id or str_role not in set_allowed_roles:

            # 记录当前来源的缺失或非法角色。
            list_findings.append(build_blocker("SRC001", f"材料角色无效:{dict_source}", "显式确认 source_id 与 role"))

            # 非法记录不参与冲突集合，避免重复噪声。
            continue

        # 为首次出现的来源建立角色集合。
        set_source_roles = dict_roles_by_source.setdefault(str_source_id, set())  # 当前来源已声明角色

        # 登记本条记录的显式角色，稍后统一判断冲突。
        set_source_roles.add(str_role)

    # 按来源编号稳定遍历，保证报告顺序可重复。
    for str_source_id in sorted(dict_roles_by_source):

        # 读取当前来源的全部角色，判断是否存在语义冲突。
        set_roles = dict_roles_by_source[str_source_id]  # 当前来源角色集合

        # 同一来源只能承担一个真实用途角色。
        if len(set_roles) > 1:

            # 冲突必须交给人工选择，生成器不得自行偏向发明或现有技术。
            list_findings.append(
                build_blocker("SRC002", f"材料角色冲突:{str_source_id}:{sorted(set_roles)}", "人工确认唯一实际用途角色")
            )

    # 返回全部材料角色问题，空数组表示当前层通过。
    return list_findings

# 判断文本是否为应由公式登记表管理的纯公式表达式。
def is_formula_expression(str_text: str) -> bool:
    """识别不应进入数据审核队列的纯公式表达式。

    参数：
    - `str_text`：待判断的原始文本。

    返回：
    - `bool`：文本具有纯公式结构时为真。

    异常：
    - 无。
    """

    # 含中文语义的句子可能是在陈述指标结果，不能仅凭等号豁免。
    if PATTERN_CJK_CHARACTER.search(str_text):

        # 保守返回非公式，让量化中文陈述继续接受数据门检查。
        return False

    # 同时具备独立变量和运算信号才视为纯公式，避免英文指标名误判。
    bool_has_variable = PATTERN_FORMULA_VARIABLE.search(str_text) is not None  # 是否包含公式变量

    # 单独记录运算信号判断，使识别边界可审阅。
    bool_has_operator = PATTERN_FORMULA_OPERATOR.search(str_text) is not None  # 是否包含公式运算符

    # 两个信号同时成立时交由 formula_registry 治理。
    return bool_has_variable and bool_has_operator

# 判断正文片段是否仍含有未被结构编号、公式和日期豁免的数值。
def contains_governed_number(str_text: str) -> bool:
    """识别需要 data_id 批准的正文数值。

    参数：
    - `str_text`：待检查正文片段。

    返回：
    - `bool`：存在受管数值时为真。

    异常：
    - 无。
    """

    # 先移除明确豁免的编号、日期和独立专利公开号，保留其他量化内容。
    str_without_patent_ids = PATTERN_PATENT_IDENTIFIER.sub("", str_text)  # 去除专利公开号后的正文

    # 再清理带语义前缀的结构编号与公开日期。
    str_governed_text = PATTERN_EXEMPT_NUMBER.sub("", str_without_patent_ids)  # 去除结构编号后的正文

    # 纯公式由公式登记表验证用途、符号和正文对象，不重复要求 data_id。
    if is_formula_expression(str_governed_text.strip()):

        # 公式常数不是实验或对比数据，直接豁免数据批准链。
        return False

    # 仅剩的数值候选必须进入数据登记和人工批准链。
    return PATTERN_NUMBER.search(str_governed_text) is not None

# 从嵌套事实载荷中收集含受管数值的原始文本片段。
def collect_governed_numeric_texts(obj_value: Any) -> list[str]:
    """递归收集需要独立人工批准的量化文本。

    参数：
    - `obj_value`：候选事实中的任意 JSON 兼容值。

    返回：
    - `list[str]`：去重且保持首次出现顺序的量化文本。

    异常：
    - 无。
    """

    # 保存首次出现顺序，便于审核工件跨运行稳定。
    list_results: list[str] = []  # 量化事实文本数组

    # 集合只用于去重，不改变最终审核顺序。
    set_seen_texts: set[str] = set()  # 已收集量化文本集合

    # 使用内部递归函数遍历 JSON 对象的字符串叶子。
    def collect_value(obj_current: Any) -> None:
        """收集当前 JSON 节点下的量化字符串。

        参数：
        - `obj_current`：当前递归节点。

        返回：
        - `None`。

        异常：
        - 无。
        """

        # 字符串叶子只有命中数值门且尚未出现时才进入结果。
        if isinstance(obj_current, str):

            # 规范首尾空白，避免相同句子因格式差异重复审核。
            str_text = obj_current.strip()  # 当前字符串事实

            # 保存需要批准且尚未登记的量化文本。
            if str_text and contains_governed_number(str_text) and str_text not in set_seen_texts:

                # 登记去重身份后再追加稳定结果。
                set_seen_texts.add(str_text)

                # 保留完整原句供人工判断数值语义和来源。
                list_results.append(str_text)

            # 字符串节点处理完成后停止向下递归。
            return

        # 映射节点按插入顺序遍历值，不把字段名误当事实。
        if isinstance(obj_current, Mapping):

            # 递归处理当前对象的每个字段值。
            for obj_child in obj_current.values():

                # 收集子节点中的量化文本。
                collect_value(obj_child)

            # 当前映射全部处理完成后返回。
            return

        # 序列节点排除字符串后按原始顺序递归。
        if isinstance(obj_current, Sequence):

            # 逐项检查列表或元组中的事实值。
            for obj_child in obj_current:

                # 收集当前序列元素中的量化文本。
                collect_value(obj_child)

    # 从调用方提供的根节点开始递归收集。
    collect_value(obj_value)

    # 返回去重且顺序稳定的量化文本。
    return list_results

# 汇总全部正文事实的数据白名单缺口，形成稳定阻断报告。
def collect_approved_data_ids(list_data_records: Any) -> set[str]:
    """收集已经获得明确人工批准的数据编号。

    参数：
    - `list_data_records`：数据登记记录数组。

    返回：
    - `set[str]`：允许进入正文的数据编号。

    异常：
    - 无。
    """

    # 非数组登记表不能提供任何可用批准证据。
    if not isinstance(list_data_records, list):

        # 返回空白名单，让上层阻断所有量化正文。
        return set()

    # 保存明确批准且编号非空的数据项。
    set_approved_ids: set[str] = set()  # 正文可引用数据编号

    # 逐项检查批准状态，不接受缺省同意。
    for dict_record in list_data_records:

        # 非对象记录不能表达稳定批准状态。
        if not isinstance(dict_record, Mapping):

            # 跳过损坏记录，使其无法进入白名单。
            continue

        # 兼容布尔批准位和人工 accept 决定。
        bool_approved = bool(dict_record.get("approved")) or dict_record.get("decision") == "accept"  # 明确批准状态

        # 只有批准且编号非空的记录才能进入白名单。
        if bool_approved and dict_record.get("data_id"):

            # 保存批准编号供正文引用闭包检查。
            set_approved_ids.add(str(dict_record["data_id"]))

    # 返回独立编号集合供当前验证调用使用。
    return set_approved_ids

# 检查单条正文事实是否缺少有效数据批准引用。
def validate_numeric_claim(
    int_index: int,
    dict_claim: Any,
    set_approved_ids: set[str],
) -> dict[str, str] | None:
    """检查一条量化事实的数据白名单闭包。

    参数：
    - `int_index`：事实记录顺序编号。
    - `dict_claim`：待检查事实对象。
    - `set_approved_ids`：当前获批数据编号。

    返回：
    - `dict[str, str] | None`：问题记录或通过标记。

    异常：
    - 无。
    """

    # 非对象事实无法提供正文和 data_ids。
    if not isinstance(dict_claim, Mapping):

        # 损坏事实记录直接形成阻断。
        return build_blocker("DAT001", f"数值事实记录无效:{int_index}", "重建事实对象")

    # 提取正文文本并判断其中是否存在受管数值。
    str_text = str(dict_claim.get("text", ""))  # 当前事实正文

    # 不含受管数值的事实无需数据白名单。
    if not contains_governed_number(str_text):

        # 返回空值表示当前事实通过数值门禁。
        return None

    # 读取显式数据引用，不根据数值相等关系自动匹配。
    set_claim_ids = {str(obj_id) for obj_id in dict_claim.get("data_ids", [])}  # 当前事实引用数据编号

    # 至少一个引用必须存在，且所有引用都必须已经明确批准。
    if not set_claim_ids or not set_claim_ids <= set_approved_ids:

        # 阻断未批准量化内容进入任何正式章节。
        return build_blocker("DAT001", f"未批准数值事实:{int_index}:{str_text}", "人工确认数据并绑定批准 data_id")

    # 显式编号全部获批时返回通过标记。
    return None

# 校验正文所有非豁免数值都绑定已批准的数据登记项。
def validate_numeric_claims(list_claims: Any, list_data_records: Any) -> list[dict[str, str]]:
    """检查量化事实的批准状态和 data_id 闭包。

    参数：
    - `list_claims`：正文事实片段数组。
    - `list_data_records`：数据登记记录数组。

    返回：
    - `list[dict[str, str]]`：未批准数值 findings。

    异常：
    - 无。
    """

    # 损坏正文容器必须阻断，不能当作无量化事实。
    if not isinstance(list_claims, list):

        # 返回明确容器问题，要求上游重建事实数组。
        return [build_blocker("DAT001", "数值事实容器必须为数组", "重建正文事实及 data_id 引用")]

    # 从登记表建立仅含明确批准项的白名单。
    set_approved_ids = collect_approved_data_ids(list_data_records)  # 获准进入正文的数据编号

    # 汇总每个含数值但未获批准的正文片段。
    list_findings: list[dict[str, str]] = []  # 数值批准 findings

    # 逐条调用单事实规则，避免主流程积累分支。
    for int_index, dict_claim in enumerate(list_claims, start=1):

        # 获取当前事实的可选 blocker。
        dict_finding = validate_numeric_claim(int_index, dict_claim, set_approved_ids)  # 当前量化事实检查结果

        # 只把实际问题加入报告。
        if dict_finding is not None:

            # 保留当前事实定位信息并继续检查其余记录。
            list_findings.append(dict_finding)

    # 返回全部数值白名单问题。
    return list_findings

# 检查接受决定是否为候选涉及的每份材料确认了真实用途。
def validate_accepted_source_roles(
    dict_candidate: Mapping[str, Any],
    dict_decision: Mapping[str, Any],
) -> dict[str, str] | None:
    """检查接受决定中的材料角色闭包。

    参数：
    - `dict_candidate`：当前内容绑定候选。
    - `dict_decision`：当前人工审核决定。

    返回：
    - `dict[str, str] | None`：角色缺失时的 blocker，否则为空。

    异常：
    - 无。
    """

    # 非接受决定不会贡献正式来源，无需要求材料用途字段。
    if dict_decision.get("decision") != "accept":

        # 返回空值，交由其他规则继续检查决定和指纹。
        return None

    # 清洗候选声明的来源路径，空路径不形成材料分类义务。
    list_source_paths = [
        str(obj_path).strip()  # 当前候选来源路径
        for obj_path in dict_candidate.get("source_paths", [])  # 遍历候选声明的来源
        if str(obj_path).strip()  # 忽略无法追踪的空路径
    ]  # 当前接受决定必须分类的来源路径

    # 不引用具体材料的数据候选无需创建虚假来源角色。
    if not list_source_paths:

        # 返回空值，允许独立数据候选只受 data_registry 规则治理。
        return None

    # 来源角色必须作为人工决定的一部分显式落盘。
    dict_source_roles = dict_decision.get("source_roles", {})  # 当前决定的材料角色映射

    # 非对象映射无法逐路径确认材料用途。
    if not isinstance(dict_source_roles, Mapping):

        # 使用独立规则代码阻止旧版接受结论绕过材料分类。
        return build_blocker("REV003", "接受决定缺少 source_roles 对象", "逐份确认 invention_evidence 或 prior_art")

    # 找出缺失或非法的材料角色，保留真实路径供人工定位。
    list_invalid_paths = [
        str_path  # 当前缺失或非法角色的材料路径
        for str_path in list_source_paths  # 遍历必须分类的全部来源
        if str(dict_source_roles.get(str_path, "")).strip() not in APPROVED_CONTENT_SOURCE_ROLES  # 仅接受正文角色
    ]  # 尚未完成人工用途确认的材料路径

    # 仍有未分类材料时审核闭包不能成立。
    if list_invalid_paths:

        # 返回可定位 blocker，要求人工补齐实际用途而非生成器猜测。
        return build_blocker("REV003", f"接受决定的材料角色未确认:{list_invalid_paths}", "逐份确认 invention_evidence 或 prior_art")

    # 所有来源路径都具备合法人工角色时返回通过。
    return None

# 校验人工决定与当前候选内容摘要严格绑定。
def validate_review_decisions(list_candidates: Any, list_decisions: Any) -> list[dict[str, str]]:
    """检查候选是否完成审核以及历史决定是否过时。

    参数：
    - `list_candidates`：当前候选事实数组。
    - `list_decisions`：人工审核决定数组。

    返回：
    - `list[dict[str, str]]`：审核闭包 findings。

    异常：
    - 无。
    """

    # 损坏容器不能构成已完成审核的证据。
    if not isinstance(list_candidates, list) or not isinstance(list_decisions, list):

        # 阻断 confirmed preview，要求恢复两类工件。
        return [build_blocker("REV001", "候选或审核决定容器无效", "重新生成候选并逐项审核")]

    # 按候选编号索引人工决定，重复项由后续指纹判断暴露。
    dict_decisions = {  # 候选编号到审核决定
        str(dict_item.get("candidate_id", "")): dict_item  # 当前审核决定按候选编号索引
        for dict_item in list_decisions  # 遍历人工审核决定
        if isinstance(dict_item, Mapping)  # 忽略无法表达决定字段的损坏记录
    }  # 完成按候选身份构建的决定索引

    # 汇总缺失、非法和过时决定。
    list_findings: list[dict[str, str]] = []  # 人工审核 findings

    # 逐个候选检查决定闭包，任何一项未关闭都不能确认预览。
    for dict_candidate in list_candidates:

        # 损坏候选无法绑定决定。
        if not isinstance(dict_candidate, Mapping):

            # 保留损坏候选定位信息。
            list_findings.append(build_blocker("REV001", f"候选记录无效:{dict_candidate}", "重新提取候选"))

            # 当前候选无法继续校验。
            continue

        # 读取候选身份和当前内容摘要。
        str_candidate_id = str(dict_candidate.get("candidate_id", ""))  # 当前候选编号

        # 从决定索引读取同编号记录。
        dict_decision = dict_decisions.get(str_candidate_id)  # 当前候选审核决定

        # 缺少决定或决定值非法都表示审核未关闭。
        if dict_decision is None or dict_decision.get("decision") not in {"accept", "modify", "reject"}:

            # 指明未关闭候选，供人工逐项处理。
            list_findings.append(build_blocker("REV001", f"候选尚未完成审核:{str_candidate_id}", "执行 accept、modify 或 reject"))

            # 没有有效决定时不再比较摘要。
            continue

        # 决定必须绑定与当前候选完全一致的内容摘要。
        if str(dict_decision.get("fingerprint", "")) != str(dict_candidate.get("fingerprint", "")):

            # 材料变化后旧决定立即失效，禁止继续生成确认稿。
            list_findings.append(build_blocker("REV002", f"审核决定已过时:{str_candidate_id}", "基于当前候选重新审核"))

        # 接受含来源路径的候选时还必须逐份确认材料实际用途。
        dict_role_finding = validate_accepted_source_roles(dict_candidate, dict_decision)  # 当前决定的材料角色问题

        # 只把真实角色缺口加入审核闭包报告。
        if dict_role_finding is not None:

            # 保留独立角色问题，禁止默认把论文或专利归为发明证据。
            list_findings.append(dict_role_finding)

    # 返回审核闭包问题。
    return list_findings

# 从明确接受且指纹仍匹配的数据候选构建批准登记表。
def build_approved_data_registry(list_candidates: Any, list_decisions: Any) -> list[dict[str, Any]]:
    """构建正式模型可消费的数据白名单。

    参数：
    - `list_candidates`：当前内容绑定候选数组。
    - `list_decisions`：人工审核决定数组。

    返回：
    - `list[dict[str, Any]]`：仅含有效接受决定的数据登记表。

    异常：
    - 无。
    """

    # 容器损坏时返回空白名单，后续数值门禁会阻断正文。
    if not isinstance(list_candidates, list) or not isinstance(list_decisions, list):

        # 空数组不代表审核完成，只表示没有可用批准数据。
        return []

    # 按候选编号索引人工决定，便于验证指纹和结论。
    dict_decisions = {  # 候选编号到人工决定
        str(dict_item.get("candidate_id", "")): dict_item  # 当前候选对应的决定记录
        for dict_item in list_decisions  # 遍历调用方提供的审核决定
        if isinstance(dict_item, Mapping)  # 仅索引能够表达决定字段的对象
    }  # 完成批准数据筛选使用的决定索引

    # 保存按候选顺序形成的批准数据记录。
    list_registry: list[dict[str, Any]] = []  # 已批准数据登记表

    # 逐项筛选 data_claim，其他候选类型不能进入数值白名单。
    for dict_candidate in list_candidates:

        # 只处理结构完整的数据候选。
        if not isinstance(dict_candidate, Mapping) or dict_candidate.get("candidate_type") != "data_claim":

            # 跳过主案、公式或其他非数值候选。
            continue

        # 读取同编号人工决定，缺失时保持未批准。
        dict_decision = dict_decisions.get(str(dict_candidate.get("candidate_id", "")))  # 当前数据候选决定

        # 仅接受明确 accept 且内容摘要仍匹配的决定。
        if (
            not isinstance(dict_decision, Mapping)
            or dict_decision.get("decision") != "accept"
            or str(dict_decision.get("fingerprint", "")) != str(dict_candidate.get("fingerprint", ""))
        ):

            # 无效或过时决定不得形成 data_id。
            continue

        # 读取候选载荷中的完整量化原句。
        dict_payload = dict_candidate.get("payload", {})  # 当前数据候选载荷

        # 非对象载荷无法提供可审计文本。
        if not isinstance(dict_payload, Mapping) or not dict_payload.get("text"):

            # 损坏载荷保持未批准状态。
            continue

        # 为有效接受的数据候选生成独立 data_id。
        list_registry.append(
            {
                "data_id": f"D{len(list_registry) + 1:03d}",  # 正式数据登记编号
                "text": str(dict_payload["text"]),  # 获批量化事实原文
                "approved": True,  # 明确人工批准状态
                "candidate_id": str(dict_candidate["candidate_id"]),  # 来源审核候选编号
                "fingerprint": str(dict_candidate["fingerprint"]),  # 决定绑定内容摘要
            }
        )

    # 返回仅含有效接受项的数据白名单。
    return list_registry

# 递归收集候选事实载荷中的字符串叶子。
def collect_payload_texts(obj_value: Any) -> list[str]:
    """收集单个候选载荷中的非空文本。

    参数：
    - `obj_value`：候选 payload 的任意 JSON 兼容值。

    返回：
    - `list[str]`：保持原始遍历顺序的非空文本叶子。

    异常：
    - 无。
    """

    # 字符串叶子清洗后直接返回，空值不进入来源摘录。
    if isinstance(obj_value, str):

        # 清理首尾空白，保持正文重合比较稳定。
        str_text = obj_value.strip()  # 当前候选载荷文本

        # 非空字符串形成单元素结果，空字符串形成空结果。
        return [str_text] if str_text else []

    # 映射节点按插入顺序汇总字段值中的文本。
    if isinstance(obj_value, Mapping):

        # 通过递归结果展开保持原始字段和值顺序。
        return [
            str_text  # 当前映射子节点中的文本叶子
            for obj_child in obj_value.values()  # 遍历当前映射全部字段值
            for str_text in collect_payload_texts(obj_child)  # 展开当前字段值的递归结果
        ]

    # 非字符串序列按原始顺序汇总元素中的文本。
    if isinstance(obj_value, Sequence):

        # 通过递归结果展开保持原始元素顺序。
        return [
            str_text  # 当前序列子节点中的文本叶子
            for obj_child in obj_value  # 遍历当前序列全部元素
            for str_text in collect_payload_texts(obj_child)  # 展开当前元素的递归结果
        ]

    # 数值、布尔值和空值不作为原文摘录。
    return []

# 判断候选是否具有当前指纹下的明确接受决定。
def is_candidate_accepted(dict_candidate: Mapping[str, Any], dict_decisions: Mapping[str, Any]) -> bool:
    """判断候选是否可以贡献正式来源。

    参数：
    - `dict_candidate`：当前内容绑定候选。
    - `dict_decisions`：候选编号到人工决定的索引。

    返回：
    - `bool`：决定为 accept 且指纹匹配时为真。

    异常：
    - 无。
    """

    # 按候选编号读取对应审核决定。
    str_candidate_id = str(dict_candidate.get("candidate_id", ""))  # 来源清单筛选候选编号

    # 获取当前候选的人工审核记录。
    dict_decision = dict_decisions.get(str_candidate_id)  # 来源清单筛选决定

    # 只有结构完整、明确接受且内容摘要未变化的决定有效。
    return bool(
        isinstance(dict_decision, Mapping)
        and dict_decision.get("decision") == "accept"
        and str(dict_decision.get("fingerprint", "")) == str(dict_candidate.get("fingerprint", ""))
    )

# 把单个获批候选的来源路径和原文摘录并入聚合清单。
def merge_candidate_sources(
    dict_manifest_by_path: dict[str, dict[str, Any]],
    dict_candidate: Mapping[str, Any],
    dict_decision: Mapping[str, Any],
) -> None:
    """合并一个获批候选贡献的来源信息。

    参数：
    - `dict_manifest_by_path`：按路径聚合的可变来源清单。
    - `dict_candidate`：已经通过接受决定检查的候选。
    - `dict_decision`：包含人工确认材料角色的接受决定。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 从当前候选事实载荷收集可执行重合检查的原文摘录。
    list_candidate_texts = collect_payload_texts(dict_candidate.get("payload", {}))  # 当前获批候选摘录

    # 读取人工确认的逐路径角色，缺失项保留 unknown 供正式验证器阻断。
    dict_source_roles = dict_decision.get("source_roles", {})  # 当前接受决定的材料角色映射

    # 逐条来源路径聚合当前候选摘录。
    for obj_source_path in dict_candidate.get("source_paths", []):

        # 清洗来源路径，空路径不能形成可审计记录。
        str_source_path = str(obj_source_path).strip()  # 当前获批来源路径

        # 空路径不进入来源清单。
        if not str_source_path:

            # 继续处理当前候选其余来源。
            continue

        # 从人工决定读取当前路径的实际用途，禁止按候选类型猜测。
        str_source_role = str(dict_source_roles.get(str_source_path, "unknown")).strip()  # 当前材料人工角色

        # 首次出现路径建立待编号的来源记录。
        dict_manifest_record = dict_manifest_by_path.setdefault(  # 当前来源聚合记录
            str_source_path,  # 以真实来源路径作为聚合键
            {
                "path": str_source_path,  # 当前来源本地相对或受管路径
                "role": str_source_role,  # 人工确认的材料实际用途
                "source_texts": [],  # 当前来源获批原文摘录
            },
        )

        # 同一路径被不同决定赋予冲突角色时保留 unknown，让来源门禁阻断。
        if dict_manifest_record.get("role") != str_source_role:

            # 不在生成层选择任一角色，明确保留待人工修复状态。
            dict_manifest_record["role"] = "unknown"  # 冲突材料角色

        # 追加尚未登记的摘录，避免同一路径因多个候选重复。
        dict_manifest_record["source_texts"].extend(
            str_text
            for str_text in list_candidate_texts
            if str_text not in dict_manifest_record["source_texts"]
        )

# 从人工接受且指纹匹配的候选构建来源与原文摘录登记表。
def build_approved_source_manifest(list_candidates: Any, list_decisions: Any) -> list[dict[str, Any]]:
    """构建正式模型可消费的获批来源清单。

    参数：
    - `list_candidates`：当前内容绑定候选数组。
    - `list_decisions`：当前人工审核决定数组。

    返回：
    - `list[dict[str, Any]]`：按来源首次出现顺序形成的来源登记表。

    异常：
    - 无。
    """

    # 容器损坏时不能推断任何来源已获批准。
    if not isinstance(list_candidates, list) or not isinstance(list_decisions, list):

        # 返回空清单，让后续来源或正文门禁决定是否阻断。
        return []

    # 按候选编号索引人工决定，供接受结论和指纹闭包共同判断。
    dict_decisions = {  # 获批来源筛选使用的决定索引
        str(dict_item.get("candidate_id", "")): dict_item  # 当前候选对应的审核决定
        for dict_item in list_decisions  # 遍历调用方提供的全部决定
        if isinstance(dict_item, Mapping)  # 只索引结构完整的决定对象
    }  # 完成人工决定索引

    # 用插入有序映射按路径聚合同一来源的多个获批摘录。
    dict_manifest_by_path: dict[str, dict[str, Any]] = {}  # 来源路径到登记记录

    # 逐个候选筛选当前指纹下的明确接受决定。
    for dict_candidate in list_candidates:

        # 结构完整且决定有效的候选才并入来源清单。
        if isinstance(dict_candidate, Mapping) and is_candidate_accepted(dict_candidate, dict_decisions):

            # 读取已通过接受与指纹检查的决定，提供人工材料角色。
            dict_decision = dict_decisions[str(dict_candidate.get("candidate_id", ""))]  # 当前有效接受决定

            # 合并当前获批候选的路径、人工角色和摘录。
            merge_candidate_sources(dict_manifest_by_path, dict_candidate, dict_decision)

    # 为按路径首次出现顺序形成的记录分配稳定来源编号。
    list_manifest = [  # 最终获批来源登记表
        {
            "source_id": f"S{int_index:03d}",  # 正式来源编号
            **dict_record,  # 当前来源路径、角色和获批摘录
        }
        for int_index, dict_record in enumerate(dict_manifest_by_path.values(), start=1)  # 按来源首次出现顺序编号
    ]  # 完成来源清单稳定编号

    # 返回仅含有效接受候选的来源登记表。
    return list_manifest

# 校验技术特征通过编号精确引用现有证据，而不是关键词相似推断。
def validate_feature_evidence(list_features: Any, list_evidence: Any) -> list[dict[str, str]]:
    """检查 feature_id 到 evidence_id 的显式闭包。

    参数：
    - `list_features`：技术特征数组。
    - `list_evidence`：证据登记数组。

    返回：
    - `list[dict[str, str]]`：技术特征证据 findings。

    异常：
    - 无。
    """

    # 只从合法证据对象收集明确编号。
    set_evidence_ids = {  # 已登记证据编号集合
        str(dict_item.get("evidence_id", dict_item.get("id", "")))  # 兼容现有 id 与新版 evidence_id
        for dict_item in list_evidence  # 遍历正式证据登记记录
        if isinstance(list_evidence, list) and isinstance(dict_item, Mapping)  # 仅接纳数组中的对象记录
    }  # 完成兼容旧字段后的证据身份集合

    # 非数组特征容器无法建立精确映射。
    if not isinstance(list_features, list):

        # 返回结构 blocker，要求重建技术特征登记表。
        return [build_blocker("EVD003", "技术特征容器必须为数组", "重建 feature_id 与 evidence_ids")]

    # 汇总缺失或悬空映射。
    list_findings: list[dict[str, str]] = []  # 技术特征证据 findings

    # 按特征逐项检查显式编号闭包。
    for dict_feature in list_features:

        # 损坏特征记录不能进入正式技术方案。
        if not isinstance(dict_feature, Mapping):

            # 报告损坏记录并继续汇总其他特征。
            list_findings.append(build_blocker("EVD003", f"技术特征记录无效:{dict_feature}", "重建技术特征对象"))

            # 当前记录无法读取编号。
            continue

        # 保存当前特征编号用于 finding 定位。
        str_feature_id = str(dict_feature.get("feature_id", ""))  # 当前技术特征编号

        # 读取显式证据编号，不进行任何文本关键词匹配。
        set_feature_evidence = {str(obj_id) for obj_id in dict_feature.get("evidence_ids", [])}  # 特征引用证据编号

        # 空映射或悬空编号都表示当前技术点缺少事实支撑。
        if not set_feature_evidence or not set_feature_evidence <= set_evidence_ids:

            # 阻断该特征进入技术方案和权利要求。
            list_findings.append(build_blocker("EVD003", f"技术特征证据未闭合:{str_feature_id}", "显式绑定存在的 evidence_id"))

    # 返回精确证据映射问题。
    return list_findings

# 按公开日相对本案参考日计算文献允许用途。
def classify_prior_art_timing(dict_record: Mapping[str, Any], str_reference_date: str) -> dict[str, Any]:
    """分类文献的时间状态并限定自动使用范围。

    参数：
    - `dict_record`：包含 publication_date 的文献记录。
    - `str_reference_date`：本案现有技术参考日。

    返回：
    - `dict[str, Any]`：时间状态与允许用途。

    异常：
    - `ValueError`：参考日格式无效时由日期解析上抛。
    """

    # 解析参考日，确保比较使用真实日期而不是字符串排序。
    obj_reference_date = date.fromisoformat(str_reference_date)  # 本案现有技术参考日

    # 读取公开日原始值，缺失时保持 unknown 而不猜测。
    str_publication_date = str(dict_record.get("publication_date", "")).strip()  # 文献公开日文本

    # 缺少公开日的文献只能进入人工审阅或背景说明。
    if not str_publication_date:

        # 返回明确未知状态和受限用途。
        return {"temporal_status": "unknown", "allowed_uses": ["background_only", "human_review"]}

    # 尝试解析公开日，损坏日期同样保持未知状态。
    try:

        # ISO 日期是正式接口唯一接受的自动比较格式。
        obj_publication_date = date.fromisoformat(str_publication_date)  # 文献公开日期

    # 无效公开日不能中断全部审阅，但不得作为参考日前证据。
    except ValueError:

        # 返回未知状态，交由人工核验原始文献。
        return {"temporal_status": "unknown", "allowed_uses": ["background_only", "human_review"]}

    # 参考日之前公开的记录才可自动参与现有技术分析。
    if obj_publication_date < obj_reference_date:

        # 返回参考日前状态和允许用途。
        return {"temporal_status": "pre_reference", "allowed_uses": ["background", "inventive_step"]}

    # 同日公开仍需人工核验时区、公开时点和法律含义。
    if obj_publication_date == obj_reference_date:

        # 同日记录不自动给出法律结论。
        return {"temporal_status": "same_day", "allowed_uses": ["background_only", "human_review"]}

    # 参考日之后公开的文献不得自动支撑创造性判断。
    return {"temporal_status": "post_reference", "allowed_uses": ["background_only", "human_review"]}

# 汇总双语连续重合结果并为每份原始材料保留单一定位项。
def has_chinese_overlap(str_draft: str, str_source_text: str) -> bool:
    """判断单份来源是否与正文存在连续中文重合。

    参数：
    - `str_draft`：待交付正文。
    - `str_source_text`：单份来源文本。

    返回：
    - `bool`：达到中文阈值时为真。

    异常：
    - 无。
    """

    # 提取不含标点空白的连续中文序列。
    list_sequences = re.findall(r"[\u4e00-\u9fff]+", str_source_text)  # 来源中文连续片段

    # 逐个检查足够长的中文序列。
    for str_sequence in list_sequences:

        # 短片段不构成长段搬运。
        if len(str_sequence) < MIN_CHINESE_OVERLAP:

            # 继续检查下一中文片段。
            continue

        # 滑动检查固定阈值窗口。
        for int_offset in range(len(str_sequence) - MIN_CHINESE_OVERLAP + 1):

            # 截取当前连续窗口供正文查找。
            str_window = str_sequence[int_offset : int_offset + MIN_CHINESE_OVERLAP]  # 当前中文重合窗口

            # 任一窗口命中即达到阻断阈值。
            if str_window in str_draft:

                # 返回命中结果，避免同一来源重复扫描。
                return True

    # 全部窗口均未命中时返回通过结果。
    return False

# 判断单份来源是否与正文存在连续英文词序列重合。
def has_english_overlap(str_draft: str, str_source_text: str) -> bool:
    """判断单份来源是否与正文存在连续英文重合。

    参数：
    - `str_draft`：待交付正文。
    - `str_source_text`：单份来源文本。

    返回：
    - `bool`：达到英文阈值时为真。

    异常：
    - 无。
    """

    # 规范化来源英文单词并保留顺序。
    list_source_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", str_source_text.lower())  # 来源英文单词

    # 规范化正文英文单词并保留顺序。
    list_draft_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", str_draft.lower())  # 正文英文单词

    # 组合正文词序列供固定窗口查找。
    str_draft_words = " ".join(list_draft_words)  # 规范化正文英文文本

    # 逐个检查十五词来源窗口。
    for int_offset in range(max(0, len(list_source_words) - MIN_ENGLISH_OVERLAP + 1)):

        # 拼接当前来源词窗口，保留连续顺序约束。
        str_window = " ".join(list_source_words[int_offset : int_offset + MIN_ENGLISH_OVERLAP])  # 当前英文重合窗口

        # 非空窗口在正文中连续出现即达到阈值。
        if str_window and str_window in str_draft_words:

            # 返回命中结果，避免同一来源重复 findings。
            return True

    # 全部英文窗口均未命中时返回通过结果。
    return False

# 检查正文是否连续搬运用户材料中的长中文句或英文词序列。
def validate_text_overlap(str_draft: str, list_source_texts: Sequence[str]) -> list[dict[str, str]]:
    """识别超过阈值的连续文本重合。

    参数：
    - `str_draft`：待交付正文。
    - `list_source_texts`：用户材料原文数组。

    返回：
    - `list[dict[str, str]]`：长文本重合 findings。

    异常：
    - 无。
    """

    # 汇总每个来源的首个阻断重合，避免对同一原句重复刷屏。
    list_findings: list[dict[str, str]] = []  # 文本重合 findings

    # 逐份来源分别调用中文和英文阈值规则。
    for int_source_index, str_source_text in enumerate(list_source_texts, start=1):

        # 中文连续窗口优先判定。
        if has_chinese_overlap(str_draft, str(str_source_text)):

            # 每份来源只登记一个中文重合 finding。
            list_findings.append(build_blocker("TXT001", f"正文与来源{int_source_index}存在连续中文重合", "改写为基于证据的专利表达"))

            # 当前来源已阻断，无需继续检查英文。
            continue

        # 未命中中文时再检查英文连续词窗口。
        if has_english_overlap(str_draft, str(str_source_text)):

            # 英文词序命中时记录来源序号和改写要求。
            list_findings.append(build_blocker("TXT001", f"正文与来源{int_source_index}存在连续英文重合", "改写为基于证据的专利表达"))

    # 返回全部来源的长文本重合问题。
    return list_findings

# 从来源登记表提取专供重合检查的原文摘录。
def collect_source_texts(list_sources: Any) -> list[str]:
    """收集来源登记记录中的原文摘录。

    参数：
    - `list_sources`：版本三来源登记表。

    返回：
    - `list[str]`：保持登记顺序的非空来源摘录。

    异常：
    - 无。
    """

    # 损坏容器无法提供可信来源摘录，来源结构问题由专用规则报告。
    if not isinstance(list_sources, list):

        # 返回空数组，避免重复生成来源容器 finding。
        return []

    # 按来源及摘录原始顺序保存文本，便于 finding 序号稳定。
    list_source_texts: list[str] = []  # 来源原文摘录数组

    # 逐项读取显式 source_texts，不从路径或标题反推原文。
    for dict_source in list_sources:

        # 非对象来源已经由来源角色规则报告，此处跳过。
        if not isinstance(dict_source, Mapping):

            # 继续检查后续合法来源。
            continue

        # 只有现有技术或显式受复制限制的材料进入长段文本重合门。
        bool_copy_restricted = (  # 当前来源是否受长段复制限制
            dict_source.get("role") == "prior_art"  # 现有技术属于外部来源
            or bool(dict_source.get("copy_restricted"))  # 人工显式声明的其他限制来源
        )

        # 发明事实来源允许精确保留必要技术特征，避免改变技术含义。
        if not bool_copy_restricted:

            # 继续检查下一受管来源。
            continue

        # 读取当前来源显式登记的原文摘录数组。
        obj_source_texts = dict_source.get("source_texts", [])  # 当前来源原文摘录值

        # 字符串本身不是合法摘录数组，防止逐字符扫描。
        if not isinstance(obj_source_texts, Sequence) or isinstance(obj_source_texts, str):

            # 非数组摘录不能进入文本重合门禁。
            continue

        # 逐条清洗来源摘录，只保留非空字符串。
        for obj_source_text in obj_source_texts:

            # 规范当前摘录的首尾空白。
            str_source_text = str(obj_source_text).strip()  # 清洗后用于连续窗口扫描的摘录

            # 非空摘录进入稳定检查数组。
            if str_source_text:

                # 保存当前来源原文供交付正文重合检查。
                list_source_texts.append(str_source_text)

    # 返回全部显式来源摘录。
    return list_source_texts

# 校验术语规范名称和别名在整个登记表中具有唯一归属。
def validate_term_registry(list_terms: Any) -> list[dict[str, str]]:
    """检查术语身份、规范名称和别名冲突。

    参数：
    - `list_terms`：版本三术语登记表。

    返回：
    - `list[dict[str, str]]`：术语结构或唯一性 findings。

    异常：
    - 无。
    """

    # 非数组术语容器不能建立稳定术语边界。
    if not isinstance(list_terms, list):

        # 使用统一术语代码要求重建登记表。
        return [build_blocker("TRM001", "term_registry 必须为数组", "重建术语规范名称和允许别名")]

    # 保存规范化术语文本的首次归属编号，用于发现跨记录冲突。
    dict_owner_by_text: dict[str, str] = {}  # 术语文本到术语编号

    # 汇总损坏记录、空名称和跨记录冲突。
    list_findings: list[dict[str, str]] = []  # 术语登记 findings

    # 逐条验证术语记录，禁止从正文自动猜测别名关系。
    for dict_term in list_terms:

        # 非对象记录无法表达术语身份。
        if not isinstance(dict_term, Mapping):

            # 保存损坏记录并继续检查其他术语。
            list_findings.append(build_blocker("TRM001", f"术语记录无效:{dict_term}", "重建术语记录"))

            # 当前损坏记录不再参与字段检查。
            continue

        # 读取显式术语编号，供冲突 finding 定位。
        str_term_id = str(dict_term.get("term_id", "")).strip()  # 当前术语编号

        # 读取并规范化术语名称，空名称不能进入正文。
        str_canonical = str(dict_term.get("canonical", "")).strip()  # 当前规范术语名称

        # 读取别名原始值，必须是数组而不是单个字符串。
        obj_aliases = dict_term.get("aliases", [])  # 当前术语别名值

        # 缺少身份、规范名称或别名数组时形成结构 blocker。
        if not str_term_id or not str_canonical or not isinstance(obj_aliases, list):

            # 指明当前损坏术语，要求人工恢复唯一名称边界。
            list_findings.append(build_blocker("TRM001", f"术语字段无效:{dict_term}", "补齐 term_id、canonical 和 aliases"))

            # 损坏记录不参与冲突登记。
            continue

        # 将规范名称和别名放入同一归属检查序列。
        list_term_texts = [str_canonical] + [str(obj_alias).strip() for obj_alias in obj_aliases]  # 当前术语全部允许文本

        # 逐个文本检查是否已归属于其他术语编号。
        for str_term_text in list_term_texts:

            # 空别名没有语义，应作为损坏记录阻断。
            if not str_term_text:

                # 空别名破坏术语清单的明确性。
                list_findings.append(build_blocker("TRM001", f"术语包含空别名:{str_term_id}", "删除空别名或补充真实名称"))

                # 继续检查当前术语其余文本。
                continue

            # 使用大小写不敏感键覆盖英文术语，同时保留中文原义。
            str_normalized_text = str_term_text.casefold()  # 当前术语冲突比较键

            # 读取当前文本此前登记的术语编号。
            str_existing_owner = dict_owner_by_text.get(str_normalized_text, "")  # 当前文本既有归属

            # 已归属于其他术语时形成一词多义 blocker。
            if str_existing_owner and str_existing_owner != str_term_id:

                # 报告冲突文本和两个术语编号，便于人工统一命名。
                list_findings.append(
                    build_blocker(
                        "TRM001",
                        f"术语文本归属冲突:{str_term_text}:{str_existing_owner}:{str_term_id}",
                        "统一规范名称或删除冲突别名",
                    )
                )

                # 冲突文本保持首次归属，避免后续报告顺序漂移。
                continue

            # 首次出现或同一术语内重复时登记当前归属。
            dict_owner_by_text[str_normalized_text] = str_term_id  # 当前术语文本唯一归属

    # 返回全部术语登记问题。
    return list_findings

# 校验现有技术证据的公开时序与声明用途相容。
def validate_prior_art_usage(obj_evidence_registry: Any) -> list[dict[str, str]]:
    """检查参考日之后或日期未知文献的用途越界。

    参数：
    - `obj_evidence_registry`：版本三证据登记表。

    返回：
    - `list[dict[str, str]]`：文献时序用途 findings。

    异常：
    - 无。
    """

    # 非对象证据登记表由结构验证器报告，此处避免重复噪声。
    if not isinstance(obj_evidence_registry, Mapping):

        # 返回空数组表示当前专用规则无法继续。
        return []

    # 读取证据记录数组，损坏容器由证据结构规则处理。
    obj_records = obj_evidence_registry.get("records", [])  # 原始证据记录数组

    # 非数组记录不能执行逐项时序检查。
    if not isinstance(obj_records, list):

        # 返回空数组，保持单一问题来源。
        return []

    # 汇总所有创造性用途越界问题。
    list_findings: list[dict[str, str]] = []  # 文献时序用途 findings

    # 只检查显式声明为 prior_art 的证据记录。
    for dict_record in obj_records:

        # 非对象或非现有技术记录不进入本规则。
        if not isinstance(dict_record, Mapping) or dict_record.get("kind") != "prior_art":

            # 继续检查后续证据记录。
            continue

        # 读取显式用途数组，未声明创造性用途时不扩大解释。
        obj_uses = dict_record.get("uses", [])  # 当前文献声明用途

        # 仅对明确包含 inventive_step 的数组执行严格时序门。
        if not isinstance(obj_uses, list) or "inventive_step" not in obj_uses:

            # 背景说明用途留给其他引用完整性规则。
            continue

        # 读取本案参考日，缺失值不得由生成器自行推测。
        str_reference_date = str(dict_record.get("reference_date", "")).strip()  # 当前文献比较参考日

        # 缺少参考日时无法证明文献可用于创造性。
        if not str_reference_date:

            # 要求人工补充本案参考日后重新分类。
            list_findings.append(build_blocker("CIT001", f"创造性文献缺少参考日:{dict_record}", "补充 reference_date 并重新核验用途"))

            # 当前记录无法继续做日期比较。
            continue

        # 日期格式错误同样不能作为自动创造性证据。
        try:

            # 调用统一时间分类规则，保持状态语义单一来源。
            dict_timing = classify_prior_art_timing(dict_record, str_reference_date)  # 当前文献时间分类

        # 捕获无效参考日，转为稳定 blocker 而不中断整份报告。
        except ValueError:

            # 提示人工修正 ISO 日期后重新执行。
            list_findings.append(build_blocker("CIT001", f"文献参考日无效:{dict_record}", "使用 YYYY-MM-DD 格式补充 reference_date"))

            # 当前记录无法形成可信分类。
            continue

        # 只有参考日前公开状态可以自动参与创造性判断。
        if dict_timing.get("temporal_status") != "pre_reference":

            # 晚公开、同日或日期未知文献统一限制为背景或人工审阅用途。
            list_findings.append(build_blocker("CIT001", f"文献时序不允许创造性用途:{dict_record}", "移除 inventive_step 用途或补充合规文献"))

    # 返回全部文献时序用途问题。
    return list_findings

# 汇总版本三模型中跨事实域的结构、待办和附图来源问题。
def validate_delivery_model(dict_model: Mapping[str, Any]) -> list[dict[str, str]]:
    """执行正式交付模型的事实完整性总门禁。

    参数：
    - `dict_model`：待验证版本三结构化模型。

    返回：
    - `list[dict[str, str]]`：跨事实域 blocker findings。

    异常：
    - 无。
    """

    # 汇总缺失字段、来源角色、数值批准、待办和附图来源问题。
    list_findings: list[dict[str, str]] = []  # 模型事实完整性 findings

    # 计算版本三要求但当前模型未声明的登记表。
    list_missing_keys = sorted(REQUIRED_MODEL_KEYS - set(dict_model))  # 缺失顶层字段

    # 每个缺失字段形成独立 blocker，便于生成链精确重建。
    for str_key in list_missing_keys:

        # 登记当前缺失事实域。
        list_findings.append(build_blocker("MOD002", f"版本三模型缺少字段:{str_key}", "重新生成完整模型"))

    # 复用材料角色规则，防止同一来源跨用途污染。
    list_findings.extend(validate_source_manifest(dict_model.get("source_manifest")))

    # 把章节正文转换为数值门禁可消费的事实片段。
    list_sections = dict_model.get("sections", [])  # 当前章节事实数组

    # 只保留对象章节，损坏章节由专用结构验证器报告。
    list_numeric_claims = [  # 供数值白名单检查的章节事实
        {
            "text": str(dict_section.get("content", "")),  # 当前章节正文
            "data_ids": list(dict_section.get("data_ids", [])),  # 当前章节显式数据引用
        }
        for dict_section in list_sections  # 遍历版本三章节记录
        if isinstance(list_sections, list) and isinstance(dict_section, Mapping)  # 仅转换数组中的对象章节
    ]  # 完成章节正文与数据引用的统一检查输入

    # 复用数据白名单规则，阻止正文携带未批准量化结果。
    list_findings.extend(validate_numeric_claims(list_numeric_claims, dict_model.get("data_registry")))

    # 拼接全部章节正文，供来源摘录重合检查统一消费。
    str_draft_text = "\n".join(dict_claim["text"] for dict_claim in list_numeric_claims)  # 当前模型全部章节正文

    # 从来源登记表读取显式原文摘录，不扫描未授权路径。
    list_source_texts = collect_source_texts(dict_model.get("source_manifest"))  # 当前模型来源原文摘录

    # 阻断正文长段复用论文或其他材料原文。
    list_findings.extend(validate_text_overlap(str_draft_text, list_source_texts))

    # 检查术语规范名称和别名在全模型内保持唯一归属。
    list_findings.extend(validate_term_registry(dict_model.get("term_registry")))

    # 检查文献公开时序是否允许其声明的创造性用途。
    list_findings.extend(validate_prior_art_usage(dict_model.get("evidence_registry")))

    # 读取待办数组，非数组值按未关闭状态处理。
    list_pending_items = dict_model.get("pending_items")  # 当前人工待办数组

    # 任一待办未明确 closed 都不能生成 confirmed preview。
    if not isinstance(list_pending_items, list) or any(
        not isinstance(dict_item, Mapping) or dict_item.get("status") != "closed"
        for dict_item in list_pending_items
    ):

        # 统一形成审核未关闭 blocker。
        list_findings.append(build_blocker("REV003", "模型仍含未关闭人工待办", "逐项关闭 pending_items"))

    # 读取附图登记表，缺失容器已经由 MOD002 报告。
    list_figures = dict_model.get("figure_registry", [])  # 当前附图登记记录

    # 逐图要求来源编号和正文引用同时存在。
    for dict_figure in list_figures if isinstance(list_figures, list) else []:

        # 非对象附图或缺少 provenance、section_ids 均不可交付。
        if (
            not isinstance(dict_figure, Mapping)
            or not dict_figure.get("provenance")
            or not dict_figure.get("section_ids")
        ):

            # 阻断生成器自行补造图名、图号或图示对象。
            list_findings.append(build_blocker("FIG001", f"附图来源或正文绑定缺失:{dict_figure}", "补充真实 provenance 与 section_ids"))

    # 返回模型级事实完整性问题。
    return list_findings
