"""Tick and k-bar cache loading for deterministic replay."""

from __future__ import annotations

import csv
import datetime
import gzip
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Iterable, Iterator, List, Optional

logger = logging.getLogger(__name__)

TAIWAN_TZ = datetime.timezone(datetime.timedelta(hours=8))
DEFAULT_CACHE_DIR = Path.cwd() / "tick_cache"

TICK_CSV_FIELDS = [
    "datetime",
    "close",
    "volume",
    "bid_price",
    "ask_price",
    "tick_type",
]

_KBARS_CSV_FIELDS = ["ts", "Open", "High", "Low", "Close", "Volume"]


@dataclass
class ReplayTick:
    """Minimal replay unit compatible with ``TradingEngine.on_tick``."""

    datetime: datetime.datetime
    close: str
    volume: int
    tick_type: int
    bid_price: float = 0.0
    ask_price: float = 0.0


@dataclass
class KBarRecord:
    ts: datetime.datetime
    Open: float
    High: float
    Low: float
    Close: float
    Volume: int


def cache_path(cache_dir: Path, code: str, date: datetime.date) -> Path:
    return Path(cache_dir) / f"{code}_{date.isoformat()}.csv"


def cache_gz_path(cache_dir: Path, code: str, date: datetime.date) -> Path:
    return Path(cache_dir) / f"{code}_{date.isoformat()}.csv.gz"


def resolve_tick_cache_path(
    cache_dir: Path, code: str, date: datetime.date
) -> Optional[Path]:
    gz = cache_gz_path(cache_dir, code, date)
    plain = cache_path(cache_dir, code, date)
    if gz.is_file():
        return gz
    if plain.is_file():
        return plain
    return None


def _open_tick_csv_reader(path: Path) -> IO[str]:
    path = Path(path)
    if path.suffix == ".gz" or path.name.endswith(".csv.gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def load_ticks_csv(path: Path) -> List[ReplayTick]:
    ticks: List[ReplayTick] = []
    with _open_tick_csv_reader(Path(path)) as f:
        for row in csv.DictReader(f):
            ticks.append(
                ReplayTick(
                    datetime=datetime.datetime.fromisoformat(row["datetime"]),
                    close=row["close"],
                    volume=int(row["volume"]),
                    tick_type=int(row["tick_type"]),
                    bid_price=float(row["bid_price"]),
                    ask_price=float(row["ask_price"]),
                )
            )
    return ticks


def iter_replay_ticks(
    code: str,
    dates: Iterable[datetime.date],
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Iterator[ReplayTick]:
    for date in dates:
        path = resolve_tick_cache_path(cache_dir, code, date)
        if path is None:
            logger.warning("快取缺檔，略過 %s_%s", code, date.isoformat())
            continue
        yield from load_ticks_csv(path)


def kbars_cache_path(cache_dir: Path, code: str, date: datetime.date) -> Path:
    return Path(cache_dir) / f"{code}_kbars_{date.isoformat()}.csv"


def save_kbars_csv(bars: Iterable[KBarRecord], path: Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_KBARS_CSV_FIELDS)
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "ts": bar.ts.isoformat(),
                    "Open": bar.Open,
                    "High": bar.High,
                    "Low": bar.Low,
                    "Close": bar.Close,
                    "Volume": bar.Volume,
                }
            )
            count += 1
    return count


def load_kbars_csv(path: Path) -> List[KBarRecord]:
    bars: List[KBarRecord] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            bars.append(
                KBarRecord(
                    ts=datetime.datetime.fromisoformat(row["ts"]),
                    Open=float(row["Open"]),
                    High=float(row["High"]),
                    Low=float(row["Low"]),
                    Close=float(row["Close"]),
                    Volume=int(row["Volume"]),
                )
            )
    bars.sort(key=lambda b: b.ts)
    return bars


def date_range(start: datetime.date, end: datetime.date) -> List[datetime.date]:
    days = (end - start).days
    return [start + datetime.timedelta(days=i) for i in range(days + 1)]


def iter_kbars_in_range(
    code: str,
    start: datetime.date,
    end: datetime.date,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> List[KBarRecord]:
    bars: List[KBarRecord] = []
    for date in date_range(start, end):
        path = kbars_cache_path(cache_dir, code, date)
        if not path.is_file():
            continue
        bars.extend(load_kbars_csv(path))
    bars.sort(key=lambda b: b.ts)
    return bars


__all__ = [
    "DEFAULT_CACHE_DIR",
    "KBarRecord",
    "ReplayTick",
    "iter_kbars_in_range",
    "iter_replay_ticks",
    "kbars_cache_path",
    "load_kbars_csv",
    "load_ticks_csv",
    "resolve_tick_cache_path",
    "save_kbars_csv",
]