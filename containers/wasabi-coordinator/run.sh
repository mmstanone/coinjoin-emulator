#!/bin/bash
if [ -z "$ADDR_BTC_NODE" ]; then
    export ADDR_BTC_NODE="btc-node"
fi
mkdir -p /home/wasabi/.walletwasabi/coordinator
cp /home/wasabi/WabiSabiConfig.json /home/wasabi/.walletwasabi/coordinator/Config.json
sleep 2
./WalletWasabi.Coordinator localhost
