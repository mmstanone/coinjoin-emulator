from manager.btc_node import BtcNode
from manager.wasabi_backend import WasabiBackend
from manager.wasabi_clients import WasabiClient
from manager import utils
import manager.commands.genscen
from time import sleep, time
import sys
import random
import os
import datetime
import json
import argparse
import shutil
import tempfile
import multiprocessing
import multiprocessing.pool
import math

from manager.wasabi_clients.joinmarket_client import JoinMarketClientServer

DISTRIBUTOR_UTXOS = 20
BATCH_SIZE = 5
BTC = 100_000_000
SCENARIO = {
    "name": "default",
    "rounds": 10,  # the number of coinjoins after which the simulation stops (0 for no limit)
    "blocks": 0,  # the number of mined blocks after which the simulation stops (0 for no limit)
    "default_version": "2.0.4",
    "wallets": [
        {"funds": [200000, 50000], "anon_score_target": 7},
        {"funds": [3000000], "redcoin_isolation": True},
        {"funds": [1000000, 500000], "skip_rounds": [0, 1, 2]},
        {"funds": [3000000, 15000]},
        {"funds": [1000000, 500000]},
        {"funds": [3000000, 600000]},
    ],
}

args = None
driver = None
node = None
coordinator = None
distributor = None
clients = []
versions = set()
invoices = {}

current_round = 0
current_block = 0


def prepare_image(name, path=None):
    prefixed_name = args.image_prefix + name
    if driver.has_image(prefixed_name):
        if args.force_rebuild:
            if args.image_prefix:
                driver.pull(prefixed_name)
                print(f"- image pulled {prefixed_name}")
            else:
                driver.build(name, f"./containers/{name}" if path is None else path)
                print(f"- image rebuilt {prefixed_name}")
        else:
            print(f"- image reused {prefixed_name}")
    elif args.image_prefix:
        driver.pull(prefixed_name)
        print(f"- image pulled {prefixed_name}")
    else:
        driver.build(name, f"./containers/{name}" if path is None else path)
        print(f"- image built {prefixed_name}")


def prepare_images():
    print("Preparing images")
    prepare_image("btc-node")
    prepare_image("joinmarket-client-server")
    # prepare_image("tor-socks-proxy")
    # prepare_image("irc-server")
    # prepare_client_images()


def start_infrastructure():
    print("Starting infrastructure")
    btc_node_ip, btc_node_ports = driver.run(
        "btc-node",
        f"{args.image_prefix}btc-node",
        ports={18443: 18443, 18444: 18444},
        cpu=4.0,
        memory=8192,
    )
    global node
    node = BtcNode(
        host=btc_node_ip if args.proxy else args.control_ip,
        port=18443 if args.proxy else btc_node_ports[18443],
        internal_ip=btc_node_ip,
        proxy=args.proxy,
    )
    node.wait_ready()
    print("- started btc-node")
    node.create_wallet("jm_wallet")

    # TODO: Initiate TOR
    # TODO: Initiate IRC



def fund_distributor(btc_amount):
    print("Funding distributor")
    for _ in range(DISTRIBUTOR_UTXOS):
        node.fund_address(
            distributor.get_new_address(),
            math.ceil(btc_amount * BTC / DISTRIBUTOR_UTXOS) // BTC,
        )
    while (balance := distributor.get_balance()) < btc_amount * BTC:
        sleep(1)
    print(f"- funded (current balance {balance / BTC:.8f} BTC)")


def init_joinmarket_clientserver(name, port, host="localhost"):
    return JoinMarketClientServer(name=name, port=port)


def start_client(idx: int):
    name = f"joinmarket-client-server-{idx:03}"
    port = 28184 + idx
    try:
        ip, manager_ports = driver.run(
            name,
            "joinmarket-client-server:latest",
            env={},
            ports={28183: port},
            cpu=(0.1),
            memory=(768),
        )
    except Exception as e:
        print(f"- could not start {name} ({e})")
        return None

    print(f"driver starting {name}")

    client = init_joinmarket_clientserver(name=name,
                                          port=port)
    return client
    # start = time()
    # # if not client.wait_wallet(timeout=60):
    # if not client.wait_ready():
    #     print(
    #         f"- could not start {name} (application timeout {time() - start} seconds)"
    #     )
    #     return None
    # print(f"- started {client.name} (wait took {time() - start} seconds)")


def start_clients(wallets):
    print("Starting clients")
    with multiprocessing.pool.ThreadPool() as pool:
        new_clients = pool.starmap(start_client, enumerate(wallets, start=len(clients)))

        for _ in range(3):
            restart_idx = list(
                map(
                    lambda x: x[0],
                    filter(
                        lambda x: x[1] is None,
                        enumerate(new_clients, start=len(clients)),
                    ),
                )
            )

            if not restart_idx:
                break
            print(f"- failed to start {len(restart_idx)} clients; retrying ...")
            for idx in restart_idx:
                driver.stop(f"wasabi-client-{idx:03}")
            sleep(60)
            restarted_clients = pool.starmap(
                start_client,
                ((idx, wallets[idx - len(clients)]) for idx in restart_idx),
            )
            for idx, client in enumerate(restarted_clients):
                if client is not None:
                    new_clients[restart_idx[idx]] = client
        else:
            new_clients = list(filter(lambda x: x is not None, new_clients))
            print(
                f"- failed to start {len(wallets) - len(new_clients)} clients; continuing ..."
            )
    clients.extend(new_clients)


def run():
    try:
        print(f"=== Scenario {SCENARIO['name']} ===")
        prepare_images()
        start_infrastructure()
        fund_distributor(1000)
        start_clients(SCENARIO["wallets"])
        # prepare_invoices(SCENARIO["wallets"])

        print("Running simulation")
    except KeyboardInterrupt:
        print()
        print("KeyboardInterrupt received")
    except Exception as e:
        print(f"Terminating exception: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run coinjoin simulation setup")
    subparsers = parser.add_subparsers(dest="command", title="command")

    parser.add_argument(
        "--driver",
        type=str,
        choices=["docker", "podman", "kubernetes"],
        default="docker",
    )
    parser.add_argument("--no-logs", action="store_true", default=False)

    console_subparser = subparsers.add_parser("console", help="run console")
    console_subparser.add_argument(
        "--force-rebuild", action="store_true", help="force rebuild of images"
    )
    console_subparser.add_argument("--namespace", type=str, default="coinjoin")
    console_subparser.add_argument(
        "--image-prefix", type=str, default="", help="image prefix"
    )
    console_subparser.add_argument("--proxy", type=str, default="")
    console_subparser.add_argument(
        "--btc-node-ip", type=str, help="override btc-node ip", default=""
    )
    console_subparser.add_argument(
        "--control-ip", type=str, help="control ip", default="localhost"
    )
    console_subparser.add_argument("--reuse-namespace", action="store_true", default=False)



    build_subparser = subparsers.add_parser("build", help="build images")
    build_subparser.add_argument(
        "--force-rebuild", action="store_true", help="force rebuild of images"
    )
    build_subparser.add_argument("--namespace", type=str, default="coinjoin")
    build_subparser.add_argument(
        "--image-prefix", type=str, default="", help="image prefix"
    )

    run_subparser = subparsers.add_parser("run", help="run simulation")
    run_subparser.add_argument(
        "--force-rebuild", action="store_true", help="force rebuild of images"
    )
    run_subparser.add_argument(
        "--image-prefix", type=str, default="", help="image prefix"
    )
    run_subparser.add_argument(
        "--scenario", type=str, help="scenario specification file"
    )
    run_subparser.add_argument(
        "--btc-node-ip", type=str, help="override btc-node ip", default=""
    )
    run_subparser.add_argument(
        "--wasabi-backend-ip",
        type=str,
        help="override wasabi-backend ip",
        default="",
    )
    run_subparser.add_argument(
        "--control-ip", type=str, help="control ip", default="localhost"
    )
    run_subparser.add_argument("--proxy", type=str, default="")
    run_subparser.add_argument("--namespace", type=str, default="coinjoin")
    run_subparser.add_argument("--reuse-namespace", action="store_true", default=False)

    clean_subparser = subparsers.add_parser("clean", help="clean up")
    clean_subparser.add_argument("--namespace", type=str, default="coinjoin")
    clean_subparser.add_argument(
        "--reuse-namespace", action="store_true", default=False
    )
    clean_subparser.add_argument("--proxy", type=str, default="")
    clean_subparser.add_argument(
        "--image-prefix", type=str, default="", help="image prefix"
    )

    genscen_subparser = subparsers.add_parser("genscen", help="generate scenario file")
    manager.commands.genscen.setup_parser(genscen_subparser)

    args = parser.parse_args()

    if args.command == "genscen":
        manager.commands.genscen.handler(args)
        exit(0)

    match args.driver:
        case "docker":
            from manager.driver.docker import DockerDriver

            driver = DockerDriver("coinjoin")
            driver = DockerDriver(args.namespace)
        case "podman":
            from manager.driver.podman import PodmanDriver

            driver = PodmanDriver()
        case "kubernetes":
            from manager.driver.kubernetes import KubernetesDriver

            driver = KubernetesDriver(args.namespace, args.reuse_namespace)
        case _:
            print(f"Unknown driver '{args.driver}'")
            exit(1)

    if args.command == "run":
        if args.scenario:
            with open(args.scenario) as f:
                SCENARIO.update(json.load(f))

    versions.add(SCENARIO["default_version"])
    if "distributor_version" in SCENARIO:
        versions.add(SCENARIO["distributor_version"])
    for wallet in SCENARIO["wallets"]:
        if "version" in wallet:
            versions.add(wallet["version"])

    match args.command:
        case "build":
            prepare_images()
        case "clean":
            driver.cleanup(args.image_prefix)
        case "run":
            run()
        case "console":
            print("Starting console")
        case _:
            print(f"Unknown command '{args.command}'")
            exit(1)