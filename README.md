# Apache-with-PHP Runner

This workspace is a lightweight macOS development runner that stitches together MacPorts Apache 2 and multiple PHP versions into a single project directory. It mirrors the convenience of tools like Laragon but stays focused on PHP-based projects.

## Layout
- `config.yml`: central configuration for the server, PHP versions, and virtual hosts (see below).
- `html/`: document roots for PHP hosts (examples: `phpapp`, `phplegacy`).
- `scripts/`: helpers for generating `httpd.conf`, ensuring SSL, and managing the server lifecycle.
- `logs/`, `ssl/`, `tmp/`: generated runtime state.

## Configuration (`config.yml`)
The YAML file lets you define:
1. `server` settings (bind IP, ports, log paths, Apache directories, SSL location, and executable paths).
2. `php` definitions which map a name (e.g. `php82`) to its CLI binary, `php.ini`, the `php-fpm` binary (`fpm_bin`), and the FastCGI address it listens on (`fpm_listen`). The runner uses these values to spawn PHP-FPM instances per version and proxy PHP requests via `mod_proxy_fcgi`.
   - `ini`, `cli`, `fpm_bin`, and `fpm_listen` are required for each version you want to expose (defaults can align with `/opt/local` if you install MacPorts’ phpXX and phpXX-fpm ports).
3. `hosts`, keyed by hostname (e.g. `phpapp`), providing a folder under `html/` and which PHP version to use. Each host becomes `{name}.{domain_suffix}` for HTTP and HTTPS and forwards `.php` files to the configured PHP-FPM endpoint.

### Server fields
- `server_root`: sets Apache's `ServerRoot` (defaults to `/opt/local` for MacPorts).
- `apache_prefix`: base prefix for locating binaries; defaults to `/opt/local`.
- `modules_dir`: where `LoadModule` points; defaults to `apache_prefix/lib/apache2/modules`.
- `conf_dir`: where `mime.types` and extras live; defaults to `apache_prefix/etc/apache2`.
- `httpd_bin`: the exact binary `start.sh`/`restart.sh` will execute; if omitted the helper falls back to `sbin/httpd` under `apache_prefix`.
- `mpm`: which MPM module to load (`prefork`, `event`, `worker`, or `builtin`). Defaults to `builtin` because MacPorts’ Apache compiles its MPM directly into the binary; specify another value only if the corresponding `mod_mpm_*.so` exists under `server.modules_dir`.
- `run_user` / `run_group`: optional overrides for the `User`/`Group` lines the generator writes. When the scripts run under `sudo`, the defaults take `SUDO_USER`/`SUDO_GID` so the daemon drops to your normal account even though `httpd` launched as root.
- `mkcert_bin`/`use_mkcert`: when `use_mkcert` is true and the binary exists, `scripts/ensure_ssl.py` runs `mkcert -cert-file ... -key-file ... <host>` to produce the certificates before Apache starts; it falls back to the builtin OpenSSL generator if mkcert is unavailable.

### Example snippet
```yaml
hosts:
  phpapp:
    folder: html/phpapp
    php: php82
```
This creates `phpapp.test` and uses PHP 8.2 for `.php` files.

## Generation step
Run `scripts/generate_httpd_conf.py` (it is invoked by `start.sh`/`restart.sh`) to convert `config.yml` into a full Apache `httpd.conf` tailored to your hosts.

## Hosts
`scripts/update_hosts.py` runs from `start.sh`/`restart.sh` and records every host defined in `config.yml` (including `server.server_name`) plus every top-level folder under `html/`. It writes a dedicated block between `# apache-with-php managed hosts start`/`end` in `/etc/hosts`, so each `{host}.{domain_suffix}` resolves to `127.0.0.1`/`::1`.

If the script cannot write `/etc/hosts` directly it will fall back to re-running via `sudo tee /etc/hosts` (you may be prompted for a password when the shell is interactive). When executed from a non-interactive context such as `auto-start-at-login.sh` started from launchd, it simply prints a reminder and skips the update—rerun `sudo python3 scripts/update_hosts.py` manually for those cases.

## SSL
`scripts/ensure_ssl.sh` issues self-signed certificates into `ssl/{host}.crt`/`.key`. Certificates are regenerated only if the key is missing, and both HTTP and HTTPS VirtualHosts point at them.

## Scripts
- `scripts/start.sh`: runs `scripts/update_hosts.py`, regenerates `httpd.conf`, ensures SSL, and launches whichever `httpd` binary `config.yml` points at (`scripts/get_httpd_bin.py` resolves it). Use this in a shell or tmux as your main development server.
- `scripts/restart.sh`: re-reads config, refreshes `/etc/hosts`/SSL, and restarts the same `httpd` process via HUP/reload so `config.yml` updates take effect.
- `scripts/tmux-start.sh`: launches (or attaches to) a tmux session named `apache` (customizable via the first argument) that runs `./start.sh`; if the session is new it is created detached and then immediately attached so you stay in tmux and can respond to the sudo prompt.
- `scripts/tmux-restart.sh`: if a session exists it stops the server (`sudo ./stop.sh`), kills the tmux session, and then relaunches `tmux-start.sh` so you get a fresh tmux window running the new process.
- `scripts/tmux-stop.sh`: calls `sudo ./stop.sh` and kills the tmux session so the root-owned httpd and PHP-FPM pools exit before you start again.
- `scripts/update_hosts.py`: rewrites `/etc/hosts` between the managed markers so every `{host}.{domain_suffix}` resolves locally; it’s invoked by start/restart but can also be run with `sudo` if auto-start fails to edit the file.
- `scripts/ensure_php_fpm.py`: reads `php.versions` and launches one PHP-FPM process per configured version (respecting `fpm_bin`, `fpm_listen`, and the shared `logs/`, `tmp/` state). This runs before Apache start/restart so the proxy handler has a listening backend.
- `scripts/get_httpd_bin.py`: helper that reads the `server` section and prints the expected httpd binary path; `start.sh`/`restart.sh` consume it so you can override `server.httpd_bin`, `server.sbin_dir`, or `server.apache_prefix`.
- `scripts/stop.sh`: stops `httpd` (using `server.httpd_bin`) and kills the PHP-FPM pools (`tmp/php-fpm-*.pid`), so you can cleanly terminate everything before editing configs or rebinding privileged ports.
- `scripts/pf-enable.sh`: loads `scripts/pf-https.conf` via `pfctl -ef` so macOS redirects external HTTPS (`:443`) to the high port Apache is actually listening on; run this once with `sudo` whenever you want the runner to appear on `https://*.test` without changing `config.yml`.
- `scripts/pf-disable.sh`: restores the system PF ruleset (`/etc/pf.conf`) so the temporary redirect is removed.
- `scripts/auto-start-at-login.sh`: idempotent helper that runs `start.sh` once per login session (skips if already inside tmux/`screen`). Drop it into your shell profile or macOS login items.
- `scripts/start-service.sh`, `scripts/restart-service.sh`, `scripts/stop-service.sh`, `scripts/check-service.sh`: helpers that install, reload, stop, and report on a `launchd` daemon (`com.farreru.apache-with-php`) that runs `start.sh` automatically on macOS.

## Flow
1. Update `config.yml` with hosts and PHP mappings.
2. Run `scripts/start.sh` (or `auto-start-at-login`); it builds config + SSL and starts Apache.
3. Change PHP/hosts as needed and run `scripts/restart.sh` to reload Apache without stopping the process manually.

## Notes
- The runner assumes MacPorts Apache under `/opt/local` and PHP modules under `/opt/local/lib/apache2/modules`. Adjust `server.apache_prefix`, `server.modules_dir`, and `php.versions.*.module` if your installation landed elsewhere.
- Because PHP is now served through PHP-FPM, you need MacPorts’ `phpXX-fpm` ports (e.g., `php74-fpm`, `php82-fpm`). Each version’s `fpm_bin`/`fpm_listen` should point at the daemon and socket that port installs.
- Generated logs land in `logs/` for easy inspection and can be rotated manually.
- Add additional host folders under `html/` and reference them inside `config.yml` to expose more virtual hosts.
- If you want browsers to reach `https://*.test` on port 443, enable the pf redirect once:
  1. Run `sudo scripts/pf-enable.sh` (it loads `scripts/pf-https.conf` and redirects 443 → `server.https_port`, default 8443).
  2. Trust the generated `/ssl/{host}.crt` in your keychain so the redirect works without certificate warnings.
  3. When you’re done, run `sudo scripts/pf-disable.sh` to restore the default PF ruleset; this step is optional if you prefer the redirect to stay in place.
