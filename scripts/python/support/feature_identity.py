"""为 Model 4.0 和 claims map 提供共享稳定特征身份。"""

# 延迟解析类型注解，保持当前技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库负责规范序列化、摘要计算和映射类型判断。
import hashlib
import json
from collections.abc import Mapping
from typing import Any

# 根据特征来源字段计算不受列表位置影响的稳定身份。
def build_stable_feature_id(dict_feature: Mapping[str, Any]) -> str:
    """根据特征来源身份生成不受列表顺序影响的稳定编号。

    参数：
    - `dict_feature`：包含步骤、特征文本和证据编号的来源记录。

    返回：
    - `str`：以 `FT` 开头并保留完整 SHA-256 的稳定编号。

    异常：
    - 输入值无法转换为字符串时由底层对象实现上抛。
    """

    # 只选择来源身份字段，并对证据集合排序去重以消除排列差异。
    dict_identity = {  # 稳定特征身份载荷
        "step": str(dict_feature.get("step", "")).strip(),  # 特征来源步骤编号
        "text": str(dict_feature.get("feature", dict_feature.get("text", ""))).strip(),  # 特征正文
        "support_ids": sorted(  # 排序去重后的特征证据编号
            {
                str(obj_support_id).strip()  # 当前证据编号规范文本
                for obj_support_id in dict_feature.get("support_ids", dict_feature.get("evidence_ids", []))  # 遍历特征证据来源
                if str(obj_support_id).strip()  # 丢弃空证据编号
            }
        ),
    }

    # 使用排序键和紧凑分隔符固定跨运行 JSON 字节边界。
    str_canonical = json.dumps(  # 规范特征身份文本
        dict_identity,  # 已收敛的特征身份载荷
        ensure_ascii=False,  # 保留中文特征正文
        separators=(",", ":"),  # 使用紧凑 JSON 分隔符
        sort_keys=True,  # 固定身份字段顺序
    )  # 完成规范序列化调用

    # 计算大写 SHA-256，便于 schema 用固定字符集验证编号。
    str_digest = hashlib.sha256(str_canonical.encode("utf-8")).hexdigest().upper()  # 特征身份摘要

    # 完整摘要避免 48 bit 截断把碰撞风险转嫁给后置验证器。
    return f"FT{str_digest}"
