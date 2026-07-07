"""
B Trader Strategy Schema

Supports multiple strategy formats.

Schema Versions

v1
Current strategy.json

v2
Rule Based Strategy Engine

Future:
v3
AI Generated Strategies
"""


SUPPORTED_SCHEMAS = [
    "1.0",
    "2.0",
]


DEFAULT_SCHEMA = "1.0"


def is_supported(schema: str) -> bool:
    return schema in SUPPORTED_SCHEMAS