#!/usr/bin/python3

from inspect import signature
import requests
import json
import argparse
import sys

class SonyRemote:
	"""https://pro-bravia.sony.net/develop/integrate/rest-api/spec/index.html"""
	def __init__(self, ip, password, version="1.0"):
		self._ip = ip
		self._url = "sony"
		self._base_data = {"id": 1, "version": version}
		self._session = requests.Session()
		self._session.headers = {"Content-Type":"application/json", "X-Auth-PSK": password}

	def _build_request(self, method, path, version=None, **kwargs):
		base = self._base_data
		if version:
			base['version'] = version
		res = self._session.post(
			f"http://{self._ip}/{self._url}/{path}",
			data=json.dumps({"method": method, "params": [kwargs], **base}))
		return json.loads(res.content.decode())

	def power(self, status=str):
		"""Change the current power status of the device.

  status | Power state to set the device to.
    active  - indicates the power on state.
    standby - indicates the power off state."""
		if status == 'active': status = True
		elif status == 'standby': status = False
		else:
			return {"error":[3, "Illegal Argument"]}
		return self._build_request("setPowerStatus", "system", status=status)
			
	def volume(self, volume=str, ui="on", target=""):
		"""Change the audio volume level.

  volume | Volume level to set. The following formats are applied.
    "N"  - N is a numeric string (ex. "25"). The volume is set to level N.
    "+N" - N is a numeric string (ex. "+14"). The volume is increased by an increment of N.
    "-N" - N is a numeric string (ex. "-10"). The volume is reduced by an increment of N.
		
  target | Output target of the sound. The following values are defined.
    default     - outputs sound to all output equipment of the device
    "speaker"   - outputs sound to the speaker(s)
    "headphone" - outputs sound to the headphones

  ui -If the UI (volume bar, etc.) should be displayed, set this "on".
    "on"  - UI is displayed. (default)
    "off" - UI is not displayed."""
		return self._build_request("setAudioVolume", "audio", version="1.2", volume=volume, ui=ui, target=target)

	def app(self, uri=str):
		"""Launch an application.

  uri | URI of target application.
    "localapp://webappruntime?url=target_url" - launch target_url.
    "localapp://webappruntime?manifest=manifest_url" - launch an application in manifest_url.
    "localapp://webappruntime?auid=application_unique_id" - launch the application in auid=application_unique_id in the USB storage."""
		return self._build_request("setActiveApp", "appControl", uri=uri)

	def reboot(self):
		"""Performs a full reboot"""
		return self._build_request("requestReboot", "system")

	def screen_mirror(self):
		"""Launch screen mirroring application"""
		return self._build_request("setPlayContent", "avContent", uri="extInput:widi?port=1")

	def list_apps(self):
		"""List of applications that can be launched."""
		return self._build_request("getApplicationList", "appControl")

	def list_inputs(self):
		"""Get current status of all external input sources of the device."""
		return self._build_request("getCurrentExternalInputsStatus", "avContent", version='1.1')



class ArgParser:
	def __init__(self):
		self.parser = argparse.ArgumentParser(description='Sony TV Remote')
		self.sub_parser = None

	def command(self, commands):
		self.parser.add_argument('command', type=str, choices=commands, help='Subcommand to run')
		return self.parser.parse_args(sys.argv[1:2]).command

	def sub_command(self, func):
		self.sub_parser = argparse.ArgumentParser(description=func.__doc__, formatter_class=argparse.RawTextHelpFormatter)
		for param in list(signature(func).parameters.values()):
			if not isinstance(param.default, type):
				self.sub_parser.add_argument(param.name, nargs='?', default=param.default, type=type(param.default))
				continue
			self.sub_parser.add_argument(param.name, type=param.default)
		
		args = self.sub_parser.parse_args(sys.argv[2:])
		return dict(args._get_kwargs())

if __name__ == "__main__":
	remote = SonyRemote("192.168.115.144", "1234", version="1.0")
	argparser = ArgParser()

	cmd_list = filter(lambda n:not n.startswith('_'), dir(remote))
	cmd_list = map(lambda c:c.replace('_','-'), cmd_list)

	command = argparser.command(list(cmd_list))
	action = getattr(remote, command.replace('-','_'))
	args = argparser.sub_command(action)
	response = action(**args)

	if 'error' in response:
		print(f"{response['error'][1]} | {args}\n")
		if response['error'][0] == 3: argparser.sub_parser.print_help()
		if response['error'][0] == 12: print("No Such Method (Check version)")
		if response['error'][0] == 14: print("Unsupported Version")
		exit(1)
	
	elif 'result' in response and response['result'] and response['result'][0]:
		results = response['result']
		if type(response['result'][0]) is list and len(response['result']) == 1:
			results = response['result'][0]
		for result in results:
			print(json.dumps(result, indent=4).replace('{','').replace('}',''))
	
	elif 'result' not in response:
		print(response)



