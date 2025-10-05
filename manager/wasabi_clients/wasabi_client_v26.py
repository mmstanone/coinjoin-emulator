from time import time, sleep
from traceback import print_exception
from .wasabi_client_base import WALLET_NAME, WasabiClientBase


class WasabiClientV26(WasabiClientBase):

    def __init__(
        self,
        host="localhost",
        port=37128,
        name="wasabi-client",
        proxy="",
        version="2.6.0",
        delay=(0, 0),
        stop=(0, 0),
    ):
        super().__init__(host, port, name, proxy, version, delay, stop)

    def select(self, timeout=5, repeat=10):
        request = {"method": "selectwallet", "params": [WALLET_NAME]}
        self._rpc(request, False, timeout=timeout, repeat=repeat)

    def wait_wallet(self, timeout=None):
        start = time()
        while timeout is None or time() - start < timeout:
            try:
                self._create_wallet()
            except Exception as e:
                print_exception(e)

            try:
                self.select(timeout=5)
                self.get_balance(timeout=5)
                return True
            except Exception as e:
                print_exception(e)

            sleep(1)
        return False
