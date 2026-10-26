import re

SLOTS = ["brand", "vehicle_model", "model_year", "powertrain", "mileage",
         "power_state", "symptom", "warning_info", "recent_events"]

UNCERTAIN = "不确定"
# power_state 只允许 3 个确定值；下面是常见同义写法（去空格/标点、转小写后整句匹配）
POWER_STATES = {
    "能READY": ["能ready", "能进入ready", "可以ready", "可以进入ready", "ready正常",
                "能正常ready", "可以正常ready", "正常ready", "ready能亮", "ready亮"],
    "不能READY": ["不能ready", "不能进入ready", "进不了ready", "无法ready", "无法进入ready",
                "上不了ready", "ready不亮", "没有ready"],
    "12V都没电": ["12v都没电", "12v没电", "全车没电"],
}

# 表示"不确定/不知道"的说法（去掉空格和标点、转小写后整句匹配）
_UNCERTAIN_WORDS = {
    "不确定", "不太确定", "不知道", "不太知道", "不清楚", "不太清楚", "未知", "不详",
    "没注意", "没注意到", "没留意", "不记得", "记不清", "忘了", "说不清", "不晓得",
    "待确认", "待定", "待核实", "unknown", "unsure", "notsure", "idk",
    "dontknow", "idontknow", "n/a", "na",
}
# 口语变体：如"我也不太清楚呢""没注意到啊"
_UNCERTAIN_RE = re.compile(r"^(我)?(也)?(不太|不|没)(确定|知道|清楚|记得|注意|注意到|留意|晓得)(了|呢|啊|哦|耶)?$")
_EMPTY_WORDS = {"null", "none", "undefined", "nil"}
_STRIP_RE = re.compile(r"[\s。，,\.！!？?~～、（）()\"'“”‘’：:；;]+")


def _clean(v):
    if v is None:
        return ""
    return str(v).strip()


def _key(v):
    return _STRIP_RE.sub("", v).lower()


def _normalize(slot, v):
    """返回 (值, 是否不确定)。空值返回 ("", False)。"""
    v = _clean(v)
    k = _key(v)
    if not k or k in _EMPTY_WORDS:
        return "", False
    if k in _UNCERTAIN_WORDS or _UNCERTAIN_RE.match(k):
        return UNCERTAIN, True
    if slot == "power_state":
        for name, aliases in POWER_STATES.items():
            if k in aliases:
                return name, False
        # 不在枚举里的 power_state 一律视为不确定（宁可再问一次）
        return UNCERTAIN, True
    return v, False


def main(is_success,
         new_brand, new_vehicle_model, new_model_year, new_powertrain, new_mileage,
         new_power_state, new_symptom, new_warning_info, new_recent_events,
         old_brand, old_vehicle_model, old_model_year, old_powertrain, old_mileage,
         old_power_state, old_symptom, old_warning_info, old_recent_events) -> dict:
    args = dict(locals())
    # 提取失败（__is_success == 0）时，不采用任何新值
    failed = _clean(is_success).lower() in ("0", "0.0", "false")
    out = {}
    for k in SLOTS:
        old, old_unsure = _normalize(k, args.get("old_" + k))
        new, new_unsure = _normalize(k, args.get("new_" + k))
        if failed or not new:
            out[k] = old                      # 新值为空/提取失败 → 保留旧值
        elif new_unsure and old and not old_unsure:
            out[k] = old                      # "不确定"不能覆盖已确定的旧值
        else:
            out[k] = new                      # 其余情况用新值（"不确定"只能填空位）
    parts = [out[k] for k in ("brand", "vehicle_model", "powertrain", "power_state",
                              "symptom", "warning_info") if out[k] and out[k] != UNCERTAIN]
    out["fault_query"] = " ".join(parts)      # 供 kr_fault 检索用（NB5）
    return out
