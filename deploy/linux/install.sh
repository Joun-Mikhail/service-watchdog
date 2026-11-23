#!/usr/bin/env bash
# Install service-watchdog as a hardened systemd service.
# Tested on Ubuntu 22.04+/Debian 12 and Amazon Linux 2023.
#
# Usage: sudo ./deploy/linux/install.sh
set -euo pipefail

APP_DIR=/opt/service-watchdog
SERVICE_USER=watchdog
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root: sudo $0"
command -v python3 >/dev/null || die "python3 is not installed"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || die "python 3.10 or newer is required"
python3 -m venv --help >/dev/null 2>&1 || die "python3 venv module missing (Debian/Ubuntu: apt install python3-venv)"

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    log "creating system user $SERVICE_USER"
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

log "installing application to $APP_DIR"
install -d -m 755 "$APP_DIR"
install -d -m 750 -o "$SERVICE_USER" -g "$SERVICE_USER" "$APP_DIR/logs" "$APP_DIR/reports"
install -m 644 "$SRC_DIR"/*.py "$SRC_DIR/requirements.txt" "$APP_DIR/"

if [[ ! -f "$APP_DIR/config.yaml" ]]; then
    install -m 644 "$SRC_DIR/config.yaml" "$APP_DIR/config.yaml"
fi
if [[ ! -f "$APP_DIR/.env" ]]; then
    install -m 600 -o "$SERVICE_USER" -g "$SERVICE_USER" "$SRC_DIR/.env.example" "$APP_DIR/.env"
    log "created $APP_DIR/.env from template - add SMTP credentials, then: systemctl restart service-watchdog"
fi

log "creating virtual environment"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

log "validating configuration"
(cd "$APP_DIR" && runuser -u "$SERVICE_USER" -- venv/bin/python -c \
    'import config; config.load_config("config.yaml")') || die "config.yaml is invalid"

log "installing systemd units"
install -m 644 "$SRC_DIR"/deploy/linux/service-watchdog*.service \
    "$SRC_DIR"/deploy/linux/service-watchdog*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now service-watchdog.service service-watchdog-report.timer

log "done"
systemctl --no-pager --lines=5 status service-watchdog.service || true
echo
echo "Follow logs:   journalctl -u service-watchdog -f"
echo "Edit targets:  $APP_DIR/config.yaml (then: systemctl restart service-watchdog)"
