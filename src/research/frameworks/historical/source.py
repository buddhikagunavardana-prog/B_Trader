from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Protocol

import pandas as pd

from src.research.frameworks.historical.exceptions import SourceMismatchError


def frame_fingerprint(frame: pd.DataFrame) -> str:
    hashed = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    columns = "|".join(map(str, frame.columns)).encode()
    return hashlib.sha256(hashed + columns).hexdigest()


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class HistoricalSource(Protocol):
    def row_count(self) -> int: ...
    def read_rows(self, start: int, end: int) -> pd.DataFrame: ...
    def fingerprint(self) -> str: ...
    def schema(self) -> tuple[str, ...]: ...
    def validate(self) -> None: ...
    def index(self) -> pd.Index: ...
    def descriptor(self) -> Mapping[str, Any]: ...


def _validate_bounds(start: int, end: int, row_count: int) -> None:
    if start < 0 or end < start or end > row_count:
        raise IndexError(f"invalid bounded read [{start}, {end}) for {row_count} rows")


class InMemoryDataFrameSource:
    def __init__(self, frame: pd.DataFrame):
        self._frame = frame

    def row_count(self) -> int:
        return len(self._frame)

    def read_rows(self, start: int, end: int) -> pd.DataFrame:
        _validate_bounds(start, end, self.row_count())
        return self._frame.iloc[start:end].copy(deep=True)

    def fingerprint(self) -> str:
        return frame_fingerprint(self._frame)

    def schema(self) -> tuple[str, ...]:
        return tuple(map(str, self._frame.columns))

    def index(self) -> pd.Index:
        return self._frame.index

    def descriptor(self) -> Mapping[str, Any]:
        return {
            "source_type": "dataframe",
            "location": "memory",
            "row_count": self.row_count(),
            "schema": self.schema(),
            "index_name": self._frame.index.name,
            "fingerprint": self.fingerprint(),
        }

    def validate(self) -> None:
        if not self._frame.index.is_monotonic_increasing:
            raise SourceMismatchError("source index must be monotonic")
        if self._frame.index.has_duplicates:
            raise SourceMismatchError("source index contains duplicate timestamps")


class LocalCsvSource:
    """A local CSV source that keeps only its timestamp index in memory.

    Data reads use ``skiprows`` and ``nrows`` so a chunk never materializes the
    complete market-data file. The index is retained as planning metadata.
    """

    def __init__(self, path: str | Path, index_column: str = "timestamp"):
        self.path = Path(path)
        self.index_column = index_column
        self._index_cache: pd.Index | None = None
        self._schema_cache: tuple[str, ...] | None = None
        self._fingerprint_cache: tuple[int, int, str] | None = None
        if not self.path.is_file():
            raise FileNotFoundError(self.path)

    def index(self) -> pd.Index:
        if self._index_cache is None:
            values = pd.read_csv(
                self.path,
                usecols=[self.index_column],
                parse_dates=[self.index_column],
            )[self.index_column]
            self._index_cache = pd.DatetimeIndex(values, name=self.index_column)
        return self._index_cache

    def row_count(self) -> int:
        return len(self.index())

    def read_rows(self, start: int, end: int) -> pd.DataFrame:
        _validate_bounds(start, end, self.row_count())
        frame = pd.read_csv(
            self.path,
            skiprows=range(1, start + 1),
            nrows=end - start,
            parse_dates=[self.index_column],
        )
        return frame.set_index(self.index_column)

    def fingerprint(self) -> str:
        stat = self.path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
        if self._fingerprint_cache is None or self._fingerprint_cache[:2] != signature:
            self._fingerprint_cache = (*signature, _file_fingerprint(self.path))
        return self._fingerprint_cache[2]

    def schema(self) -> tuple[str, ...]:
        if self._schema_cache is None:
            columns = pd.read_csv(self.path, nrows=0).columns
            self._schema_cache = tuple(str(column) for column in columns if column != self.index_column)
        return self._schema_cache

    def descriptor(self) -> Mapping[str, Any]:
        return {
            "source_type": "csv",
            "location": str(self.path.resolve()),
            "row_count": self.row_count(),
            "schema": self.schema(),
            "index_name": self.index_column,
            "fingerprint": self.fingerprint(),
        }

    def validate(self) -> None:
        index = self.index()
        if not index.is_monotonic_increasing:
            raise SourceMismatchError("source index must be monotonic")
        if index.has_duplicates:
            raise SourceMismatchError("source index contains duplicate timestamps")


class LocalParquetSource:
    """Optional Parquet source; requires a pandas Parquet engine at runtime."""

    def __init__(self, path: str | Path, index_column: str = "timestamp"):
        self.path = Path(path)
        self.index_column = index_column
        self._frame: pd.DataFrame | None = None
        if not self.path.is_file():
            raise FileNotFoundError(self.path)

    def _load(self) -> pd.DataFrame:
        if self._frame is None:
            frame = pd.read_parquet(self.path)
            if self.index_column in frame.columns:
                frame = frame.set_index(self.index_column)
            self._frame = frame
        return self._frame

    def row_count(self) -> int:
        return len(self._load())

    def read_rows(self, start: int, end: int) -> pd.DataFrame:
        _validate_bounds(start, end, self.row_count())
        return self._load().iloc[start:end].copy(deep=True)

    def fingerprint(self) -> str:
        return _file_fingerprint(self.path)

    def schema(self) -> tuple[str, ...]:
        return tuple(map(str, self._load().columns))

    def index(self) -> pd.Index:
        return self._load().index

    def descriptor(self) -> Mapping[str, Any]:
        return {
            "source_type": "parquet",
            "location": str(self.path.resolve()),
            "row_count": self.row_count(),
            "schema": self.schema(),
            "index_name": self._load().index.name,
            "fingerprint": self.fingerprint(),
        }

    def validate(self) -> None:
        InMemoryDataFrameSource(self._load()).validate()


def source_bundle(frames: Mapping[str, pd.DataFrame]):
    return {role: InMemoryDataFrameSource(frame) for role, frame in frames.items()}
