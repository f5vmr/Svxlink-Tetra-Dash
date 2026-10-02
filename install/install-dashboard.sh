#!/bin/bash
set -eu

REPO_URL="https://github.com/f5vmr/SvxLink-Dash-V4.0.git"
STREAMER_REPO_URL="https://github.com/f5vmr/Svxlink-Streamer.git"

INSTALL_DIR="/opt/dashboard"
BACKUP_ROOT="/var/backups/svxlink-dash"

SCRIPT_DIR="$(
    CDPATH= cd -- "$(dirname -- "$0")" &&
    pwd
)"
SOURCE_DIR="$(
    CDPATH= cd -- "$SCRIPT_DIR/.." &&
    pwd
)"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
STAGING_DIR="/opt/.svxlink-dashboard-v4-${TIMESTAMP}-$$"
PREVIOUS_DIR=""
EXISTING_RELEASE=""
STREAMER_SOURCE_DIR=""

echo "Installing SvxLink-Dash-V4.0..."

SOURCE_ORIGIN=""

cleanup_installer() {
    if [ -n "${STREAMER_SOURCE_DIR}" ] &&
       [ -d "${STREAMER_SOURCE_DIR}" ]; then
        rm -rf -- "${STREAMER_SOURCE_DIR}"

    fi
}

trap cleanup_installer EXIT


if [ -f "$SOURCE_DIR/.git/config" ]; then
    SOURCE_ORIGIN="$(
        git config \
            --file "$SOURCE_DIR/.git/config" \
            --get remote.origin.url \
            2>/dev/null ||
        true
    )"
fi

case "$SOURCE_ORIGIN" in
    *"/SvxLink-Dash-V4.0.git"|*"/SvxLink-Dash-V4.0")
        ;;
    *)
        echo "ERROR: The installer source is not a recognised V4.0 checkout." >&2
        echo "Source: $SOURCE_DIR" >&2
        echo "Origin: ${SOURCE_ORIGIN:-not detected}" >&2
        exit 1
        ;;
esac

if [ -e "$INSTALL_DIR" ]; then
    if [ ! -d "$INSTALL_DIR" ]; then
        echo "ERROR: $INSTALL_DIR exists but is not a directory." >&2
        exit 1
    fi

    EXISTING_ORIGIN=""

    if [ -f "$INSTALL_DIR/.git/config" ]; then
        EXISTING_ORIGIN="$(
            git config \
                --file "$INSTALL_DIR/.git/config" \
                --get remote.origin.url \
                2>/dev/null ||
            true
        )"
    fi

    case "$EXISTING_ORIGIN" in
        *"/SvxLink-Dash-V3.git"|*"/SvxLink-Dash-V3")
            EXISTING_RELEASE="V3"
            ;;
        *"/SvxLink-Dash-V3.0.git"|*"/SvxLink-Dash-V3.0")
            EXISTING_RELEASE="V3.0"
            ;;
        *"/SvxLink-Dash-V3.1.git"|*"/SvxLink-Dash-V3.1")
            EXISTING_RELEASE="V3.1"
            ;;
        *"/SvxLink-Dash-V4.0.git"|*"/SvxLink-Dash-V4.0")
            EXISTING_RELEASE="V4.0"
            ;;
        *)
            echo "ERROR: Unrecognised existing dashboard installation." >&2
            echo "Directory: $INSTALL_DIR" >&2
            echo "Origin: ${EXISTING_ORIGIN:-not detected}" >&2
            echo "No dashboard files have been replaced." >&2
            exit 1
            ;;
    esac
fi

apt update

apt install -y git python3 python3-flask python3-jinja2 python3-werkzeug sox device-tree-compiler gpiod python3-libgpiod
if [ ! -d /opt ]; then
    mkdir -p /opt
fi

#-----------------------
# Svxlink-Streamer
#-----------------------

STREAMER_SOURCE_DIR="/opt/.svxlink-streamer-${TIMESTAMP}-$$"

echo "Installing Svxlink-Streamer..."

if ! git clone \
    --depth 1 \
    "$STREAMER_REPO_URL" \
    "$STREAMER_SOURCE_DIR"
then
    echo "ERROR: Could not clone Svxlink-Streamer." >&2
    rm -rf -- "$STREAMER_SOURCE_DIR"
    exit 1
fi

if [ ! -x "$STREAMER_SOURCE_DIR/scripts/install.sh" ]; then
    echo "ERROR: Svxlink-Streamer installer was not found." >&2
    rm -rf -- "$STREAMER_SOURCE_DIR"
    exit 1
fi

if ! "$STREAMER_SOURCE_DIR/scripts/install.sh"; then
    echo "ERROR: Svxlink-Streamer installation failed." >&2
    rm -rf -- "$STREAMER_SOURCE_DIR"
    exit 1
fi

rm -rf -- "$STREAMER_SOURCE_DIR"
STREAMER_SOURCE_DIR=""

echo "Svxlink-Streamer installed."

echo "Preparing a clean SvxLink-Dash V4.0 application tree..."

git clone \
    --no-hardlinks \
    "$SOURCE_DIR" \
    "$STAGING_DIR"

git -C "$STAGING_DIR" remote set-url origin "$REPO_URL"

if [ -n "$EXISTING_RELEASE" ]; then
    BACKUP_DIR="$BACKUP_ROOT/${TIMESTAMP}-${EXISTING_RELEASE}-$$"

    install -d \
        -o root \
        -g root \
        -m 0755 \
        "$BACKUP_ROOT"

    echo "Backing up the existing $EXISTING_RELEASE dashboard:"
    echo "  $BACKUP_DIR"

    cp -a \
        "$INSTALL_DIR" \
        "$BACKUP_DIR"

    if [ ! -d "$BACKUP_DIR" ]; then
        echo "ERROR: The existing dashboard backup could not be verified." >&2
        exit 1
    fi

    systemctl stop svxlink-dash.service \
        2>/dev/null ||
        true

    PREVIOUS_DIR="${INSTALL_DIR}.previous-${TIMESTAMP}-$$"

    mv \
        "$INSTALL_DIR" \
        "$PREVIOUS_DIR"

    if ! mv "$STAGING_DIR" "$INSTALL_DIR"; then
        mv "$PREVIOUS_DIR" "$INSTALL_DIR"
        echo "ERROR: Could not activate the V4.0 application tree." >&2
        exit 1
    fi

    if [ "$EXISTING_RELEASE" = "V4.0" ]; then
        echo "Restoring the existing V4.0 runtime configuration."

        for CONFIG_FILE in \
            node_model.json \
            talkgroups.json \
            gpio_lines.json
        do
            if [ -f "$BACKUP_DIR/config/$CONFIG_FILE" ]; then
                cp -a \
                    "$BACKUP_DIR/config/$CONFIG_FILE" \
                    "$INSTALL_DIR/config/$CONFIG_FILE"
            fi
        done

        if [ -d "$BACKUP_DIR/config/backups" ]; then
            cp -a \
                "$BACKUP_DIR/config/backups" \
                "$INSTALL_DIR/config/backups"
        fi

        if [ -d "$BACKUP_DIR/backups" ]; then
            cp -a \
                "$BACKUP_DIR/backups" \
                "$INSTALL_DIR/backups"
        fi
    else
        echo "The $EXISTING_RELEASE configuration remains available in:"
        echo "  $BACKUP_DIR"
        echo "V4.0 will begin with a new guided configuration."
    fi
else
    mv "$STAGING_DIR" "$INSTALL_DIR"
fi

chmod +x "$INSTALL_DIR/install/fix-permissions.sh"
"$INSTALL_DIR/install/fix-permissions.sh"

cp "$INSTALL_DIR/install/svxlink-dash.service" /etc/systemd/system/svxlink-dash.service
chmod +x "$INSTALL_DIR/install/fix-permissions.sh"
"$INSTALL_DIR/install/fix-permissions.sh"
#-----------------------
# ICS_preparatory stage
#-----------------------
ICS_HELPER_SOURCE="/opt/dashboard/install/svxlink_dashboard_ics_prepare"
ICS_HELPER_DEST="/usr/local/sbin/svxlink_dashboard_ics_prepare"

echo "Installing or updating SvxLink Dashboard ICS preparation helper..."

if [ ! -f "$ICS_HELPER_SOURCE" ]; then
    echo "ERROR: ICS preparation helper source not found:"
    echo "       $ICS_HELPER_SOURCE"
    exit 1
fi

install \
    -o root \
    -g root \
    -m 0755 \
    "$ICS_HELPER_SOURCE" \
    "$ICS_HELPER_DEST"

echo "Installed or updated $ICS_HELPER_DEST"

#-----------------------
# NanoPi preparation stage
#-----------------------

NANOPI_HELPER_SOURCE="/opt/dashboard/install/svxlink_dashboard_nanopi_prepare"
NANOPI_HELPER_DEST="/usr/local/sbin/svxlink_dashboard_nanopi_prepare"

echo "Installing SvxLink Dashboard NanoPi preparation helper..."

if [ ! -f "$NANOPI_HELPER_SOURCE" ]; then
    echo "ERROR: NanoPi preparation helper source not found:"
    echo "       $NANOPI_HELPER_SOURCE"
    exit 1
fi

install \
    -o root \
    -g root \
    -m 0755 \
    "$NANOPI_HELPER_SOURCE" \
    "$NANOPI_HELPER_DEST"

echo "Installed or updated $NANOPI_HELPER_DEST"

#-----------------------
# SvxLink service-account preparation helper
#-----------------------

SERVICE_ACCOUNT_HELPER_SOURCE="/opt/dashboard/install/svxlink_dashboard_service_account_prepare"
SERVICE_ACCOUNT_HELPER_DEST="/usr/local/sbin/svxlink_dashboard_service_account_prepare"

if [ ! -f "$SERVICE_ACCOUNT_HELPER_SOURCE" ]; then
    echo "ERROR: Service-account preparation helper source not found:"
    echo "       $SERVICE_ACCOUNT_HELPER_SOURCE"
    exit 1
fi

install \
    -o root \
    -g root \
    -m 0755 \
    "$SERVICE_ACCOUNT_HELPER_SOURCE" \
    "$SERVICE_ACCOUNT_HELPER_DEST"

"$SERVICE_ACCOUNT_HELPER_DEST" no-gpio

echo "Prepared the SvxLink service account and C-Media HIDRAW access."

#-----------------------
# Svxlink-Dash Library files
#-----------------------
echo "Preparing SvxLink Dashboard runtime directories..."

install -d -o svxlink -g svxlink -m 0775 \
    /var/lib/svxlink-dash \
    /var/lib/svxlink-dash/sounds \
    /var/lib/svxlink-dash/sounds/idents \
    /var/lib/svxlink-dash/backups
#-----------------------
# Configure sudo permissions
#----------------------

SUDOERS_FILE="/etc/sudoers.d/svxlink-dash"

if [ -L "$SUDOERS_FILE" ]; then
    echo "ERROR: Refusing to replace symbolic sudoers path:" >&2
    echo "       $SUDOERS_FILE" >&2
    exit 1
fi

if [ -d "$SUDOERS_FILE" ]; then
    echo "Removing an empty directory obstructing the sudoers file:"

    if ! rmdir "$SUDOERS_FILE"; then
        echo "ERROR: $SUDOERS_FILE is a non-empty directory." >&2
        echo "Its contents have been preserved for manual review." >&2
        exit 1
    fi
elif [ -e "$SUDOERS_FILE" ] && [ ! -f "$SUDOERS_FILE" ]; then
    echo "ERROR: The sudoers path is not a regular file:" >&2
    echo "       $SUDOERS_FILE" >&2
    exit 1
fi

cat > "$SUDOERS_FILE" <<'EOF'
# SvxLink-Dash-V4.0 controlled service permissions

svxlink ALL=(root) NOPASSWD: \
    /usr/bin/systemctl restart svxlink.service, \
    /usr/bin/systemctl is-active svxlink.service, \
    /usr/bin/systemctl stop svxlink.service, \
    /usr/bin/systemctl start svxlink.service, \
    /usr/bin/systemctl restart svxlink-dash.service, \
    /usr/bin/systemctl is-active svxlink-dash.service, \
    /usr/sbin/shutdown, \
    /usr/bin/systemctl, \
    /usr/bin/mkdir, \
    /usr/bin/chown, \
    /usr/bin/chmod, \
    /usr/bin/git, \
    /usr/bin/devcal, \
    /usr/bin/systemd-run, \
    /usr/bin/install, \
    /usr/bin/pkill, \
    /usr/local/sbin/svxlink_dashboard_ics_prepare, \
    /usr/local/sbin/svxlink_dashboard_nanopi_prepare, \
    /usr/local/sbin/svxlink_dashboard_service_account_prepare, \
    /usr/bin/nmcli, \
    /usr/bin/sh
EOF


chmod 0440 "$SUDOERS_FILE"
visudo -c -f "$SUDOERS_FILE"
# Wifi install
# -------------------------------------------------
# Install network failsafe helper
# -------------------------------------------------
#
#install -o root -g root -m 755 \
#    network_failsafe.py \
#    /opt/dashboard/services/network_failsafe.py
#
# -------------------------------------------------
# Install systemd service
# -------------------------------------------------

cat > /etc/systemd/system/network-failsafe.service <<'EOF'
[Unit]
Description=SvxLink Dashboard Network Failsafe
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/dashboard/services/network_failsafe.py
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

chmod 644 /etc/systemd/system/network-failsafe.service
chown root:root /etc/systemd/system/network-failsafe.service

# -------------------------------------------------
# Enable failsafe service
# -------------------------------------------------

systemctl daemon-reload
systemctl enable --now network-failsafe.service

# -------------------------------------------------
# Create hotspot profile
# -------------------------------------------------

echo "Creating NetworkManager hotspot profile..."

nmcli connection add \
    type wifi \
    ifname wlan0 \
    con-name Hotspot \
    autoconnect no \
    ssid svxlink || true

nmcli connection modify Hotspot \
    802-11-wireless.mode ap \
    802-11-wireless.band bg \
    ipv4.method shared \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk "password" || true
#end- Wifi profile

cat > /etc/logrotate.d/svxlink <<'EOF'
/var/log/svxlink.log {
    su svxlink svxlink
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0664 svxlink svxlink
    sharedscripts
    postrotate
        /usr/bin/systemctl reload svxlink.service
    endscript
}
EOF

chmod 644 /etc/logrotate.d/svxlink
chown root:root /etc/logrotate.d/svxlink

cp "$INSTALL_DIR/install/svxlink-dash.service" /etc/systemd/system/svxlink-dash.service
systemctl daemon-reload
systemctl enable svxlink-dash
systemctl restart svxlink-dash

if [ -n "$PREVIOUS_DIR" ] && [ -d "$PREVIOUS_DIR" ]; then
    rm -rf -- "$PREVIOUS_DIR"
fi

echo "SvxLink-Dash installed."
echo "Open: http://<node-ip>:5000/"
