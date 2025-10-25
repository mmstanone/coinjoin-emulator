FROM mcr.microsoft.com/dotnet/sdk:8.0
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
RUN apt update && apt install -y patch

RUN useradd -u 1000 -ms /bin/sh wasabi
# Needs to be numeric for kubernetes security context
USER 1000:1000

# get wasabi from the github repo and checkout to the desired branch
RUN mkdir -p /home/wasabi/wasabi-src
WORKDIR /home/wasabi/wasabi-src
RUN git clone https://github.com/zkSNACKs/WalletWasabi.git .
RUN git checkout v2.6.0

COPY 260.patch /home/wasabi/wasabi-src/logger.patch
COPY indexstore.patch /home/wasabi/wasabi-src/indexstore.patch
COPY global.patch /home/wasabi/wasabi-src/global.patch
COPY broadcaster.patch /home/wasabi/wasabi-src/broadcaster.patch
RUN patch --binary -p1 < global.patch

WORKDIR /home/wasabi/wasabi-src/WalletWasabi.Daemon
RUN dotnet build 
# RUN patch --binary -p1 < logger.patch
# RUN patch -p1 < indexstore.patch

# RUN patch --binary -p1 < broadcaster.patch

COPY --chown=wasabi:wasabi Config.json /home/wasabi/Config.json
COPY --chown=wasabi:wasabi Config2.json /home/wasabi/Config2.json
COPY --chown=wasabi:wasabi run.sh /home/wasabi/wasabi-src/WalletWasabi.Daemon
WORKDIR /home/wasabi/wasabi-src/WalletWasabi.Daemon
CMD ["./run.sh"]
