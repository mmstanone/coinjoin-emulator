#!/bin/bash
if [ -z "$ADDR_BTC_NODE" ]; then
    export ADDR_BTC_NODE="btc-node"
fi

export WASABI_BIND="http://0.0.0.0:37128"


echo "Wasabi binding to $WASABI_BIND"
echo $WASABI_BIND
rm -rf /home/wasabi/.walletwasabi

./WalletWasabi.Coordinator
cat /home/wasabi/.walletwasabi/coordinator/Config.json
cp /home/wasabi/Config.json /home/wasabi/.walletwasabi/coordinator/Config.json
cat /home/wasabi/.walletwasabi/coordinator/Config.json

sleep 3
./WalletWasabi.Coordinator --loglevel=trace
