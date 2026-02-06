#!/usr/bin/env python3
"""Create missing certificates for every configured vhost."""

from __future__ import annotations

import subprocess
from pathlib import Path

from config_utils import ROOT, ensure_directory, parse_config


def ensure_certificate(
    name: str,
    suffix: str,
    ssl_dir: Path,
    mkcert_bin: Path | None,
    use_mkcert: bool,
) -> None:
    cert = ssl_dir / f"{name}.crt"
    key = ssl_dir / f"{name}.key"
    if cert.exists() and key.exists():
        return
    ensure_directory(ssl_dir)
    if use_mkcert and mkcert_bin and mkcert_bin.exists():
        subprocess.run(
            [
                str(mkcert_bin),
                "-cert-file",
                str(cert),
                "-key-file",
                str(key),
                f"{name}.{suffix}",
            ],
            check=True,
        )
        print(f"Generated mkcert certificate for {name}.{suffix}")
        return

    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-subj",
            f"/CN={name}.{suffix}",
            "-days",
            "365",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
    )
    print(f"Generated self-signed certificate for {name}.{suffix}")


def main() -> None:
    config = parse_config()
    server = config.get("server", {}) or {}
    suffix = server.get("domain_suffix", "test")
    ssl_dir = ROOT / server.get("ssl_dir", "ssl")
    hosts: dict[str, dict[str, object]] = config.get("hosts", {}) or {}
    mkcert_bin = Path(server.get("mkcert_bin", "/opt/local/bin/mkcert"))
    use_mkcert = bool(server.get("use_mkcert", False))

    for host in hosts:
        ensure_certificate(host, suffix, ssl_dir, mkcert_bin if mkcert_bin else None, use_mkcert)


if __name__ == "__main__":
    main()
