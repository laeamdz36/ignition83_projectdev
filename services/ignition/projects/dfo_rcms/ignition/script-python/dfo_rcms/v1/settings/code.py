"""Constants used throughout the RCMS project."""

__all__ = [
    "DB_HIST",
    "DB_CONFIG",
    "RCMS_TOKENS_TABLE",
    "RCMS_TOKENS_HIST_TABLE",
    "RCMS_CONFIG_TABLE"
]

DB_HIST = "mssql_dev1"
DB_CONFIG = "AD_Develop"
# sql tables definition
RCMS_TOKENS_TABLE = "rcms_tokens"
RCMS_TOKENS_HIST_TABLE = "rcms_tokens_hist"
RCMS_CONFIG_TABLE = "proxy_config"