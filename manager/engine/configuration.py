import enum
from dataclasses import dataclass


@dataclass
class WasabiConfig:
    anon_score_target: int | None
    redcoin_isolation: bool | None
    skip_rounds: list[int]


class JoinmarketParticipantType(enum.StrEnum):
    maker = enum.auto()
    taker = enum.auto()


@dataclass
class JoinmarketConfig:
    type: JoinmarketParticipantType


@dataclass
class Wallet:
    funds: list[int]
    delay_blocks: int
    stop_blocks: int
    wasabi_config: WasabiConfig | None
    joinmarket_config: JoinmarketConfig | None


@dataclass
class Scenario:
    name: str
    rounds: int
    blocks: int
    default_version: str
    wallets: list[Wallet]
