from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Strategy:
    name: str
    version: str
    exchange: str
    market_type: str
    quote_asset: str
    symbols: List[str]
    timeframe: str
    indicators: Dict[str, Any]
    entry_rules: Dict[str, Any]
    exit_rules: Dict[str, Any]
    risk: Dict[str, Any]
    signal_scoring: Dict[str, Any]