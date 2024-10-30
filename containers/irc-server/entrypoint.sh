#!/bin/sh

# Add network latency using 'tc' command
tc qdisc add dev eth0 root netem delay 200ms

# Switch to the `inspircd` user and run the original entrypoint
exec su -s /bin/sh inspircd -c "/entrypoint.sh $@"