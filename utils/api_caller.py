import json
import requests as re
from requests.exceptions import ConnectionError, Timeout
from logging import getLogger
from requests.auth import HTTPBasicAuth
from rich import print_json
from requests.packages.urllib3.exceptions import InsecureRequestWarning  # type: ignore

re.packages.urllib3.disable_warnings(InsecureRequestWarning)

_logger = getLogger(__name__)

basic_auth = HTTPBasicAuth(username="NMGPOSMAPP", password="Welcome1234")
# basic_auth = HTTPBasicAuth(username="NMGPOSMAPP", password="Welcome1nmg1")


class RequestSender:
    """Responsible for sending the payload to the remote Oracle Database"""

    def __init__(self, url, payload, session=None):
        self.url = url
        self.payload = payload
        self.session: re.Session = session
        self.headers = {"Content-Type": "application/json", "Accept": "*/*", "User-Agent": "WalPOSCron/16.0.1"}

    def post(self):
        """Send the data to the remote system with Object Confs"""
        try:
            if self.session:
                resp = self.session.post(self.url, json=self.payload, auth=basic_auth, verify=False, headers=self.headers)
            else:
                resp = re.post(self.url, json=self.payload, auth=basic_auth, verify=False, headers=self.headers)
            _logger.info(f"Got Response From Oracle {resp}")
            print("---------- Oracle Payload ----------")
            print_json(json.dumps(self.payload))
            print("---------- Oracle Response ----------")
            print_json(json.dumps(resp.json()))
            if resp.status_code != 200:
                _logger.error(f"Failed to Post on Oracle server with msg={resp.json()!r}")
            _logger.info("Posted Successfully")
            return resp.json()
        except ConnectionError as exc:
            _logger.error("Error While Connecting to Oracle Rest API Service !!!")
            _logger.exception(exc)
            return False
        except Timeout as exc:
            _logger.error("The request timed out while trying to connect to the remote server !!!")
            _logger.exception(exc)
            return False

    def get(self):
        try:
            if self.session:
                resp = self.session.get(self.url, auth=basic_auth, verify=False, headers=self.headers)
            else:
                resp = re.get(self.url, auth=basic_auth, verify=False, headers=self.headers)
            _logger.info(f"Got Response From Oracle {resp}")
            print("---------- Oracle Response ----------")
            print_json(json.dumps(resp.json()))
            if resp.status_code != 200:
                _logger.error(f"Failed to Post on Oracle server with msg={resp.json()!r}")
            _logger.info("Posted Successfully")
            return resp.json()
        except ConnectionError as exc:
            _logger.error("Error While Connecting to Oracle Rest API Service !!!")
            _logger.exception(exc)
            return False
        except Timeout as exc:
            _logger.error("The request timed out while trying to connect to the remote server !!!")
            _logger.exception(exc)
            return False
