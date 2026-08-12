"""协调专利技术交底书的 DOCX 导出流程。"""

# 延迟解析类型注解，保持拆分模块间的类型合同稳定。
from __future__ import annotations

# 标准库负责按同目录真实路径加载拆分模块，兼容 runpy 与文件规格加载。
import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 固定拆分模块所在目录，避免依赖调用方是否把脚本目录加入 sys.path。
PATH_EXPORT_MODULE_DIR = Path(__file__).resolve().parent  # DOCX 导出模块目录

# 按文件位置加载一个内部模块，并用稳定名称登记其依赖关系。
def load_export_internal_module(str_module_name: str) -> Any:
    """按同目录文件加载导出内部模块。

    参数：
    - `str_module_name`：不含扩展名的内部模块名称。

    返回：
    - `Any`：已经执行并登记的模块对象。

    异常：
    - `ImportError`：模块规格或加载器不可用。
    """

    # 从受控导出目录拼出内部模块真实路径。
    path_module = PATH_EXPORT_MODULE_DIR / f"{str_module_name}.py"  # 内部模块路径

    # 读取稳定名称下已登记的模块，判断它是否属于当前技能 root。
    obj_registered_module = sys.modules.get(str_module_name)  # 已登记的同名内部模块

    # 只有真实文件路径一致时才复用模块对象，保持同 root 对象身份。
    if obj_registered_module is not None:

        # 读取已登记模块文件路径；无文件来源的对象不能证明属于当前 root。
        str_registered_file = getattr(obj_registered_module, "__file__", "")  # 已登记模块来源路径

        # 当前路径一致时返回原对象，避免重复执行模块级常量初始化。
        if str_registered_file and Path(str_registered_file).resolve() == path_module.resolve():

            # 返回当前技能 root 已完成加载的同名内部模块。
            return obj_registered_module

    # 为同目录模块创建不依赖 sys.path 的加载规格。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, path_module)  # 内部模块加载规格

    # 加载规格或加载器缺失时阻断不完整的兼容导入。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出包含真实路径的稳定错误，便于定位技能包缺件。
        raise ImportError(f"> ERR: [Python] 无法加载 DOCX 导出内部模块：{path_module}")

    # 先创建并登记模块，确保后续内部 import 复用同一对象。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 待执行内部模块

    # 提前登记模块，使下游拆分模块能按稳定名称解析依赖。
    sys.modules[str_module_name] = obj_module  # 内部模块注册项

    # 执行真实模块源码；组事务统一负责所有稳定键的失败回滚。
    obj_specification.loader.exec_module(obj_module)

    # 返回已登记模块供兼容导出流程读取名称。
    return obj_module

# 按依赖顺序加载四类实现模块，后加载模块可以直接引用前序名称。
TUPLE_EXPORT_MODULE_NAMES = (  # 导出实现模块加载顺序
    "export_runtime_support",  # 运行时与加载支持
    "markdown_template_parser",  # Markdown 与模板章节解析
    "fallback_docx_builder",  # 无严格模板时的 DOCX 构造
    "docx_package_validator",  # 最终 DOCX 包与公式校验
)

# 以完整稳定键组为事务边界加载全部导出职责模块。
def load_export_module_group() -> list[Any]:
    """原子加载当前 root 的全部导出职责模块。

    参数：
    - 无。

    返回：
    - `list[Any]`：按依赖顺序完成加载的导出职责模块。

    异常：
    - 任一 helper 加载失败时恢复整组稳定键后原样上抛。
    """

    # 只记录事务开始时真实存在的稳定键及其对象身份。
    dict_original_modules = {  # 导出模块组事务快照
        str_module_name: sys.modules[str_module_name]  # 事务开始前的原模块对象
        for str_module_name in TUPLE_EXPORT_MODULE_NAMES  # 覆盖完整导出稳定键组
        if str_module_name in sys.modules  # 原先不存在的键不写入快照
    }

    # 顺序加载整组 helper，成功时保留当前 root 的完整模块组。
    try:

        # 返回完整模块列表，供兼容名称收集保持旧覆盖顺序。
        return [
            load_export_internal_module(str_module_name)  # 当前导出职责模块
            for str_module_name in TUPLE_EXPORT_MODULE_NAMES  # 固定依赖加载顺序
        ]

    # 任一 helper 失败时必须撤销本轮所有前序稳定键替换。
    except Exception:

        # 按完整稳定键组恢复原对象或删除本轮新增键。
        for str_module_name in TUPLE_EXPORT_MODULE_NAMES:

            # 原先存在的键恢复为事务开始前的同一对象。
            if str_module_name in dict_original_modules:

                # 恢复导出 helper 的原始注册身份。
                sys.modules[str_module_name] = dict_original_modules[str_module_name]  # 原导出模块对象

            # 原先不存在的键必须删除，避免留下当前 root 的部分模块组。
            else:

                # 清除本轮事务新登记的导出 helper。
                sys.modules.pop(str_module_name, None)

        # 保留真实加载异常和 traceback，供调用方定位具体缺件。
        raise

# 收集拆分模块的公共名称，供协调器一次性恢复旧 import 面。
def collect_export_compatibility() -> dict[str, Any]:
    """收集四个内部模块的非私有名称。

    参数：
    - 无。

    返回：
    - `dict[str, Any]`：原入口需要继续暴露的名称与对象。

    异常：
    - 内部模块加载失败时由加载函数继续上抛。
    """

    # 初始化兼容名称表，后加载模块沿用原单文件中的覆盖顺序。
    dict_compatibility: dict[str, Any] = {}  # 协调器公共兼容名称表

    # 原子加载完整职责模块组，再按固定依赖顺序恢复公共名称。
    for obj_export_module in load_export_module_group():

        # 逐项检查模块命名空间，完整保留拆分前可直接导入的 helper。
        for str_export_name in dir(obj_export_module):

            # 私有实现名称不属于原公共兼容面，无需从协调器继续暴露。
            if str_export_name.startswith("_"):

                # 跳过模块内部私有名称，继续处理下一个候选。
                continue

            # 读取当前公共名称绑定的真实对象。
            obj_export_value = getattr(obj_export_module, str_export_name)  # 兼容导出对象

            # 写入兼容表，保持原单文件后定义名称覆盖前定义名称的语义。
            dict_compatibility[str_export_name] = obj_export_value  # 当前公共名称绑定

    # 返回完整兼容表，由协调器在定义自身入口前一次性恢复。
    return dict_compatibility

# 在定义协调器逻辑前恢复拆分模块的全部公共 helper 与常量。
DICT_EXPORT_COMPATIBILITY = collect_export_compatibility()  # 原入口公共兼容名称表

# 将受控兼容表合入当前模块，旧调用方仍可沿用原 import 路径。
globals().update(DICT_EXPORT_COMPATIBILITY)

# 使用模板 DOCX 生成严格交底书 DOCX，并把公式与附图真正嵌入主稿。
def export_with_template_docx(
    dict_paths: dict[str, Path | None],
    obj_runtime_module: Any,
) -> dict[str, Any]:
    """使用模板 DOCX 生成严格交底书 DOCX。

    参数：
    - `dict_paths`：已经解析完成的输入、输出和模板路径集合。
    - `obj_runtime_module`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：包含导出模式和内部说明行的结果字典。

    异常：
    - 模板缺失、Markdown 读取、图片渲染或 DOCX 写入失败时由底层异常继续上抛。
    """

    # 模板导出依赖 python-docx 打开模板并写入真实嵌图对象。
    from docx import Document

    # 读取模板路径，调用方已经在主流程中确认其存在。
    path_template = dict_paths["path_template"]  # 模板 DOCX 路径

    # 模板路径缺失时立即阻断，避免静默退回空白 DOCX 破坏交底书合同。
    if path_template is None or not path_template.exists():

        # 抛出明确错误，让上游知道严格模板导出缺少模板资产。
        raise FileNotFoundError("> ERR: [Python] 缺少专利技术交底书 DOCX 模板。")

    # 读取 Markdown 全文，准备拆分成模板章节块和内部说明内容。
    str_markdown = dict_paths["path_input"].read_text(encoding="utf-8")  # 输入 Markdown 全文

    # 解析模板章节块和内部说明，确保主稿只保留可提交代理的正式正文。
    dict_template_payload = collect_template_section_blocks(str_markdown)  # 模板导出结构化块载荷

    # 收集当前案件可嵌入 DOCX 的正式 PNG 附图路径列表。
    list_figure_paths = collect_delivery_figure_image_paths(dict_paths.get("path_case_dir"))  # 当前案件正式 PNG 附图路径列表

    # 确保目标导出目录存在，避免 DOCX 保存阶段因目录缺失失败。
    obj_runtime_module.ensure_dir(dict_paths["path_output"].parent)

    # 打开模板文档对象，后续在保留信息表和版式的前提下重建正文主体。
    obj_document = Document(str(path_template))  # 基于模板打开的 Word 文档对象

    # 加载独立槽位渲染器，保留模板标题节点、分节和正文段落样式而非重建 Heading。
    obj_template_renderer = load_template_renderer_module()  # 模板槽位渲染器模块对象

    # 加载纯 Python Office 公式转换器，任何失败都会硬阻断当前交付。
    obj_office_math = load_office_math_module()  # Office 原生公式转换模块对象

    # Office 模式按转换顺序收集预改写和 OMML 结构证据，MathType 模式保持为空。
    list_conversion_evidence: list[dict[str, object]] = []  # 当前文档的 Office 公式转换证据

    # 包装带证据转换入口，同时保持模板渲染器需要的单节点回调形态。
    def convert_formula_with_evidence(str_latex: str, bool_display: bool, str_mode: str) -> Any:
        """转换单条公式并登记对象级证据。

        参数：
        - `str_latex`：当前公式的原始 LaTeX 文本。
        - `bool_display`：当前公式是否采用行间布局。
        - `str_mode`：本轮公式对象模式。

        返回：
        - `Any`：可由 python-docx 追加的 OMML 节点。

        异常：
        - `ValueError`：预改写、转换或 OMML 结构门失败。
        """

        # 调用正式带证据入口，确保记录与实际插入文档的节点来自同一次转换。
        obj_formula, dict_formula_evidence = obj_office_math.convert_latex_to_omml_with_evidence(  # 当前公式节点与转换证据
            str_latex,  # 当前公式原始 LaTeX
            bool_display,  # 当前公式行内或行间布局
            str_mode,  # 当前 Office 或 MathType 中间模式
        )

        # 按文档转换顺序登记证据，后续与公式源记录逐项对账。
        list_conversion_evidence.append(dict_formula_evidence)

        # 返回模板渲染器需要追加的原生数学节点。
        return obj_formula

    # 按原模板标题节点替换正文、OMML 公式和附图，保留原有分节与正文样式。
    list_formula_records = obj_template_renderer.replace_template_slots(  # MathType 原位替换所需公式清单
        obj_document,  # 当前模板文档对象
        TEMPLATE_SECTION_ORDER,  # 正式模板槽位顺序
        dict_template_payload["sections"],  # 待写入的章节内容
        list_figure_paths,  # 本轮正式附图路径
        convert_formula_with_evidence,  # 带对象证据的 OMML 转换回调
        obj_office_math.split_inline_equations,  # 行内公式拆分回调
        str(dict_paths["equation_mode"]),  # 本轮公式对象模式
    )  # 与 Word OMath 顺序一致的公式源记录

    # 把当前模板文档保存到目标输出路径，形成正式交付 DOCX。
    obj_document.save(str(dict_paths["path_output"]))

    # MathType 模式通过 Word COM 把中间 OMML 原位替换为 Equation.DSMT4 OLE。
    if str(dict_paths["equation_mode"]) == "mathtype":

        # 加载专用写入器并由 MathType 自身把 MathML 转为 OLE 内部 MTEF。
        obj_mathtype_ole = load_mathtype_ole_module()  # 原生 MathType OLE 写入模块

        # 原位替换全部中间公式，任何 COM 失败都硬阻断当前导出。
        obj_mathtype_ole.replace_omml_with_mathtype(
            dict_paths["path_output"],  # 已保存的中间 DOCX 路径
            list_formula_records,  # 按文档顺序记录的公式源文本
        )

        # Word 会折叠与样式等价的直接排版属性，需在最终交付前按合同恢复。
        obj_template_validator = load_template_validator_module()  # MathType 后处理使用的模板验证器

        # 使用正式渲染与验证模块共同恢复最终交付件的显式样式。
        restore_mathtype_docx_explicit_layout(
            dict_paths["path_output"],
            obj_template_renderer,
            obj_template_validator,
        )

        # python-docx 后处理必须继续保留全部原生 MathType OLE，禁止只信转换前校验。
        obj_mathtype_ole.validate_native_mathtype_docx(
            dict_paths["path_output"],
            len(list_formula_records),
        )

    # 同内容附图会被 python-docx 合并为一个媒体部件，因此按真实字节内容去重估算媒体下限。
    set_unique_figure_contents = {
        path_figure.read_bytes()  # 以真实媒体字节作为去重键
        for path_figure in list_figure_paths  # 遍历本次准备嵌入的正式附图
        if path_figure.exists()  # 忽略已被上游移除的失效路径
    }  # 当前正式附图的去重字节内容集合

    # OMML 不占用媒体部件，严格媒体下限只统计按内容去重的正式附图。
    int_expected_media_count = len(set_unique_figure_contents)  # 严格模板校验的最小附图媒体数量

    # 对最终 DOCX 执行严格模板校验，并要求媒体数量满足公式和附图嵌入预期。
    validate_template_docx_output(
        dict_paths["path_output"],
        int_expected_media_count=int_expected_media_count,
    )

    # 从最终 DOCX 包读取对象统计，并与源公式和转换证据逐项对账。
    dict_formula_object_evidence = collect_formula_object_evidence(  # 当前交付文档的公式对象验收载荷
        dict_paths["path_output"],  # 已通过最终模板校验的 DOCX
        str(dict_paths["equation_mode"]),  # 当前公式对象模式
        list_formula_records,  # 文档顺序源公式清单
        list_conversion_evidence,  # Office 模式预改写与结构证据
    )

    # 绑定最终保存文件的内容哈希，防止结构统计证据被复用于另一份 DOCX。
    dict_formula_object_evidence["docx_sha256"] = hashlib.sha256(  # 最终 DOCX 内容哈希
        dict_paths["path_output"].read_bytes()  # 已通过最终校验的 DOCX 字节
    ).hexdigest()

    # 公式证据固定落在导出目录，供后续视觉审查和交付门读取。
    path_formula_evidence = dict_paths["path_output"].parent / FORMULA_EVIDENCE_FILENAME  # 最终公式对象证据路径

    # 使用共享运行时 JSON 写入器保持 UTF-8 和格式合同一致。
    obj_runtime_module.write_json_file(path_formula_evidence, dict_formula_object_evidence)

    # 返回导出结果，供上游登记导出模式和可选内部说明。
    return {
        "mode": "template-docx",
        "internal_lines": dict_template_payload["internal_lines"],
        "formula_evidence": str(path_formula_evidence),
    }

# 解析输入、输出和模板路径，统一处理按案件目录自动定位正文草稿的逻辑。
def resolve_paths(
    namespace_arguments: argparse.Namespace,
    obj_runtime_module: Any,
) -> dict[str, Path | None]:
    """解析输入、输出和模板路径。

    参数：
    - `namespace_arguments`：命令行解析后的参数对象。
    - `obj_runtime_module`：共享运行时支持模块对象。

    返回：
    - `dict[str, Path | None]`：输入 Markdown、输出 DOCX 和可选模板路径的封装字典。

    异常：
    - 缺少输入来源时抛出 `ValueError`。
    - 自动定位后的输入草稿缺失时抛出 `FileNotFoundError`。
    """

    # 在调用方显式给出案件目录时解析其绝对路径，否则保留空值。
    path_case_dir = Path(namespace_arguments.case_dir).resolve() if namespace_arguments.case_dir else None  # 案件目录绝对路径

    # 在调用方显式给出输入草稿时解析其绝对路径，否则保留空值供自动定位逻辑处理。
    path_input = Path(namespace_arguments.input).resolve() if namespace_arguments.input else None  # 输入 Markdown 绝对路径

    # 在调用方显式给出模板路径时解析其绝对路径，否则保留空值。
    path_template = Path(namespace_arguments.template).resolve() if namespace_arguments.template else None  # 模板 DOCX 绝对路径

    # 在既未提供输入文件也未提供案件目录时直接报错，避免自动定位无从开始。
    if path_input is None and path_case_dir is None:

        # 抛出明确参数错误，要求调用方至少提供一种正文来源。
        raise ValueError("> ERR: [Python] 请提供 --input 或 --case-dir。")

    # 在未显式提供输入草稿时按案件目录自动定位当前可用正文文件。
    if path_input is None:

        # 通过共享运行时支持模块查找当前案件下最合适的正文草稿。
        path_input = obj_runtime_module.find_disclosure_draft(path_case_dir)  # 自动定位到的正文草稿路径

    # 在最终仍无法获得有效正文草稿时立即报错。
    if path_input is None or not path_input.exists():

        # 抛出明确文件缺失错误，避免后续导出路径对空输入继续工作。
        raise FileNotFoundError("> ERR: [Python] 缺少 disclosure draft markdown。")

    # 在调用方显式给出输出路径时直接解析并使用该绝对路径。
    if namespace_arguments.output:

        # 解析调用方显式指定的 DOCX 输出路径，作为本次最终交付位置。
        path_output = Path(namespace_arguments.output).resolve()  # 显式指定的 DOCX 输出路径

    # 在未显式给出输出路径时按案件导出目录和时间戳自动构造文件名。
    else:

        # 在案件目录尚未明确时从输入 Markdown 的目录结构反推案件根目录。
        if path_case_dir is None:

            # 根据正式案件目录布局从输入文件位置回推出案件根目录。
            path_case_dir = path_input.parent.parent  # 由输入文件位置反推出的案件根目录

        # 确保案件导出目录存在，后续 DOCX 会稳定落到这里。
        path_export_dir = obj_runtime_module.ensure_dir(path_case_dir / "05_exports")  # 当前案件导出目录

        # 基于输入草稿名和当前时间戳自动构造 DOCX 文件名。
        str_output_name = (  # 自动生成的 DOCX 文件名
            f"{obj_runtime_module.sanitize_name(path_input.stem)}_"  # 清理后的草稿名称前缀
            f"{obj_runtime_module.now_timestamp()}.docx"  # 避免覆盖历史导出的时间戳后缀
        )

        # 拼出最终 DOCX 输出路径，保持正式导出目录结构一致。
        path_output = path_export_dir / str_output_name  # 自动构造的 DOCX 输出路径

    # 用字典封装解析结果，减少主流程中的多值拆包复杂度。
    dict_paths = {  # 当前导出流程使用的受控路径集合
        "path_case_dir": path_case_dir,  # 当前案件根目录
        "path_input": path_input,  # 当前要导出的 Markdown 主稿路径
        "path_output": path_output,  # 当前 DOCX 主交付件输出路径
        "path_template": path_template,  # 当前导出流程使用的模板路径
        "equation_mode": namespace_arguments.equation_mode,  # Office OMML 或原生 MathType OLE 模式
    }

    # 将已经解析完成的路径字典交回主流程继续导出。
    return dict_paths

# 生成导出说明 Markdown，记录源文件、导出模式和模板来源，便于回看导出上下文。
def render_export_note(
    path_input: Path,
    str_mode: str,
    path_template: Path | None,
) -> str:
    """渲染导出说明 Markdown 文本。

    参数：
    - `path_input`：输入 Markdown 路径。
    - `str_mode`：实际采用的导出模式标识。
    - `path_template`：可选模板 DOCX 路径。

    返回：
    - `str`：导出说明 Markdown 文本。

    异常：
    - 无。
    """

    # 在存在模板路径时提取模板文件名，否则回退到 `none`。
    str_template_name = path_template.name if path_template else "none"  # 导出说明中展示的模板名称

    # 先准备导出说明文本行列表，后续按固定顺序逐条登记说明内容。
    list_export_note_lines = [TEXT_EXPORT_NOTE_TITLE]  # 导出说明 Markdown 行列表

    # 为标题与正文条目之间补一个空行，保持 sidecar 可读性。
    list_export_note_lines.append("")

    # 登记本次导出的 Markdown 来源文件名，方便后续回看输入材料。
    list_export_note_lines.append(f"- source markdown: `{path_input.name}`")

    # 登记本次实际采用的导出模式，便于判断是否走了标准库回退。
    list_export_note_lines.append(f"- export mode: `{str_mode}`")

    # 登记本次使用的模板名称，便于追溯页面版式来源。
    list_export_note_lines.append(f"- template: `{str_template_name}`")

    # 在说明末尾补一个空行，保持 sidecar 文本结尾结构稳定。
    list_export_note_lines.append("")

    # 拼接导出说明 Markdown 文本，供 sidecar 文件直接写入。
    return "\n".join(list_export_note_lines)

# 生成提交说明 sidecar，承接行政空白和不进入主 DOCX 的内部审查内容。
def render_submission_note(
    path_input: Path,
    path_template: Path | None,
    list_internal_lines: list[str],
) -> str:
    """渲染提交说明 Markdown 文本。

    参数：
    - `path_input`：输入 Markdown 路径。
    - `path_template`：可选模板 DOCX 路径。
    - `list_internal_lines`：从主 DOCX 移出的内部审查说明行。

    返回：
    - `str`：提交说明 Markdown 文本。

    异常：
    - 无。
    """

    # 提交说明只展示文件名，避免把本地绝对路径写入 sidecar。
    str_template_name = path_template.name if path_template else "none"  # 提交说明中的模板名称

    # 先准备提交说明基础信息，避免内部材料混进最终 DOCX 主体。
    list_submission_lines = [  # 提交说明基础段落
        TEXT_SUBMISSION_NOTE_TITLE,  # 固定 sidecar 标题
        "",  # 标题后的 Markdown 空行
        f"- source markdown: `{path_input.name}`",  # 仅记录输入文件名
        f"- template: `{str_template_name}`",  # 仅记录模板文件名
        "",  # 基础信息与行政清单分隔
        "## 行政信息待确认",  # 行政空白集中列示
    ]

    # 逐项列出模板行政字段，避免空白信息在交付说明中不可见。
    for str_label in ADMIN_LABELS:

        # 写入当前待确认字段名，供人工按模板信息表逐项核对。
        list_submission_lines.append(f"- {str_label}")

    # 内部审查章节从主 DOCX 移出后在 sidecar 中保留可追溯文本。
    list_submission_lines.extend(["", "## 内部审查材料"])

    # 没有内部审查材料时给出明确说明，保持 sidecar 结构稳定。
    if not list_internal_lines:

        # 写入无内部材料的说明，避免空章节让读者误判写出失败。
        list_submission_lines.append("- 无")

    # 有内部审查材料时逐行展开，保留原先的标题和正文顺序。
    else:

        # 逐行写入内部材料，供后续审查或补充证据时回看。
        list_submission_lines.extend(list_internal_lines)

    # 末尾补空行，保证 Markdown 文件以换行结束。
    list_submission_lines.append("")

    # 拼接提交说明 Markdown 文本，交给统一文件写入器落盘。
    return "\n".join(list_submission_lines)

# 执行 DOCX 导出入口，按环境能力在 python-docx 与标准库回退之间选择后端。
def main() -> int:
    """执行 DOCX 导出入口。

    参数：
    - 无。

    返回：
    - `int`：导出成功时返回 `0`。

    异常：
    - 参数无效、输入草稿缺失或导出写入失败时由底层异常继续上抛。
    """

    # 加载共享运行时支持模块，复用统一路径、时间和正文草稿查找工具。
    obj_runtime_module = load_runtime_support_module()  # 共享运行时支持模块对象

    # 解析命令行参数，读取案件目录、输入、输出和模板配置。
    namespace_arguments = build_parser().parse_args()  # 导出入口命令行参数对象

    # 把命令行参数收束成统一路径字典，避免主流程手工分支拼路径。
    dict_paths = resolve_paths(namespace_arguments, obj_runtime_module)  # 主流程共享的输入输出路径字典

    # 在当前解释器缺少模板导出能力时，优先切到 Codex 文档运行时继续执行当前脚本。
    int_reexec_return_code = maybe_reexec_with_bundled_template_runtime(dict_paths["path_template"])  # 模板运行时重启退出码

    # 发生受控重启时直接复用子进程退出码，保持当前 CLI 契约不变。
    if int_reexec_return_code is not None:

        # 返回文档运行时子进程的退出码，避免当前进程继续重复执行导出逻辑。
        return int_reexec_return_code

    # 在模板文件存在时优先走严格模板导出，保留信息表和交底书章节合同。
    if dict_paths["path_template"] is not None and dict_paths["path_template"].exists():

        # 严格模板导出必须依赖可用的 python-docx；缺失时直接报出明确环境能力错误。
        if not is_python_docx_available():

            # 抛出清晰错误，阻止模板导出悄悄退化成不满足代理交付合同的回退模式。
            raise RuntimeError(
                "> ERR: [Python] 当前解释器缺少可用的 python-docx，且未找到可复用的 Codex 文档运行时。"
            )

        # 执行严格模板导出，把正式正文、附图和公式嵌入最终交底书主稿。
        export_with_template_docx(dict_paths, obj_runtime_module)

    # 在没有模板资产且 python-docx 可用时走增强导出路径，作为兼容回退。
    elif is_python_docx_available():

        # 执行 python-docx 增强导出，兼容没有严格模板资产的本地导出场景。
        export_with_python_docx(dict_paths, obj_runtime_module)

    # 在 python-docx 缺失时回退到标准库最小 DOCX 导出路径。
    else:

        # 执行标准库回退导出，保留最低可用 DOCX 写出能力。
        export_with_stdlib_docx(dict_paths, obj_runtime_module)

    # 把 DOCX 输出绝对路径作为机器可消费的单行结果写回上游流程。
    sys.stdout.write(str(dict_paths["path_output"].resolve()) + "\n")

    # 用零退出码告知调用方当前导出流程已经成功完成。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
