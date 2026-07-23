# OctoPrint Light Control - TPLink
Adds TP-Link smart plug support to
[OctoPrint-LightControl](https://github.com/arbeaman/OctoPrint-LightControl)
as a sub-plugin. It talks to the plug directly over the local network using TP-Link's legacy
protocol (TCP port 9999) — no external dependencies and no cloud account required.

## Supported plugs
Works with TP-Link **Kasa** smart plugs and power strips that speak the original (legacy)
local protocol on TCP port 9999 — the same device family supported by
[OctoPrint-PSUControl-TPLink](https://github.com/kantlivelong/OctoPrint-PSUControl-TPLink).

- **Single-outlet plugs** — leave *Plug* set to `0`. Examples: HS100, HS103, HS105, HS110,
  KP105, KP115, KP125, KP401.
- **Multi-outlet plugs / power strips** — set *Plug* to the outlet number (`1`, `2`, `3`, …).
  Examples: HS107, EP40, HS300, KP200, KP303, KP400.

Not supported:
- **Tapo** devices, and any plug that only exposes TP-Link's newer encrypted **KLAP** protocol.
- Some recent hardware revisions / firmware of the models above have switched to KLAP; if a
  device stops responding on port 9999 after a firmware update, it is no longer compatible.

## Setup
- Install [OctoPrint-LightControl](https://github.com/arbeaman/OctoPrint-LightControl) first.
- Install this plugin using the Plugin Manager from Settings.
- Configure this plugin with your smart plug's hostname or IP address, and the outlet number
  if it is a multi-outlet strip.
- Select this plugin as the Switching and Sensing method in Light Control.

## Support
Help can be found at the [OctoPrint Community Forums](https://community.octoprint.org)

## Credits
Based on [OctoPrint-PSUControl-TPLink](https://github.com/kantlivelong/OctoPrint-PSUControl-TPLink) by Shawn Bruce (kantlivelong), used under the AGPLv3.
