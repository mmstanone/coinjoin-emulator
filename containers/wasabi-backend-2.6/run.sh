#!/bin/bash
if [ -z "$ADDR_BTC_NODE" ]; then
    export ADDR_BTC_NODE="btc-node"
fi

export WASABI_BIND="http://0.0.0.0:37127"
rm -rf /home/wasabi/.walletwasabi

./WalletWasabi.Backend
echo "Waiting for the crash which happened already"
echo "BEFORE\n\n\n"
cat /home/wasabi/.walletwasabi/backend/Config.json
cp /home/wasabi/Config.json /home/wasabi/.walletwasabi/backend/Config.json

cat /home/wasabi/.walletwasabi/backend/Config.json
sleep 2
timeout 10 ./WalletWasabi.Backend

echo "This should error now...\n\n\n\n"

./WalletWasabi.Backend
