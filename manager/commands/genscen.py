import argparse
import json
import os
import sys
import numpy.random
import copy
import random
from dataclasses import dataclass, field
import dataclasses
from typing import List, Optional


@dataclass
class BackendConfig:
    MaxInputCountByRound: int = 400
    MinInputCountByRoundMultiplier: float = 0.01
    StandardInputRegistrationTimeout: str = "0d 0h 20m 0s"
    ConnectionConfirmationTimeout: str = "0d 0h 6m 0s"
    OutputRegistrationTimeout: str = "0d 0h 6m 0s"
    TransactionSigningTimeout: str = "0d 0h 6m 0s"
    FailFastTransactionSigningTimeout: str = "0d 0h 6m 0s"
    RoundExpiryTimeout: str = "0d 0h 10m 0s"


@dataclass
class WalletConfig:
    funds: List[int] = field(default_factory=list)
    anon_score_target: Optional[int] = None
    redcoin_isolation: Optional[bool] = None
    skip_rounds: Optional[List[int]] = None
    version: Optional[str] = None
    delay_blocks: int = 0
    delay_rounds: int = 0
    stop_blocks: int = 0
    stop_rounds: int = 0


@dataclass
class Scenario:
    name: str = "template"
    rounds: int = 0
    blocks: int = 0
    backend: BackendConfig = field(default_factory=BackendConfig)
    wallets: List[WalletConfig] = field(default_factory=list)
    distributor_version: Optional[str] = None
    default_version: str = "2.0.4"
    default_anon_score_target: Optional[int] = None
    default_redcoin_isolation: Optional[bool] = None


SCENARIO_TEMPLATE = Scenario()


def setup_parser(parser: argparse.ArgumentParser):
    parser.add_argument("--name", type=str, help="scenario name")
    parser.add_argument("--client-count", type=int, default=10, help="number of wallets")
    parser.add_argument("--type", type=str, default="static", help="scenario type")
    parser.add_argument(
        "--distribution",
        type=str,
        default="lognorm",
        help="fund distribution strategy",
    )
    parser.add_argument("--utxo-count", type=int, default=30, help="number of UTXOs per wallet")
    parser.add_argument(
        "--max-coinjoin",
        type=int,
        default=400,
        help="maximal number of inputs to a coinjoin",
    )
    parser.add_argument(
        "--min-coinjoin",
        type=int,
        default=4,
        help="minimal number of inputs to a coinjoin",
    )
    parser.add_argument(
        "--stop-round",
        type=int,
        default=0,
        help="terminate after N coinjoin rounds, 0 for no limit",
    )
    parser.add_argument(
        "--stop-block",
        type=int,
        default=0,
        help="terminate after N blocks, 0 for no limit",
    )
    parser.add_argument(
        "--skip-rounds",
        type=str,
        required=False,
        help="skip rounds ('random[fraction]' for randomly sampled fraction of rounds, or comma-separated list of rounds to skip)",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    parser.add_argument("--out-dir", type=str, default="scenarios", help="output directory")
    parser.add_argument(
        "--distributor-version",
        type=str,
        required=False,
        help="version of the distibutor wallet",
    )
    parser.add_argument(
        "--client-version",
        type=str,
        required=False,
        help="version of the client wallet",
    )
    parser.add_argument(
        "--anon-score-target",
        type=int,
        required=False,
        help="default anon score target used for wallets",
    )
    parser.add_argument(
        "--redcoin-isolation",
        type=bool,
        required=False,
        help="default redcoin isolation setting used for wallets",
    )


def format_name(args):
    if args.name:
        return args.name
    if args.type == "static":
        return f"{args.distribution}-{args.type}-{args.client_count}-{args.utxo_count}utxo"
    if args.type == "default":
        return f"{args.distribution}-{args.type}-{args.client_count}"
    if args.type == "overmixing":
        return f"{args.distribution}-{args.type}-{args.client_count}"
    if args.type == "delayed":
        return f"{args.distribution}-{args.type}-{args.client_count}"
    if args.type == "delayed-overmixing":
        return f"{args.distribution}-{args.type}-{args.client_count}"


def prepare_skip_rounds(args):
    if not args.skip_rounds:
        return None
    if args.skip_rounds.startswith("random"):
        if args.stop_round == 0:
            print("- cannot use random skip rounds with no stop round")
            sys.exit(1)

        fraction = 2 / 3
        if args.skip_rounds != "random":
            try:
                fraction = float(args.skip_rounds.split("[")[1].split("]")[0])
            except IndexError:
                print("- random skip rounds fraction parsing failed")
                sys.exit(1)
        print(f"- skipping {fraction * 100:.2f}% of rounds")

        return lambda _: sorted(
            map(
                int,
                numpy.random.choice(
                    range(0, args.stop_round),
                    size=int(args.stop_round * fraction),
                    replace=False,
                ),
            )
        )
    else:
        try:
            return lambda idx: (sorted(map(int, args.skip_rounds.split(","))) if idx < args.client_count // 2 else [])
        except ValueError:
            print("- invalid skip rounds list")
            sys.exit(1)


def prepare_distribution(distribution):
    dist_name = distribution.split("[")[0]
    dist_params = None
    if "[" in distribution:
        dist_params = map(float, distribution.split("[")[1].split("]")[0].split(","))

    match dist_name:
        case "uniform":
            dist_params = dist_params or [0.0, 10_000_000.0]
            return lambda x: map(round, numpy.random.uniform(*dist_params, x))
        case "pareto":
            dist_params = dist_params or [1.16]
            return lambda x: map(round, numpy.random.pareto(*dist_params, x) * 1_000_000)
        case "lognorm":
            # parameters estimated from mainnet data of Wasabi 2.0 coinjoins
            dist_params = dist_params or [14.1, 2.29]
            return lambda x: map(round, numpy.random.lognormal(*dist_params, x))
        case _:
            return None


def prepare_wallet(args, idx, distribution, skip_rounds):
    wallet = WalletConfig()

    if args.type == "default":
        wallet.funds = list(distribution(random.randint(1, 10)))
        if idx < args.client_count // 5:
            wallet.anon_score_target = random.randint(27, 75)
            wallet.redcoin_isolation = True
        else:
            wallet.anon_score_target = 5
    elif args.type == "overmixing":
        wallet.funds = list(distribution(random.randint(1, 10)))
        if idx < args.client_count // 10:
            wallet.anon_score_target = 1_000_000
        elif idx < args.client_count // 5:
            wallet.anon_score_target = random.randint(27, 75)
            wallet.redcoin_isolation = True
        else:
            wallet.anon_score_target = 5
    elif args.type == "delayed":
        wallet.funds = list(distribution(random.randint(1, 10)))
        wallet.skip_rounds = list(range(random.randint(1, 5)))
        if idx < args.client_count // 5:
            wallet.anon_score_target = random.randint(27, 75)
            wallet.redcoin_isolation = True
        else:
            wallet.anon_score_target = 5
    elif args.type == "delayed-overmixing":
        wallet.funds = list(distribution(random.randint(1, 10)))
        if idx < args.client_count // 10:
            wallet.anon_score_target = 1_000_000
        elif idx < args.client_count // 5:
            wallet.skip_rounds = list(range(random.randint(1, 5)))
            wallet.anon_score_target = random.randint(27, 75)
            wallet.redcoin_isolation = True
        else:
            wallet.skip_rounds = list(range(random.randint(1, 5)))
            wallet.anon_score_target = 5
    else:
        wallet.funds = list(distribution(args.utxo_count))

    if skip_rounds:
        wallet.skip_rounds = skip_rounds(idx)

    return wallet


def handler(args):
    print("Generating scenario...")
    scenario = copy.deepcopy(SCENARIO_TEMPLATE)
    scenario.name = format_name(args)

    scenario.backend.MaxInputCountByRound = args.max_coinjoin
    scenario.backend.MinInputCountByRoundMultiplier = args.min_coinjoin / args.max_coinjoin
    scenario.rounds = args.stop_round
    scenario.blocks = args.stop_block

    if args.distributor_version:
        scenario.distributor_version = args.distributor_version

    if args.client_version:
        scenario.default_version = args.client_version

    if args.anon_score_target:
        scenario.default_anon_score_target = args.anon_score_target

    if args.redcoin_isolation:
        scenario.default_redcoin_isolation = args.redcoin_isolation

    distribution = prepare_distribution(args.distribution)
    if not distribution:
        print("- invalid distribution")
        sys.exit(1)

    skip_rounds = prepare_skip_rounds(args)

    for idx in range(args.client_count):
        scenario.wallets.append(prepare_wallet(args, idx, distribution, skip_rounds))

    print(f"- requires {(sum(map(lambda x: sum(x.funds), scenario.wallets)) / 100_000_000):0.8f} BTC")

    os.makedirs(args.out_dir, exist_ok=True)
    if os.path.exists(f"{args.out_dir}/{scenario.name}.json") and not args.force:
        print(f"- file {args.out_dir}/{scenario.name}.json already exists")
        sys.exit(1)

    with open(f"{args.out_dir}/{scenario.name}.json", "w") as f:
        json.dump(dataclasses.asdict(scenario), f, indent=2)

    print(f"- saved to {args.out_dir}/{scenario.name}.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a scenario file")
    setup_parser(parser)
    handler(parser.parse_args())
