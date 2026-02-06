#!/usr/bin/env python3
"""Print the httpd binary path the runner should launch."""

from __future__ import annotations

from pathlib import Path

from config_utils import parse_config


def resolve_httpd() -> Path:
    cfg = parse_config()
    server = cfg.get("server", {}) or {}
    if httpd := server.get("httpd_bin"):
        return Path(httpd)
    if sbin := server.get("sbin_dir"):
        return Path(sbin) / "httpd"
    prefix = Path(server.get("apache_prefix", "/opt/local"))
    return prefix / "sbin" / "httpd"


def main() -> None:
    print(resolve_httpd())


if __name__ == "__main__":
    main()
