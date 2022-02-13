#!/usr/bin/python3

from inspect import signature, isfunction
from argparse import ArgumentParser, RawTextHelpFormatter
import requests
import json
import sys

class SonyRemote:
	"""https://pro-bravia.sony.net/develop/integrate/rest-api/spec/index.html"""
	def __init__(self, host, psk, version="1.0"):
		self._ip = host
		self._url = "sony"
		self._base_data = {"id": 1, "version": version}
		self._session = requests.Session()
		self._session.headers = {"Content-Type":"application/json", "X-Auth-PSK": psk}

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

	def check_power(self):
		"""Provides the current power status of the device."""
		return self._build_request("getPowerStatus", "system")


class ArgParser(ArgumentParser):
	def __init__(self):
		super().__init__(description='Sony TV Remote', formatter_class=RawTextHelpFormatter)
		self.add_argument("--host", default="192.168.1.100", help="IP address of the TV")
		self.add_argument("--psk", default='1234', help="Pre-Shared Key used for authentication")
		self.sub_parsers = self.add_subparsers(parser_class=ArgumentParser)

	def add_command(self, command, func):
		sub_parser = self.sub_parsers.add_parser(command, description=func.__doc__, help=func.__doc__.split('\n')[0], formatter_class=RawTextHelpFormatter)
		sub_parser.set_defaults(func=func)
		params = list(signature(func).parameters.values())
		if isfunction(func) and len(params) > 0 and params[0].name == 'self': params.pop(0)
		for param in params:
			if not isinstance(param.default, type):
				sub_parser.add_argument(param.name, nargs='?', default=param.default, type=type(param.default))
				continue
			sub_parser.add_argument(param.name, type=param.default)

if __name__ == "__main__":
	argparser = ArgParser()

	command_list = filter(lambda n:not n.startswith('_'), dir(SonyRemote))
	for command in command_list:
		argparser.add_command(command.replace('_','-'), getattr(SonyRemote, command))
	
	args = argparser.parse_args().__dict__
	if 'func' not in args: 
		argparser.print_help()
		exit(1)

	host = args.pop('host')
	psk = args.pop('psk')
	remote = SonyRemote(host, psk, version="1.0")
	command = getattr(remote, args.pop('func').__name__)
	response = command(**args)

	if 'error' in response:
		print(f"{response['error'][1]} | {args}\n")
		if response['error'][0] == 3: argparser.print_help()
		if response['error'][0] == 12: print("No Such Method (Check version)")
		if response['error'][0] == 14: print("Unsupported Version")
		exit(1)
	
	elif 'result' in response and response['result'] and response['result'][0]:
		results = response['result']
		if type(response['result'][0]) is list and len(response['result']) == 1:
			results = response['result'][0]
		for result in results:
			print(json.dumps(result, indent=2).replace('"','').replace('{','').replace('}',''))
	
	elif 'result' not in response:
		print(response)



