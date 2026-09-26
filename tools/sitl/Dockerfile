# ArduPilot SITL (the real ArduCopter flight code, simulated vehicle) for testing
# PyreSwarm with several autopilots at once, before any real flight.
#
#   docker build -t pyreswarm-sitl tools/sitl
#   docker run --rm -p 5760-5800:5760-5800 -e COUNT=3 pyreswarm-sitl
#
# Instance i listens on TCP 5760 + 10*i with MAVLink system id i+1.
# In the hub: Add drone -> MAVLink -> tcp:127.0.0.1:5760 (5770, 5780 ...).
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates python3 python3-pip python3-dev build-essential g++ gawk \
        pkg-config libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir empy==3.3.4 pexpect future lxml pymavlink
ARG AP_TAG=Copter-4.5.7
RUN git clone --depth 1 --branch ${AP_TAG} https://github.com/ArduPilot/ardupilot.git /ardupilot \
    && cd /ardupilot && git submodule update --init --recursive --depth 1
WORKDIR /ardupilot
RUN ./waf configure --board sitl && ./waf copter
COPY run_swarm.sh /run_swarm.sh
EXPOSE 5760 5770 5780 5790 5800
ENTRYPOINT ["/bin/bash", "/run_swarm.sh"]
