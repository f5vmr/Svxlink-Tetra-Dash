# SvxLink-Dash V4.1

SvxLink-Dash V4.1 is a Flask-based configuration and runtime dashboard for SvxLink 26.05.2 and its predecessor.

It provides a guided environment for configuring, building and operating simplex, repeater and multi-port SvxLink installations. It is suitable for independently operated nodes and is not restricted to a particular reflector network, region or deployment model.

SvxLink 26.05.2 is developed by Tobias Blomberg, SM0SVX.

## Principal features

- Guided SvxLink configuration
- Single-port and multi-port installations
- SimplexLogic and RepeaterLogic configuration
- Local port-to-port links
- SvxReflector connection and authentication
- Federation-family and independent reflector routes
- EchoLink and METAR module configuration
- GPIO, serial, HIDRAW and audio-interface configuration
- Installation-wide courtesy, idle and closedown tones
- Public node information and optional LocationInfo generation
- Configuration review before deployment
- Managed configuration deployment and SvxLink restart
- Protected runtime configuration editing
- Live service, radio and reflector status
- Talkgroup monitoring and DTMF control
- Local RF CTCSS talkgroup selection
- Hardware and system telemetry
- Live SvxLink log viewing

## Intended installations

SvxLink-Dash V4.1 is intended for:

- New or existing SvxLink operators who require guided configuration.
- Appliance-style installations using Raspberry Pi or NanoPi Neo hardware.
- Generic Debian-based Linux computers running SvxLink.
- Single-channel radio interfaces.
- Independent dual-USB radio interfaces.
- Supported ICS-CTRLS 1X, 2X, 4X and 8X hardware.

The dashboard is currently presented in English.

## Configuration builder

The guided workflow covers:

- Platform and hardware selection
- Radio-port selection
- Simplex and repeater roles
- Audio and control interfaces
- Squelch detection
- Identification and CW
- Courtesy, idle and closedown tones
- Repeater operating settings
- SvxReflector access
- Local and reflector-link topology
- EchoLink and METAR modules
- Node information
- Final configuration review and deployment

## Runtime dashboard

The runtime dashboard provides:

- SvxLink service status
- Reflector connection state
- Radio and squelch status
- Active and monitored talkgroups
- EchoLink activity
- Reflector activity
- DTMF talkgroup controls
- Manual DTMF command entry
- Host and operating-system information
- CPU temperature where available
- Memory and disk utilisation
- Live SvxLink log output

## Protected editing

Authenticated runtime pages allow authorised operators to update supported settings without repeating the initial setup workflow.

Protected facilities include:

- Talkgroup controls
- Monitoring talkgroups
- Local RF CTCSS talkgroup mappings
- EchoLink configuration
- METAR configuration
- Macro configuration
- Node information
- Live log viewing
- Guided reconfiguration

Saved changes are presented for review before the managed configuration is rebuilt and deployed.

## Supported platforms

The configuration model recognises:

- Raspberry Pi
- NanoPi Neo
- Generic Linux server

Runtime architecture reporting recognises:

- 32-bit ARM (`armhf`)
- 64-bit ARM (`arm64`)
- 32-bit x86 (`i386`; tested on `i686`)
- 64-bit x86 (`amd64`)

The dashboard is intended for Debian-based operating systems on which SvxLink 26.05.2 is already installed and operational.

Platform recognition and hardware-profile support are separate. Not every hardware profile is appropriate for every platform.

## Hardware profiles

Available hardware profiles include:

- Generic Single Channel
- Dual USB Sound Fob Interfaces
- ICS-CTRLS 1X
- ICS-CTRLS 2X
- ICS-CTRLS 4X
- ICS-CTRLS 8X

Some hardware profiles require additional preparation, device-tree overlays, ALSA configuration or a system reboot. The guided workflow identifies those requirements when the profile is selected.

### Dual USB Sound Fob Interfaces

The Dual USB Sound Fob Interfaces profile supports exactly two separate duplex
USB radio interfaces, including compatible CM108 and CM119 devices.

Both interfaces must be connected before hardware preparation is completed.
The Dashboard discovers the two duplex USB audio devices in their current ALSA
order and assigns them to Port 1 and Port 2. ALSA card numbers do not need to be
0 and 1; other host audio devices may occupy lower card numbers.

The discovered named ALSA identifiers, such as
`alsa:plughw:CARD=Set,DEV=0`, are stored in the node configuration instead of
raw numeric card indices. The corresponding C-Media HIDRAW devices are recorded
with the same port assignments.

The installer grants the `svxlink` service account the required audio and USB
device-group membership and installs a udev rule providing group access to
C-Media HIDRAW devices. The rule covers C-Media vendor ID `0d8c`, including the
tested CM108-compatible and CM119-compatible interfaces.

Once preparation has assigned the two interfaces, leave them connected to their
original physical USB sockets. Moving or exchanging the devices can change
their detected order and therefore requires the hardware-preparation check to
be repeated.

## Radio control and squelch detection

The selected hardware profile determines which audio, receiver-control and
transmitter-control choices are appropriate for each radio port.

Supported interface modes include:

* HIDRAW for compatible CM108, CM119, TOADS and related USB interfaces

* GPIOD for receiver SQL and transmitter PTT controlled through Linux GPIO
  lines

* Hybrid control using different supported methods for SQL and PTT

* Serial-port control

HIDRAW and GPIOD inputs can be configured for the active sense required by the
connected hardware. An incorrect active-high or active-low selection commonly
causes the Dashboard to show the receiver as permanently open or permanently
closed.

Each enabled port has its own receiver, transmitter and squelch configuration.
In a multi-port system, changing one port does not alter another port's
radio-control settings.


### Standard squelch methods

The guided standard choices are:

* HIDRAW - uses the supported USB-interface input

* GPIOD - uses the configured GPIO chip and line

* SERIAL - uses the selected serial-port signal

* CTCSS - asks SvxLink to detect the configured sub-audible tone

When CTCSS is the active SQL detector, a receive CTCSS frequency is required.
The operator may also select transmit CTCSS when the connected radio system
requires the same tone to be transmitted.

For repeater operation, selecting CTCSS-controlled squelch also causes the
generated logic to use the corresponding CTCSS opening condition.


### Advanced and specialist squelch examples

The Dashboard can record and render commented examples for advanced detectors
without activating them automatically.

Advanced examples include:

* VOX

* SIGLEV using noise detection

* COMBINE

A COMBINE example uses AND logic and requires two or three selected components
from:

* VOX

* SIGLEV

* CTCSS

The specialist manual examples are:

* EVDEV

* PTY

* RTL_SDR

These advanced and specialist selections require manual completion, device
mapping, any necessary supporting software and operational testing. The
generated examples remain commented until the operator deliberately completes
and enables them.


### CTCSS squelch and CTCSS TalkGroup selection

CTCSS-controlled squelch and local RF CTCSS TalkGroup selection serve
different purposes and must not be confused.

CTCSS-controlled squelch answers:

    Should this received RF signal open the receiver?

Local RF CTCSS TalkGroup selection answers:

    Which reflector TalkGroup should this received RF signal select?

A port cannot use local RF CTCSS TalkGroup selection when CTCSS already
participates in its squelch decision, either as the standard CTCSS detector or
as a component of an advanced COMBINE example.

Eligible ports may instead map individual received CTCSS tones to reflector
TalkGroups. Each mapping requires:

* A positive CTCSS frequency

* A positive whole-number TalkGroup

* A tone that is not duplicated in another mapping for the same logic

* At least one mapping when the facility is enabled

An optional non-negative detection delay can reject very short tone detections
before they select a TalkGroup.

These mappings apply only to local RF traffic received by the selected radio
logic. They are separate from monitored TalkGroups, which determine which
traffic is accepted from the reflector.

DTMF TalkGroup selection remains available when CTCSS is used as the
receiver's ordinary squelch-access condition.

## Installation

SvxLink-Bootstrap is the recommended installation method. It prepares a supported SvxLink 26.05.2 installation, installs SvxLink-Dash V4.1 and hands control to the permanent Dashboard configuration workflow.

### Recommended Bootstrap installation

Begin with a supported Debian or Raspberry Pi OS installation connected to the local network. Administrative access through `sudo` is required.

Run the Bootstrap launcher:

```bash
curl -fsSL \
https://raw.githubusercontent.com/f5vmr/Svxlink-Bootstrap/main/launch-bootstrap.sh |
sudo sh
```

The launcher installs essential prerequisites when necessary, obtains SvxLink-Bootstrap and starts its temporary browser manager.

Open the complete URL printed in the terminal. It includes a temporary access token and normally uses port `8765`.

Bootstrap then:

1. Detects the operating system, release, architecture and hardware platform.

2. Selects the exact compatible SvxLink  package.

3. Classifies any existing package-managed or compiler installation.

4. Creates a timestamped configuration backup when an existing supported installation is adopted.

5. Downloads and verifies the selected package when required.

6. Installs and verifies SvxLink.

7. Obtains SvxLink-Dash V4.1 and runs its established installer.

8. Opens the permanent Dashboard configuration workflow.

Do not close the browser or terminal, interrupt the launcher or remove power while installation is running.

After successful handover, the browser opens:

```text
http://<dashboard-hostname-or-address>:5000/start
```

The temporary Bootstrap manager then shuts down. Port `8765` is not the permanent Dashboard address.

Complete Bootstrap installation, migration, compatibility and troubleshooting documentation is available at:

[SvxLink-Bootstrap](https://github.com/f5vmr/Svxlink-Bootstrap#readme)

### Direct Dashboard installation

Direct installation is intended for systems where SvxLink 26.05.2 has already been installed correctly or for development and recovery work.

Before using the direct installer, confirm that:

* SvxLink 26.05.2 or a previous version is installed.

* `svxlink.service` is available.

* The `svxlink` user and group exist.

* `/etc/svxlink` is present.

* The computer is connected to the local network.

* You have local administrative access through `sudo`.

A newly installed or reconfigured SvxLink service does not have to be running before Dashboard configuration begins. It may remain inactive until a valid configuration has been built and deployed.

Clone the repository into a temporary directory and run the executable installer:

```bash
cd /tmp

git clone \
https://github.com/f5vmr/SvxLink-Dash-V4.1.git

cd SvxLink-Dash-V4.1

sudo ./install/install-dashboard.sh
```

The direct Dashboard installer does not install or replace the SvxLink package.

### Installed locations and service account

The installer places the operational Dashboard in:

```text
/opt/dashboard
```
The saved configuration model is stored at:

```text
/opt/dashboard/config/node_model.json
```
Before a full configuration reset, the previous model is copied beneath:

```text
/opt/dashboard/config/backups
```
Before deployment, existing svxlink.conf and svxlink.d/*.conf files are
copied beneath:

```text
/opt/dashboard/backups
```
Persistent Dashboard sound data, including generated identification audio,
is stored beneath:

```text
/var/lib/svxlink-dash/sounds
```

The Bootstrap installer also prepares /var/lib/svxlink-dash/backups, but the current
Dashboard backup routines do not use that directory.

The current node model is stored here:
```text
/opt/dashboard/config/node_model.json
```

The Dashboard service runs as:

```text
svxlink:svxlink
```

The installer creates and enables:

```text
svxlink-dash.service
```

### Confirm the installation

Check the Dashboard service:

```bash
sudo systemctl status \
svxlink-dash.service \
--no-pager
```

It should report:

```text
active (running)
```

Check SvxLink separately:

```bash
sudo systemctl status \
svxlink.service \
--no-pager
```

On a new installation, `svxlink.service` may remain inactive until the guided workflow has produced and deployed a valid configuration. This does not prevent the Dashboard from being used.

### First access

Open the Dashboard from a browser on the same network:

```text
http://<dashboard-hostname-or-address>:5000/
```

Where local hostname resolution is available, the default hostname may be used:

```text
http://svxlink.local:5000/
```

A new installation presents the authorisation and initial configuration workflow. Create the Dashboard credentials, complete the guided configuration, review the validated model and deploy the generated SvxLink configuration.

### Updating SvxLink-Dash

SvxLink-Bootstrap remains the recommended route when preparing or migrating
the complete appliance. It checks and prepares SvxLink before running the
Dashboard installer.

For a direct Dashboard update, run the installer from a current temporary V4.1
clone. The installer deploys that checkout as a clean application tree; it does
not run `git pull` inside `/opt/dashboard`.

When `/opt/dashboard` already exists, its Git origin is checked before any
package installation or file replacement. The installer recognises:

* SvxLink-Dash V3.0
* SvxLink-Dash V3.1
* SvxLink-Dash V4.1

An existing directory with an absent or unrecognised Git origin is refused and
left unchanged.

Before replacing a recognised installation, the complete existing
`/opt/dashboard` tree is copied beneath:

```text
/var/backups/svxlink-dash
```

Each backup uses a timestamp, detected release and process identifier. The
existing Dashboard service is stopped only after the backup has completed and
been verified.

The new V4.1 application tree is prepared separately and then moved into
`/opt/dashboard`. If that activation fails, the previous tree is immediately
returned to its original location. The temporary previous tree is removed only
after the V4.1 service has restarted successfully.

The installer then refreshes permissions, helper programs, service files and
supporting installation resources, reloads systemd, enables
`svxlink-dash.service` and restarts the Dashboard.

### V3.0 and V3.1 replacement

V3.0 and V3.1 installations are replaced with a clean V4.1 application tree.
Their complete application directory and saved data remain available in the
timestamped backup beneath `/var/backups/svxlink-dash`.

V3 configuration files are not inserted automatically into the V4 model.
Differences between the older configuration structures and the V4 validated
model make automatic reuse unsafe. After replacement, complete the V4 guided
configuration. The archived V3 files may be consulted when transferring
operator settings.

Generated SvxLink configuration beneath `/etc/svxlink` is outside the
Dashboard application tree and is not removed merely by replacing the
Dashboard. A later V4 build may deliberately replace Dashboard-managed
SvxLink files after validation and its normal configuration backup.

### V4.0 and V4.1 configuration preservation during updates

When an existing V4.0 or V4.1 installation is updated, the installer restores these
runtime files from the verified application backup when they exist:

```text
/opt/dashboard/config/node_model.json
/opt/dashboard/config/talkgroups.json
/opt/dashboard/config/gpio_lines.json
/opt/dashboard/config/backups
/opt/dashboard/backups
```

The saved node model is loaded through the Dashboard model-migration process so
that newly introduced defaults can be added while preserving explicit operator
selections.

Persistent identification sounds beneath
`/var/lib/svxlink-dash/sounds` are outside the application tree and remain in
place during an update.

### Rollback limitations

SvxLink-Dash does not provide an automatic application-version rollback
command. The complete pre-replacement application backup beneath
`/var/backups/svxlink-dash` provides the material required for an
administrative rollback.

An older Dashboard version may not understand a model that has already been
migrated or extended by a newer version. Before restoring an earlier
application, also preserve:

* Required files beneath `/etc/svxlink`
* Persistent identification sounds beneath `/var/lib/svxlink-dash/sounds`
* Any V4 model or configuration created after the installation backup

After a rollback, validate the restored model and generated configuration
before restarting SvxLink. If compatibility is uncertain, restore the matching
Dashboard application, saved model and SvxLink configuration together, or
rebuild through the guided workflow.

## Authentication

Runtime monitoring is publicly accessible on the local network. Configuration and management functions require dashboard authentication.

Protected facilities include:

* Talkgroup controls
* Monitoring talkgroups
* Local RF CTCSS talkgroup mappings
* EchoLink configuration
* METAR configuration
* Macro configuration
* Node information
* Guided reconfiguration
* Live log viewing

Dashboard credentials are created during the initial setup workflow.

### Forgotten credentials

Dashboard credentials can be reset from the Linux console:

```bash
sudo /opt/dashboard/tools/reset_dashboard_auth.py
```

After resetting the credentials, follow the command’s displayed instructions and sign in again.

## Service management

The installer creates and enables:

```text
svxlink-dash.service
```

The dashboard runs as the `svxlink` user so that it can access dashboard-managed configuration, runtime controls and SvxLink operational information.

### View dashboard status

```bash
sudo systemctl status \
svxlink-dash.service \
--no-pager
```

### Restart the dashboard

```bash
sudo systemctl restart \
svxlink-dash.service
```

### View dashboard service messages

```bash
sudo journalctl \
-u svxlink-dash.service \
-n 100 \
--no-pager
```

### Restart SvxLink

```bash
sudo systemctl restart \
svxlink.service
```

## SvxLink log detection

The dashboard automatically locates the configured SvxLink log.

It first checks the `LOGFILE` setting in:

```text
/etc/default/svxlink
```

It can also recognise the standard locations:

```text
/var/log/svxlink.log
/var/log/svxlink
```

The protected live-log page displays the detected log output.

## Modules and macros

Every generated installation includes ModuleHelp and ModuleParrot.

EchoLink and METAR are optional modules selected during guided configuration.
Their protected editing pages remain available after deployment, and saved
changes are incorporated into a rebuilt SvxLink configuration.


### EchoLink configuration

Enabling EchoLink adds ModuleEchoLink and opens the EchoLink configuration
stage.

The required information is:

* An EchoLink callsign ending in -L or -R

* The EchoLink password

* The sysop name

* A location description

The Dashboard automatically prefixes the published location with [Svx]. The
operator-entered part of the location is limited to 12 characters.

The runtime Dashboard reports EchoLink activity and provides protected
EchoLink controls. Optional EchoLink status publication through LocationInfo
is configured separately and is available only while EchoLink is enabled.


### METAR configuration

Enabling METAR adds ModuleMetarInfo.

The operator first selects the appropriate airport region and one default
airport. Up to six additional airports may then be selected from that region.
The Dashboard validates the default airport against the chosen regional
catalogue before saving it.

The runtime controls can open the generated METAR module and select configured
airport entries. Module identifiers may differ if the generated configuration
has been customised.


### Macro management

The protected macro page manages the generated [Macros] section. Existing
macros discovered from SvxLink configuration are retained in the model where
possible.

The Dashboard supports up to 16 macros. Every configured row requires a unique
macro number.

Structured macro types include:

* Reflector TalkGroup reset

* Recall the previous reflector TalkGroup

* Select a specified non-zero reflector TalkGroup

* Send a command to an enabled module

* Preserve an operator-supplied custom SvxLink macro command

Module macros require both a module name and a command. EchoLink and MetarInfo
are offered as structured module destinations only when their corresponding
modules are enabled. The Dashboard adds the terminating # to a structured
module command when it is omitted.

Custom commands are stored without reinterpretation and remain the operator's
responsibility.

Saving macros updates the model, rebuilds the managed SvxLink configuration
and requests a SvxLink restart. If rebuild or restart fails, the Dashboard
reports that the macro settings were saved but were not successfully deployed.

## Default manual DTMF commands

The runtime dashboard can send DTMF commands through the configured SvxLink control FIFO.

### Talkgroup selection

Prefix the talkgroup number with `91` and terminate the command with `#`.

Example for talkgroup 235:

```text
91235#
```

### EchoLink

Open the default EchoLink module:

```text
2#
```

Enter the required EchoLink node number followed by `#`:

```text
<node-number>#
```

Exit the EchoLink module:

```text
##
```

### METAR

Open the default METAR module:

```text
5#
```

Select a configured airport entry:

```text
1#
```

Exit the METAR module:

```text
#
```

Module identifiers and macros may differ when the operator changes the generated configuration.

## Troubleshooting

### Dashboard does not start

Check the service status:

```bash
sudo systemctl status \
svxlink-dash.service \
--no-pager
```

View its recent service messages:

```bash
sudo journalctl \
-u svxlink-dash.service \
-n 100 \
--no-pager
```

### Dashboard page does not open

Confirm that `svxlink-dash.service` is active and use the Linux computer’s current IP address:

```bash
hostname -I
```

Open the first reported address on port 5000:

```text
http://<ip-address>:5000/
```

### Live log viewer has no output

Check the configured SvxLink log path:

```bash
grep '^LOGFILE=' \
/etc/default/svxlink
```

If `/var/log/svxlink.log` is in use, inspect it directly:

```bash
tail -f \
/var/log/svxlink.log
```

### DTMF controls do not work

Confirm that the appropriate SvxLink DTMF control FIFO exists:

```text
/dev/shm/simplex_dtmf_ctrl
/dev/shm/repeater_dtmf_ctrl
```

The required FIFO depends on the configured radio logic. It must be writable by the `svxlink` user.

Also confirm that SvxLink is active:

```bash
sudo systemctl status \
svxlink.service \
--no-pager
```

## Guided configuration sequence

The configuration workflow establishes the available hardware, configures every enabled radio port and identifies the primary installation identity before creating any local or reflector links.

The normal sequence is:

1. Select the hardware platform.
2. Select the hardware profile and enable the required radio ports.
3. Assign each enabled port as `SimplexLogic` or `RepeaterLogic`.
4. Configure the node, interface, squelch, identification and CW settings for each enabled port.
5. Select the installation-wide courtesy, idle and closedown tones.
6. Configure optional emergency DTMF online/offline control for each radio logic.
7. Complete the repeater settings for any repeater ports.
8. Select the primary installation port. A single-port installation selects its only port automatically.
9. Select whether the installation will use a reflector.
10. Configure the reflector route and authentication method when required.
11. Select reflector node-map publication and, independently, SvxLink LocationInfo and APRS publication.
12. Assign every enabled port to independent operation, a local link or the reflector link.
13. Validate and review the complete configuration.
14. Build and deploy the generated SvxLink configuration.

The reflector route follows primary-port selection so that `ReflectorLogic` uses the correct installation callsign. This is especially important for Protocol 3, where the callsign forms part of the certificate identity.

Link topology is configured after the available ports, their logic types and the reflector route are known.

Node-map and LocationInfo publication choices are separate. Both describe the selected primary radio port, but only reflector node-map publication controls whether `/etc/svxlink/node_info.json` contains the public information used by the connected reflector’s map.

## Primary installation identity

Every multi-port installation has one selected primary port.

The callsign assigned to that port becomes the primary callsign of the installation. Port number and configuration order do not override the selected primary identity.

The primary callsign is used where one callsign must represent the complete installation, including:

* `ReflectorLogic`
* Node information
* Dashboard installation identification
* The system login display or MOTD

A single-port installation automatically uses the callsign of its only configured radio logic.

When reflector operation is enabled:

* The primary port is included in the reflector link.
* `ReflectorLogic` uses the primary installation callsign.
* Additional ports may participate in the same reflector link.
* Additional ports may use the same or different callsigns.
* A secondary port never replaces the selected primary identity merely because it has a lower port number or was configured first.

For example:

```text
Port 1 — RepeaterLogic — AK6BL — Primary
Port 2 — SimplexLogic — KO6IL-L
```

Both ports may participate in the reflector link:

```ini
[LinkToReflector]
CONNECT_LOGICS=RepeaterLogic1:9,SimplexLogic2:9,ReflectorLogic
DEFAULT_ACTIVE=1
TIMEOUT=300
```

The reflector identity remains:

```ini
[ReflectorLogic]
CALLSIGN=AK6BL
```

For Protocol 3 operation, the `ReflectorLogic` callsign determines the X.509 client-certificate identity. Changing the primary callsign may therefore require a new certificate request and approval by the reflector administrator.

When reflector operation is disabled, the primary port may remain independent or participate in a local link. It continues to provide the installation identity.

## Installation-wide tone settings

Courtesy, idle and closedown tones are shared installation settings. They are not configured independently for each port because SvxLink produces them through common event-handling files.

The available settings are:

* Courtesy tone
* Courtesy beep frequency
* Repeater idle tone
* Repeater closedown tone

Courtesy behaviour is applied through the shared `Logic.tcl` event handling.

Idle and closedown behaviour is applied through the shared `RepeaterLogicType.tcl` event handling and affects every configured repeater logic.

Courtesy choices are:

* None
* Morse A, D, E, I, K, M, N, R, S, T, U or X
SvxLink generates the selected Morse character using the configured CW
pitch, speed and level. E, I, K and R are common choices.

Repeater idle-tone choices are:

* None
* Pip
* Chime

Repeater closedown-tone choices are:

* None
* Biboop
* VA

`None` is a valid deliberate selection in every case. A courtesy tone is commonly used for repeater operation, but it is not mandatory.

The dashboard applies each shared event-file customisation once, regardless of the number of configured radio ports.

## Emergency DTMF online/offline control

Emergency DTMF control is optional and configured separately for each
simplex or repeater radio logic, including individual ports in a multi-port
installation.

Enable the feature and enter a private six-digit command. Leading zeroes
are preserved. Enter only the six digits in the configuration page, without
`*`, `#` or the final online/offline selection digit.

Share the command only with authorised operators.

To operate the control over the radio:

* Enter the private command followed by `0#` to take the logic offline.
* Enter the private command followed by `1#` to return the logic online.
* Prefix the complete command with `*` if a module is active.

When enabled, the generated radio logic section contains the configured
`ONLINE_CMD` and `ONLINE=1`. The generated startup setting is online.
When disabled, the configuration retains a commented manual example.

Existing installations can change these settings through
**Rebuild / Reconfigure → Emergency DTMF Control**.

Save the settings, rebuild the configuration and restart SvxLink to apply
the change.

## Node information and LocationInfo publication

SvxLink-Dash treats reflector node-map publication and SvxLink LocationInfo
publication as separate facilities.

They share public location and RF details because both describe the same
installation, but enabling one does not automatically enable the other.

### Reflector node-map publication

Reflector node-map publication controls the contents of:

    /etc/svxlink/node_info.json

When enabled, the Dashboard populates this file with the public information
used to represent the node on the connected reflector's map.

The generated information includes, where supplied:

* Node location or administrative area

* QTH name

* Sysop callsign

* Decimal latitude and longitude

* Maidenhead locator

* Receiver and transmitter frequencies

* Receiver squelch type

* Transmitter power

* Antenna description, height and direction

For a single-port installation, the generated radio names are Rx1 and Tx1.

For a multi-port installation, node_info.json represents the selected primary
port. The receiver and transmitter names therefore use that port number, such
as Rx2 and Tx2.

A receiver configured for CTCSS squelch is published with the CTCSS squelch
type. Other supported physical squelch methods are represented as COR.

When reflector node-map publication is disabled, the Dashboard writes an
empty JSON object rather than publishing the stored node details:

    {}

Stored information can therefore be retained for later use without appearing
on the reflector map.

### SvxLink LocationInfo and APRS

LocationInfo publication independently controls generation and activation of
the SvxLink [LocationInfo] configuration.

Enable it only when the installation should publish through the configured
APRS service. It is not required merely to populate the connected reflector's
node map.

LocationInfo adds settings that are not required by node_info.json, including:

* Coordinates in SvxLink degrees-minutes-seconds format

* APRS server list

* Optional EchoLink status publication

* Signed transmitter offset in kHz

* Antenna gain in dBd

* Antenna height unit

* Beacon interval

* APRS comment

EchoLink status publication is available only when EchoLink itself is enabled.
When selected, a status-server list must also be supplied.

### Coordinate formats

The Dashboard keeps the coordinate formats required by the two publication
methods distinct.

Decimal coordinates are used for public node information. They must be signed
values within these ranges:

* Latitude: -90 to 90

* Longitude: -180 to 180

Examples:

    Latitude:  55.1809
    Longitude: -1.54604

Maidenhead locators may contain four, six or eight characters.

Example:

    IO85fe

LocationInfo additionally requires coordinates in SvxLink
degrees-minutes-seconds format. Degrees, minutes and seconds are separated by
full stops and followed immediately by a compass direction.

Example:

    Latitude:  55.10.51N
    Longitude: 01.32.45W

### Transmitter offsets

The LocationInfo transmitter offset is stored as a signed whole number of kHz.

Examples:

    Simplex:       0
    600 kHz down: -600
    600 kHz up:    600
    7.6 MHz down: -7600

The sign must describe the transmitter frequency relative to the receiver
frequency. Custom signed offsets are preserved by the configuration model.

### Publication combinations

The two controls permit four deliberate states:

* Node map disabled, LocationInfo disabled: no public node information is
  published.

* Node map enabled, LocationInfo disabled: node_info.json populates the
  connected reflector's node map.

* Node map disabled, LocationInfo enabled: LocationInfo and APRS are active,
  but node_info.json remains empty.

* Node map enabled, LocationInfo enabled: both publication methods are active.

The shared public node and RF fields are available whenever either publication
method is enabled. LocationInfo-specific fields are available only when
LocationInfo and APRS publication is enabled.

Existing saved models created before these controls were separated are
migrated automatically. Their former combined location_info.enabled choice
becomes the initial reflector node-map publication choice. Once the independent
node_info.enabled value exists, later migrations preserve the operator's
explicit selection.

## Logic and link topology

SvxLink-Dash supports single-port and multi-port installations containing `SimplexLogic`, `RepeaterLogic` and, when selected, `ReflectorLogic`.

Every enabled port has its own radio logic. The topology determines whether that logic operates independently or participates in a local or reflector link.

### Logic declaration

Every configured logic is declared in the `[GLOBAL]` section of the generated `svxlink.conf`.

Example:

```ini
[GLOBAL]
LOGICS=SimplexLogic1,RepeaterLogic2,SimplexLogic3,SimplexLogic4,ReflectorLogic
LINKS=LinkToReflector,LocalLink1
```

`LOGICS` determines which logic instances SvxLink creates.

`LINKS` identifies the link sections that join selected logic instances. Declaring a logic does not automatically connect it to another logic.

### Link membership

A link section uses `CONNECT_LOGICS` to define its exact membership.

Example reflector link:

```ini
[LinkToReflector]
CONNECT_LOGICS=SimplexLogic1:9,RepeaterLogic2:9,ReflectorLogic
DEFAULT_ACTIVE=1
TIMEOUT=300
```

In this example:

* `SimplexLogic1` participates in the reflector link.
* `RepeaterLogic2` participates in the reflector link.
* The `:9` suffix allows DTMF reflector talkgroup control.
* Other declared radio logics remain outside this link.

A declared radio logic that is not included in a link remains independently operational.

## Single-port topology

A single-port installation does not require a separate topology-selection page.

Without reflector access, its `SimplexLogic` or `RepeaterLogic` operates independently.

When reflector access is enabled, the radio logic is linked automatically to `ReflectorLogic`.

Example:

```ini
[LinkToReflector]
CONNECT_LOGICS=SimplexLogic:9,ReflectorLogic
DEFAULT_ACTIVE=1
TIMEOUT=300
```

## Multi-port topology

Every enabled port in a multi-port installation is assigned to one of these dispositions:

* Independent operation
* A named local link
* The reflector link

A local link joins two or more radio ports.

A reflector link joins one or more selected radio ports to the installation’s single `ReflectorLogic`.

For example:

```text
Ports 1 and 2 — Reflector link
Ports 3 and 4 — Local link
Ports 5, 6, 7 and 8 — Independent
```

Ports 1 and 2 share the same reflector connection and reflector talkgroup state. Ports 3 and 4 communicate through their separate local link. Ports 5 to 8 remain operational without participating in either link.

Example local link:

```ini
[LocalLink1]
CONNECT_LOGICS=SimplexLogic3,RepeaterLogic4
DEFAULT_ACTIVE=1
TIMEOUT=300
```

The operator selects the required connectivity. The dashboard generates the appropriate logic names and validates the resulting topology before configuration can be built.

## Strict port-membership rule

A radio port may belong to no more than one link.

For example, this arrangement is invalid:

```ini
[LinkToReflector]
CONNECT_LOGICS=RepeaterLogic1:9,SimplexLogic2:9,ReflectorLogic

[LocalLink1]
CONNECT_LOGICS=SimplexLogic2,RepeaterLogic3
```

`SimplexLogic2` appears in both links. That overlap would unintentionally connect the local group to the reflector group.

A port already assigned to one link must be removed from that link before it can be assigned elsewhere.

## Topology validation

Before the configuration can be built, the dashboard verifies that:

* Every enabled port has a completed radio-logic configuration.
* Every enabled port has an explicit topology disposition.
* Every link member refers to an enabled radio port or `ReflectorLogic`.
* Every local link contains at least two radio ports.
* The reflector link contains at least one radio port and `ReflectorLogic`.
* No radio port appears in more than one link.
* `ReflectorLogic` appears only in the reflector link.
* Every radio logic connected to `ReflectorLogic` receives the required `:9` suffix.
* A reflector link is not created when reflector operation is disabled.
* No more than one `ReflectorLogic` and one reflector destination are configured.

The final review identifies every enabled port as:

* Connected to the reflector
* Connected through a named local link
* Independent

## Incomplete and disabled ports

An incomplete port cannot be used to build the final configuration. The dashboard identifies its missing configuration and returns the operator to the required setup stage.

A port that was not enabled during hardware selection cannot be assigned to a link. It must first be enabled and configured through the hardware workflow because additional audio devices, GPIO preparation or device-tree changes may be required.

## Independent ports

An independent port has a valid `SimplexLogic` or `RepeaterLogic` declaration but does not appear in a link section.

It remains locally operational and retains its own radio, squelch, identification and logic settings.

Independent operation is useful when one computer supports several unrelated radio systems that do not need to exchange audio or signalling.

## Reflector topology limit

One installation supports no more than one `ReflectorLogic` and one reflector destination.

Multiple radio ports may share that reflector connection, subject to the strict port-membership rule.

Other enabled ports may operate independently or form separate local groups. Simultaneous connections to multiple independent reflectors are outside the supported configuration scope.

## Reconfiguration behaviour

Initial setup follows the complete guided sequence:

```text
Configure the installation
→ Configure reflector access and topology
→ Review
→ Build and deploy
```

When an existing setting is opened from the protected reconfiguration menu, saving it returns directly to the Build page:

```text
Runtime dashboard
→ Reconfiguration
→ Selected configuration page
→ Build
→ Deploy
```

The operator is not sent through unrelated initial-setup pages. The Build page remains the common point for reviewing, rendering and deploying the revised configuration.

## Rebuild warning

The dashboard manages generated SvxLink configuration and event files.

A Rebuild can overwrite manual changes made directly to managed files. Before rebuilding, review the proposed configuration and preserve any manual work that must remain outside dashboard management.

Specialist configuration that is not guided by the dashboard should be maintained only in documented, manually managed sections or files.

## Repository layout

The principal source directories are:

* config — example models, hardware profiles, ALSA resources, device-tree
  overlay sources and configuration data used during installation or rendering

* data — controlled application data such as regional airport, timezone and
  selection catalogues

* hw_platforms — platform-specific recognition and preparation support

* install — the Dashboard installer, service unit, permission helper and ICS
  preparation helper

* models — the default configuration model, migration-aware model structure
  and high-level validation

* renderers — conversion of the validated model into SvxLink configuration

* services — configuration storage, deployment, runtime status, hardware,
  sound, network, log, DTMF, macro and supporting operations

* templates — browser pages and reusable Jinja templates

* templates/config — templates for generated SvxLink configuration sections
  and files

* static — Dashboard stylesheets, scripts, icons and other browser assets

* tests — unit and orchestration tests for model, rendering, deployment and
  browser-workflow behaviour

* tools — administrative utilities supplied with the Dashboard

The application entry point is app.py. Project-owned paths are resolved from
the installed project root so that the Dashboard does not depend on the shell's
current working directory.


## Managed configuration and deployment

The saved node model is the Dashboard's source of truth for guided and
protected configuration. A build validates that model before rendering or
deploying configuration.

The deployment process can manage:

* /etc/svxlink/svxlink.conf

* Dashboard-generated module and logic configuration beneath
  /etc/svxlink/svxlink.d

* /etc/svxlink/node_info.json

* Required local event logic beneath /usr/share/svxlink/events.d/local

* Dashboard-generated identification sounds beneath
  /var/lib/svxlink-dash/sounds/idents

Before replacing the active SvxLink configuration, the Dashboard copies the
existing svxlink.conf and existing .conf files from svxlink.d into timestamped
files beneath /opt/dashboard/backups.

The local event files deployed by the Dashboard are generated managed output.
They are not separately backed up during each build.

A configuration-only build can render and deploy configuration without
requiring svxlink.service to become active. A normal operational build may
request a service restart after successful deployment.

The Dashboard reports build, backup, deployment and restart failures
separately. A successful render does not by itself prove that every file was
deployed or that SvxLink restarted successfully.

### Ownership of generated files

Files rendered or deployed by the Dashboard should be treated as generated
output. Manual edits to those files may be replaced during the next build.

Operator-maintained additions should be kept only in documented locations or
sections that are outside Dashboard management. Before rebuilding, preserve
any required manual changes and review the proposed configuration.

The presence of ordinary SvxLink configuration files remains intentional: the
Dashboard manages and operates standard SvxLink rather than replacing its
configuration format or service model.

## Reflector configuration and security

SvxLink-Dash V4.1 supports four distinct reflector routes:

* No reflector
* Federation Family reflector using Protocol 2
* Independent reflector using Protocol 2
* Reflector using Protocol 3 and X.509 certificates

Before configuring reflector access, confirm the required connection and authentication method with the destination reflector administrator.

## No reflector

The installation can operate without `ReflectorLogic`.

A single-port radio logic remains independently operational. Multi-port installations may contain independent ports and local port-to-port links.

No reflector connection, authentication or talkgroup-routing configuration is generated.

## Federation Family reflector

The Federation Family comprises:

* UK-Wide
* North America
* Australia
* YorkshireNet

The dashboard supplies the predefined connection information for the selected reflector, including its hostname, port, website and suggested monitoring talkgroups.

Federation Family access uses SvxReflector Protocol 2 callsign-and-password authentication.

The operator must enter the network password issued for the node callsign. This password must contain exactly 16 characters.

The 16-character requirement applies specifically to the Federation Family route. It is not a general Protocol 2 requirement.

## Independent Protocol 2 reflector

An independently operated Protocol 2 reflector uses connection information supplied by its administrator.

The operator must obtain:

* Reflector name
* Hostname or IP address
* Port number
* Authentication password
* Any recommended default or monitoring talkgroups

The password is rendered as the `AUTH_KEY` in `ReflectorLogic`.

The dashboard accepts the password specified by the reflector administrator. It does not apply the Federation Family’s 16-character password rule to an independent Protocol 2 reflector.

Protocol 2 uses a shared authentication password. It does not use the Protocol 3 certificate-request and approval process.

## Protocol 3 reflector

Protocol 3 uses X.509 client-certificate authentication rather than a shared reflector password.

The operator must obtain:

* Reflector name
* Hostname or IP address
* Port number
* Any identity information required by the reflector administrator
* Any recommended default or monitoring talkgroups

The dashboard generates the required `ReflectorLogic` certificate settings using the primary installation callsign.

SvxLink then performs the client-certificate process:

1. Create the client private key.
2. Create a Certificate Signing Request.
3. Obtain the reflector’s CA bundle.
4. Submit the certificate request to the reflector.
5. Wait for approval by the reflector administrator.
6. Retrieve the signed client certificate.
7. Authenticate to the reflector using that certificate.

The private key must remain on the node and must not be shared.

The reflector administrator must inspect and approve the pending request before the node can complete certificate authentication.

Successful Protocol 3 operation also depends on the reflector having:

* A valid root, issuing and server certificate chain
* A CA bundle containing the active root certificate
* A server certificate covering the hostname or IP address used by the client
* A working certificate-request review and approval process

The hostname or IP address entered in the dashboard must match an identity contained in the reflector’s server certificate. A certificate issued for a DNS hostname will not validate when the node connects using an unrelated IP address.

The client dashboard cannot repair or bypass an incorrectly configured reflector certificate system.

### Certificate identity and reapproval

The primary installation callsign becomes the `ReflectorLogic` callsign and the Protocol 3 client-certificate identity.

Changing that callsign changes the node’s certificate identity. A deliberate primary-callsign change may therefore require:

* A new private key and Certificate Signing Request
* A new approval by the reflector administrator
* A new signed client certificate

Changing the primary installation identity should not be treated as an ordinary cosmetic change on a Protocol 3 installation.

## Common reflector behaviour

The reflector callsign is taken from the primary installation identity. It does not need to be entered again during routine reflector setup.

Standard certificate paths, filenames and safe connection defaults are generated automatically where applicable.

Default and monitoring talkgroups remain specific to the selected reflector and installation. They may be configured after the reflector connection has been established.

In a multi-port installation, the operator selects which enabled radio ports participate in the reflector link.

Each participating radio logic is added to `CONNECT_LOGICS` with the required `:9` DTMF control suffix.

A port assigned to the reflector link cannot also belong to a local port-to-port link.

SvxLink-Dash supports one `ReflectorLogic` and one reflector destination within an installation. Multiple selected radio ports may share that connection.

## Scope limitations

The initial SvxLink-Dash V4.1 release does not provide guided configuration for:

* Browser audio streaming
* Complete RemoteTrx deployment
* NetRx or NetTx deployment
* MultiRx or MultiTx specialist deployment
* Complete RTL-SDR installation and calibration
* LADSPA filter design
* Audio compressor design
* Automatic reflector-account approval
* Automatic Protocol 3 certificate approval
* External network validation beyond safe connection checks

Relevant upstream-compatible configuration sections may remain available for manual administration.

A dashboard Rebuild can overwrite manual changes made to dashboard-managed files. Preserve specialist configuration in documented manually managed sections or files.

## Credits

SvxLink 26.05.2 is developed by Tobias Blomberg, SM0SVX.

SvxLink-Dash V4.1 is developed by Chris Jackson, G4NAB.

Additional assistance with Python, Flask, configuration rendering, testing, debugging and documentation was provided through ChatGPT by OpenAI.

## Licence

SvxLink-Dash V4.1 is free software distributed under the GNU General Public License version 3.

You may use, modify and redistribute it under the terms contained in the repository’s [`LICENSE`](LICENSE) file.

SvxLink itself is developed and licensed separately by Tobias Blomberg, SM0SVX. Files derived from or supplied by SvxLink retain their original copyright and licensing terms.