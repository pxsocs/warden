FROM python:3.10-slim-buster

WORKDIR /app

RUN python3 -m pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN apt-get update
RUN apt-get install -y git python3 build-essential
RUN apt-get install -y python3-pip
RUN apt-get install -y python3-dev
RUN apt-get install -y libevent-dev
RUN apt-get install -y gcc
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install Cython
RUN python3 -m pip install pysocks
RUN python3 -m pip install numpy==1.24.1
RUN python3 -m pip install pybind11==2.10.1
RUN python3 -m pip install cmake
RUN python3 -m pip install -r requirements.txt

COPY . .
RUN chmod 777 docker_launcher.sh

# Install Tor
RUN apt-get install -y tor

# These are the ports that WARden runs from
# It will try one of these
EXPOSE 5000
EXPOSE 5001
EXPOSE 5002
EXPOSE 5003
EXPOSE 5004
EXPOSE 5005

# These are Tor ports
EXPOSE 9050
EXPOSE 9150

ENTRYPOINT ["sh","/app/docker_launcher.sh"]
CMD [""]
