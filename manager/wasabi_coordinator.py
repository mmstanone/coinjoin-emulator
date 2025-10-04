import json
import requests
from time import sleep

class WasabiCoordinator:
    def __init__(self, host="localhost", port=37117, internal_ip="", proxy=""):
        self.host = host
        self.port = port
        self.internal_ip = internal_ip
        self.proxy = proxy

    def _get_status(self):
        """Get coordinator status"""
        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/api/v1/status",
                proxies=dict(http=self.proxy),
                timeout=5,
            )
            return response.json()
        except Exception:
            return None

    def _get_rounds(self):
        """Get active coinjoin rounds"""
        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/api/v1/rounds",
                proxies=dict(http=self.proxy),
                timeout=5,
            )
            return response.json()
        except Exception:
            return None

    def wait_ready(self):
        """Wait for coordinator to be ready"""
        print("Waiting for coordinator to be ready...")
        while True:
            try:
                status = self._get_status()
                if status:
                    print(f"Coordinator ready: {status}")
                    break
            except:
                pass
            sleep(0.1)
