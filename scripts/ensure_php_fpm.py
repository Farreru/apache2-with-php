#!/usr/bin/env python3
"""Start PHP-FPM instances for every configured PHP version."""

from __future__ import annotations

import getpass
import grp
import os
import subprocess
from pathlib import Path
import getpass

from config_utils import ROOT, ensure_directory, parse_config

TMP_DIR = ROOT / "tmp" / "phpfpm"
LOG_DIR = ROOT / "logs"
USER = getpass.getuser()
GROUP = grp.getgrgid(os.getgid()).gr_name


def default_fpm_listen(version: str) -> str:
    digits = "".join(ch for ch in version if ch.isdigit())
    port = 9000 + int(digits) if digits else 9000
    return f"127.0.0.1:{port}"


def default_fpm_bin(version: str) -> Path:
    numeric = "".join(ch for ch in version if ch.isdigit())
    suffix = numeric or ""
    return Path("/opt/local/sbin") / f"php-fpm{suffix}"


def ensure_php_fpm(version: str, info: dict[str, object], server_conf: dict[str, object]) -> None:
    fpm_bin = Path(info.get("fpm_bin") or default_fpm_bin(version))
    if not fpm_bin.exists():
        raise FileNotFoundError(f"php-fpm binary not found at {fpm_bin} for {version}")
    fpm_listen = info.get("fpm_listen") or default_fpm_listen(version)
    pid_file = ROOT / "tmp" / f"php-fpm-{version}.pid"
    conf_file = TMP_DIR / f"php-fpm-{version}.conf"
    log_file = LOG_DIR / f"php-fpm-{version}.log"

    ensure_directory(TMP_DIR)
    ensure_directory(LOG_DIR)

    pool_lines = [
        "[global]",
        f"pid = {pid_file}",
        f"error_log = {log_file}",
        "",
        "[php-fpm]",
        f"listen = {fpm_listen}",
        f"listen.owner = {USER}",
        f"listen.group = {GROUP}",
        "listen.mode = 0600",
    ]
    if os.geteuid() == 0:
        pool_lines += [
            f"user = {USER}",
            f"group = {GROUP}",
        ]
    pool_lines += [
        "pm = dynamic",
        "pm.max_children = 5",
        "pm.start_servers = 2",
        "pm.min_spare_servers = 1",
        "pm.max_spare_servers = 3",
        "clear_env = no",
    ]
    config = "\n".join(pool_lines) + "\n"
    conf_file.write_text(config)

    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            pid = None
        if pid:
            try:
                os.kill(pid, 0)
                return
            except OSError:
                pid_file.unlink()

    subprocess.run([str(fpm_bin), "-y", str(conf_file), "-D"], check=True)


def main() -> None:
    cfg = parse_config()
    php_versions = cfg.get("php", {}).get("versions", {}) or {}
    for version, info in php_versions.items():
        ensure_php_fpm(version, info, cfg.get("server", {}) or {})


if __name__ == "__main__":
    main()
