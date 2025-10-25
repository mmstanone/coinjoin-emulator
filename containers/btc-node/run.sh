#!/bin/sh
./mine.sh &
bitcoind -conf=/home/bitcoin/.bitcoin/bitcoin.conf -datadir=/home/bitcoin/data -printtoconsole -blockfilterindex -regtest -fallbackfee=0.00000001 --paytxfee=0.00000010
