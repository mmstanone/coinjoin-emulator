from .wasabi_client_base import WasabiClientBase


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
