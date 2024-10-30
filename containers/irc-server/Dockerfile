FROM inspircd/inspircd-docker:latest

USER root

# Install necessary packages
RUN apk update && \
    apk add --no-cache iproute2 iputils

# Copy your entrypoint script into the container
COPY entrypoint.sh /entrypoint-latency.sh
RUN chmod +x /entrypoint-latency.sh

# Add volumes for the configuration and data
COPY inspircd.conf /inspircd/conf/inspircd.conf

# Set the entrypoint to your script
WORKDIR /

ENTRYPOINT ["/entrypoint-latency.sh"]