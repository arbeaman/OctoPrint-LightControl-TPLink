__author__ = "Alerick Beaman <35195829+arbeaman@users.noreply.github.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2026 Alerick Beaman - Released under terms of the AGPLv3 License"
# Sub-plugin that switches the printer lights through a TP-Link Kasa smart plug over the local
# network, using TP-Link's legacy protocol on TCP port 9999. Registers with Light Control as a
# switching and sensing method.

import json
import socket
import struct
from struct import unpack

import octoprint.plugin

class LightControl_TPLink(octoprint.plugin.StartupPlugin,
                        octoprint.plugin.RestartNeedingPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.SettingsPlugin):
    """Sub-plugin that drives the printer lights through a TP-Link Kasa smart plug."""

    def __init__(self):
        """Initialize the in-memory configuration store."""
        self.config = dict()


    def get_settings_defaults(self):
        """Define the plug address and outlet-index settings and their defaults."""
        return dict(
            address = '',
            plug = 0
        )


    def on_settings_initialized(self):
        """Load stored settings into memory."""
        self.reload_settings()


    def reload_settings(self):
        """Copy stored settings into the in-memory config."""
        for k, v in self.get_settings_defaults().items():
            if isinstance(v, str):
                v = self._settings.get([k])
            elif isinstance(v, bool):
                v = self._settings.get_boolean([k])
            elif isinstance(v, int):
                v = self._settings.get_int([k])
            elif isinstance(v, float):
                v = self._settings.get_float([k])

            self.config[k] = v
            self._logger.debug("{}: {}".format(k, v))


    def on_startup(self, host, port):
        """Register this sub-plugin with the main plugin so it can be used for switching and sensing."""
        lightcontrol_helpers = self._plugin_manager.get_helpers("lightcontrol")
        if not lightcontrol_helpers or 'register_plugin' not in lightcontrol_helpers.keys():
            self._logger.warning("The version of LightControl that is installed does not support plugin registration.")
            return

        self._logger.debug("Registering plugin with LightControl")
        lightcontrol_helpers['register_plugin'](self)


    def get_sysinfo(self):
        """Query the plug for its system information."""
        cmd = dict(system=dict(get_sysinfo=dict()))
        result = self.send(cmd)

        try:           
            return result['system']['get_sysinfo']
        except (TypeError, KeyError):
            self._logger.error("Expecting get_sysinfo, got result={}".format(result))
            return dict()


    def change_light_state(self, state):
        """Set the relay state, targeting the selected outlet on multi-outlet power strips."""
        cmd = dict(system=dict(set_relay_state=dict(state=state)))

        if self.config['plug'] > 0:
            sysinfo = self.get_sysinfo()
            
            if not sysinfo:
                return

            try:
                device_id = sysinfo['children'][self.config['plug']-1]['id']
            except KeyError:
                self._logger.error("Expecting id for child index {}, got sysinfo={}".format(self.config['plug']-1, sysinfo))
                return

            # Address the selected outlet on a multi-outlet power strip.
            cmd.update(dict(context=dict(child_ids=[device_id])))

        self.send(cmd)


    def turn_light_on(self):
        """Switch the plug on."""
        self._logger.debug("Switching Light On")
        self.change_light_state(1)


    def turn_light_off(self):
        """Switch the plug off."""
        self._logger.debug("Switching Light Off")
        self.change_light_state(0)


    def get_light_state(self):
        """Return whether the plug, or the selected outlet, is currently on."""
        self._logger.debug("get_light_state")
        sysinfo = self.get_sysinfo()

        if not sysinfo:
            return False

        result = False

        if self.config['plug'] > 0:
            try:
                result = bool(sysinfo['children'][self.config['plug']-1]['state'])
            except KeyError:
                self._logger.error("Expecting state for child index {}, got sysinfo={}".format(self.config['plug']-1, sysinfo))
        else:
            try:
                result = bool(sysinfo['relay_state'])
            except KeyError:
                self._logger.error("Expecting relay_state, got sysinfo={}".format(sysinfo))

        return result


    def encrypt(self, string):
        """Encode a command with TP-Link's legacy autokey (XOR) cipher and a length header."""
        key = 171
        result = b"\0\0\0" + bytes([len(string)])
        for i in bytes(string.encode('latin-1')):
            a = key ^ i
            key = a
            result += bytes([a])
        return result


    def decrypt(self, string):
        """Decode a TP-Link legacy autokey (XOR) response payload."""
        key = 171
        result = b""
        for i in bytes(string):
            a = key ^ i
            key = i
            result += bytes([a])
        return result.decode('latin-1')


    def send(self, cmd):
        """Send an encrypted command to the plug over TCP port 9999 and return the decoded response."""
        self._logger.debug("send={}".format(cmd))
        cmd_json = json.dumps(cmd)

        result = dict()

        try:
            host = socket.gethostbyname(self.config['address'])
        except Exception:
            self._logger.error("Unable to resolve hostname {}".format(self.config['address']))
            return result

        port = 9999

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bound network operations so an unresponsive plug can't block the polling thread.
        s.settimeout(5)
        try:
            s.connect((host, port))
        except (OSError, ConnectionRefusedError) as e:
            self._logger.error("Unable to connect to {}:{} - {}".format(host, port, e.strerror))
            return result

        try:
            s.send(self.encrypt(cmd_json))
        except socket.error as e:
            self._logger.error("Error sending data - {}".format(e.strerror))
            return result

        try:
            data = s.recv(1024)
            len_data = unpack('>I', data[0:4])
            while (len(data) - 4) < len_data[0]:
                data = data + s.recv(1024)
        except socket.timeout as e:
            self._logger.error("Error receiving data - {}".format(e))
            return result
        except struct.error:
            self._logger.error("Error invalid data received")
            return result

        s.close()

        result = json.loads(self.decrypt(data[4:]))
        self._logger.debug("recv={}".format(result))

        return result

    def on_settings_save(self, data):
        """Persist settings and reload them into memory."""
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.reload_settings()


    def get_settings_version(self):
        """Return the settings schema version."""
        return 1


    def on_settings_migrate(self, target, current=None):
        """Placeholder for future settings migrations."""
        pass


    def is_template_autoescaped(self):
        """Enable Jinja autoescaping for the plugin's template."""
        return True


    def get_template_configs(self):
        """Declare the settings template."""
        return [
            dict(type="settings", custom_bindings=False)
        ]


    def get_update_information(self):
        """Provide Software Update plugin metadata for GitHub release checks."""
        return dict(
            lightcontrol_tplink=dict(
                displayName="Light Control - TPLink",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="arbeaman",
                repo="OctoPrint-LightControl-TPLink",
                current=self._plugin_version,

                # update method: pip w/ dependency links
                pip="https://github.com/arbeaman/OctoPrint-LightControl-TPLink/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "Light Control - TPLink"
__plugin_pythoncompat__ = ">=3,<4"

def __plugin_load__():
    """Instantiate the sub-plugin and register its Software Update hook."""
    global __plugin_implementation__
    __plugin_implementation__ = LightControl_TPLink()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
