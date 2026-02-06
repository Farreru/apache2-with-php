#!/usr/bin/env python3
"""Render an Apache httpd.conf from config.yml."""

from __future__ import annotations

import argparse
import getpass
import grp
import os
from pathlib import Path
from textwrap import dedent

from config_utils import CONFIG_PATH, ROOT, ensure_directory, parse_config


def render(config: dict[str, object], dest: Path) -> None:
    server: dict[str, object] = config.get("server", {})  # type: ignore
    php: dict[str, object] = config.get("php", {})  # type: ignore
    hosts: dict[str, dict[str, object]] = config.get("hosts", {})  # type: ignore

    apache_prefix = Path(server.get("apache_prefix", "/opt/local"))
    server_root = Path(server.get("server_root", str(apache_prefix)))
    modules_dir = Path(server.get("modules_dir", str(apache_prefix / "lib/apache2/modules")))
    conf_dir = Path(server.get("conf_dir", str(apache_prefix / "etc/apache2")))
    types_config = server.get("types_config", str(conf_dir / "mime.types"))
    bind_ip = server.get("bind_ip", "127.0.0.1")
    http_port = server.get("http_port", 8080)
    https_port = server.get("https_port", 8443)
    domain_suffix = server.get("domain_suffix", "test")
    server_name = server.get("server_name", "localdev")
    log_dir = ROOT / server.get("log_dir", "logs")
    ssl_dir = ROOT / server.get("ssl_dir", "ssl")
    pid_file = ROOT / server.get("pid_file", "tmp/httpd.pid")
    log_level = server.get("log_level", "info")
    server_admin = server.get("server_admin", f"webmaster@{server_name}.{domain_suffix}")

    default_php = php.get("default")
    php_versions = php.get("versions", {})
    if not default_php or default_php not in php_versions:
        raise ValueError("config.yml must declare a php.default that exists in php.versions")

    ensure_directory(log_dir)
    ensure_directory(ssl_dir)
    ensure_directory(pid_file.parent)

    base_modules = [
        ("unixd_module", "mod_unixd.so"),
        ("authz_core_module", "mod_authz_core.so"),
        ("authz_host_module", "mod_authz_host.so"),
        ("reqtimeout_module", "mod_reqtimeout.so"),
        ("log_config_module", "mod_log_config.so"),
        ("mime_module", "mod_mime.so"),
        ("dir_module", "mod_dir.so"),
        ("alias_module", "mod_alias.so"),
        ("setenvif_module", "mod_setenvif.so"),
        ("rewrite_module", "mod_rewrite.so"),
        ("access_compat_module", "mod_access_compat.so"),
        ("ssl_module", "mod_ssl.so"),
        ("socache_shmcb_module", "mod_socache_shmcb.so"),
        ("proxy_module", "mod_proxy.so"),
        ("proxy_fcgi_module", "mod_proxy_fcgi.so"),
    ]
    mpm_choice = server.get("mpm", "builtin")
    load_modules = list(base_modules)
    if mpm_choice != "builtin":
        mpm_modules = {
            "prefork": ("mpm_prefork_module", "mod_mpm_prefork.so"),
            "event": ("mpm_event_module", "mod_mpm_event.so"),
            "worker": ("mpm_worker_module", "mod_mpm_worker.so"),
        }
        if mpm_choice not in mpm_modules:
            raise ValueError(
                f"Unsupported MPM '{mpm_choice}' (valid options: builtin, {', '.join(mpm_modules)})"
            )
        module_name, module_file = mpm_modules[mpm_choice]
        module_path = modules_dir / module_file
        if not module_path.exists():
            raise FileNotFoundError(
                f"MPM module {module_file} not found under {modules_dir}; compile Apache with {mpm_choice} or adjust config."
            )
        load_modules.append((module_name, module_file))

    load_module_lines = "\n".join(
        f"LoadModule {module} {modules_dir / so}"
        for module, so in load_modules
    )
    php_module_lines = ""

    run_user = server.get("run_user")
    run_group = server.get("run_group")
    if not run_user:
        run_user = os.environ.get("SUDO_USER") or os.environ.get("USER") or getpass.getuser()
    if not run_group:
        sudo_gid = os.environ.get("SUDO_GID")
        if sudo_gid:
            try:
                run_group = grp.getgrgid(int(sudo_gid)).gr_name
            except (KeyError, ValueError):
                run_group = None
    if not run_group:
        run_group = grp.getgrgid(os.getgid()).gr_name

    host_blocks = []
    for name, info in hosts.items():
        folder = info.get("folder")
        if not folder:
            raise ValueError(f"Host {name} needs a folder")
        docroot = Path(folder)
        if not docroot.is_absolute():
            docroot = ROOT / docroot
        ensure_directory(docroot)
        php_version = info.get("php", default_php)
        version_info = php_versions.get(php_version, {})
        fpm_listen = version_info.get("fpm_listen")
        if not fpm_listen:
            raise ValueError(f"Host {name} references PHP version {php_version} with no fpm_listen address")
        host_domain = f"{name}.{domain_suffix}"
        host_log_base = log_dir / name
        ensure_directory(host_log_base)
        host_block = dedent(
            f"""
            <VirtualHost {bind_ip}:{http_port}>
                ServerName {host_domain}
                ServerAdmin {server_admin}
                DocumentRoot "{docroot}"
                ErrorLog "{log_dir / f'{name}.error.log'}"
                CustomLog "{log_dir / f'{name}.access.log'}" combined
                DirectoryIndex index.php index.html
                <Directory "{docroot}">
                    AllowOverride All
                    Require all granted
                </Directory>
                <FilesMatch "\\.php$">
                    SetHandler "proxy:fcgi://{fpm_listen}"
                </FilesMatch>
            </VirtualHost>

            <VirtualHost {bind_ip}:{https_port}>
                ServerName {host_domain}
                ServerAdmin {server_admin}
                DocumentRoot "{docroot}"
                ErrorLog "{log_dir / f'{name}-ssl.error.log'}"
                CustomLog "{log_dir / f'{name}-ssl.access.log'}" combined
                DirectoryIndex index.php index.html
                <Directory "{docroot}">
                    AllowOverride All
                    Require all granted
                </Directory>
                <FilesMatch "\\.php$">
                    SetHandler "proxy:fcgi://{fpm_listen}"
                </FilesMatch>
                SSLEngine on
                SSLCertificateFile "{ssl_dir / f'{name}.crt'}"
                SSLCertificateKeyFile "{ssl_dir / f'{name}.key'}"
            </VirtualHost>
            """
        )
        host_blocks.append(host_block)

    log_format_line = (
        "LogFormat '%h %l %u %t \"\\\"%r\\\"\" %>s %b \"\\\"%{Referer}i\\\"\" \"\\\"%{User-Agent}i\\\"\"' "
        "combined"
    )
    content = dedent(
        f"""
        ServerRoot "{server_root}"
        PidFile "{pid_file}"
        Listen {bind_ip}:{http_port}
        Listen {bind_ip}:{https_port}
        User {run_user}
        Group {run_group}
        ServerName {server_name}.{domain_suffix}:{http_port}
        LogLevel {log_level}
        {log_format_line}
        ErrorLog "{log_dir / 'error.log'}"
        CustomLog "{log_dir / 'access.log'}" combined
        TypesConfig "{types_config}"
        {load_module_lines}
        {php_module_lines}
        DocumentRoot "{ROOT / 'html'}"
        <Directory "{ROOT / 'html'}">
            AllowOverride All
            Require all granted
        </Directory>
        {''.join(host_blocks)}
        """
    )

    dest.write_text(content)
    print(f"Wrote Apache config to {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render httpd.conf from config.yml")
    parser.add_argument("--output", "-o", default=ROOT / "tmp" / "httpd.conf", type=Path)
    args = parser.parse_args()
    config = parse_config(CONFIG_PATH)
    render(config, args.output)


if __name__ == "__main__":
    main()
