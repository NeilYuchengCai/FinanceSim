"""
FinanceSim 数据来源（Data Provenance）统一定义

系统此前对"数据从哪来"的标注非常混乱：既有小写的 ``"simulated"``（Asset 默认值、
snapshot_service 写入的 ``"snapshot"``），也有大写的 ``"SIMULATED"``（bond/commodity/fx
引擎、routers 里到处硬编码）。本模块把取值收敛为一个受控枚举，并提供
``normalize_data_source`` 把历史遗留字符串映射到规范值，保证新增写入与既有读取兼容。

注意：数据库列仍是 ``String(20)``（未加枚举约束），所以旧值会继续存在于库中，
本模块只负责"写入时用规范值、读取时归一化"，不迁移存量数据。
"""
from enum import Enum


class DataSource(str, Enum):
    """数据来源类型。

    取值同时是字符串（``str`` 混入），可直接写入 DB 列或塞进 JSON。
    """

    LIVE = "LIVE"                # 实时外部行情/数据
    CACHED = "CACHED"            # 缓存/快照（含历史遗留的 "snapshot"）
    HISTORICAL = "HISTORICAL"    # 历史回放数据
    SIMULATED = "SIMULATED"      # 本平台合成的仿真数据
    FALLBACK = "FALLBACK"        # 外部源不可用、回退到合成/缓存

    def __str__(self) -> str:  # 便于直接 f-string / 拼接
        return self.value


# 历史遗留字符串 -> 规范枚举值的映射。键统一用大写比较。
_LEGACY_MAP = {
    "SNAPSHOT": DataSource.CACHED,  # 旧 snapshot_service 写入的 "snapshot" 归到 CACHED
}


def normalize_data_source(value) -> str:
    """把任意遗留/手写的数据来源字符串归一化为规范枚举字符串。

    规则：
    - ``None`` 或空 -> ``SIMULATED``（与 Asset 表默认值一致）
    - 与任一枚举 ``value`` 大小写不敏感匹配 -> 该枚举值
    - 已知遗留别名（如 ``snapshot``）-> 对应枚举值
    - 其它未知值 -> 回退 ``SIMULATED``，并打印一次告警由调用方决定是否接受

    返回的是 ``str``（枚举的 value），便于直接落库。
    """
    if value is None:
        return DataSource.SIMULATED.value
    s = str(value).strip().upper()
    if not s:
        return DataSource.SIMULATED.value
    for ds in DataSource:
        if ds.value == s:
            return ds.value
    mapped = _LEGACY_MAP.get(s)
    if mapped is not None:
        return mapped.value
    # 未知来源：保持可运行，回退到 SIMULATED 并记录。
    import logging
    logging.getLogger(__name__).warning(
        "Unknown data_source %r, normalizing to %s", value, DataSource.SIMULATED.value
    )
    return DataSource.SIMULATED.value
