#!/usr/bin/env python3
"""Ensure /etc/hosts has entries for every configured host and html folder."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable

from config_utils import ROOT, parse_config

HOSTS_PATH = Path("/etc/hosts")
MANAGED_START = "# apache-with-php managed hosts start"
MANAGED_END = "# apache-with-php managed hosts end"


def gather_domains() -> list[str]:
    cfg = parse_config()
    server = cfg.get("server", {}) or {}
    suffix = server.get("domain_suffix", "test")
    hosts: dict[str, dict[str, object]] = cfg.get("hosts", {}) or {}
    names: set[str] = set()
    if "server_name" in server and server["server_name"]:
        names.add(f"{server['server_name']}.{suffix}")
    for name in hosts:
        names.add(f"{name}.{suffix}")
    html_root = ROOT / "html"
    if html_root.exists():
        for entry in html_root.iterdir():
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                names.add(f"{entry.name}.{suffix}")
    return sorted(names)


def build_block(domains: Iterable[str]) -> str:
    lines: list[str] = [MANAGED_START]
    for domain in domains:
        lines.append(f"127.0.0.1 {domain}")
        lines.append(f"::1 {domain}")
    lines.append(MANAGED_END)
    return "\n".join(lines) + "\n"


def merge(existing: str, block: str) -> str:
    start_idx = existing.find(MANAGED_START)
    end_idx = existing.find(MANAGED_END)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        before = existing[:start_idx].rstrip()
        after = existing[end_idx + len(MANAGED_END):].lstrip()
        prefix = f"{before}\n\n" if before else ""
        suffix = f"\n\n{after}" if after else ""
        return f"{prefix}{block}{suffix}".strip() + "\n"
    base = existing.rstrip()
    if base:
        return f"{base}\n\n{block}"
    return block


def write_hosts(content: str) -> bool:
    try:
        HOSTS_PATH.write_text(content)
        return True
    except PermissionError:
        if not sys.stdin.isatty():
            print("Need root privileges to update /etc/hosts; rerun this script with sudo or run 'sudo scripts/update_hosts.py'.")
            return False
        print("Updating /etc/hosts requires elevated privileges; you may be prompted for your password.")
        try:
            subprocess.run(
                ["sudo", "tee", "/etc/hosts"],
                input=content.encode(),
                check=True,
                stdout=subprocess.DEVNULL,
            )
            return True
        except subprocess.CalledProcessError:
            print("sudo failed; /etc/hosts was not updated.")
            return False
    except OSError as exc:
        print(f"Failed to write /etc/hosts: {exc}")
        return False


def main() -> None:
    domains = gather_domains()
    if not domains:
        print("No hosts defined; skipping /etc/hosts update.")
        return
    block = build_block(domains)
    existing = HOSTS_PATH.read_text() if HOSTS_PATH.exists() else ""
    desired = merge(existing, block)
    if existing == desired:
        print("/etc/hosts already contains the required entries.")
        return
    write_hosts(desired)


if __name__ == "__main__":
    main()
