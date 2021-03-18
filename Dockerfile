FROM debian:buster-slim

WORKDIR /build
COPY . /build


RUN apt-get update
RUN apt-get install -y git python3 build-essential
RUN apt-get install -y python3-pip
RUN apt-get -y install python3-numpy
RUN apt-get -y install python3-pandas
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install Cython
RUN python3 -m pip install pysocks
RUN python3 -m pip install -r requirements.txt

# Install Tor
RUN apt-get install -y tor

# This is the port that WARden runs from
EXPOSE 5000

# These are Tor ports
EXPOSE 9050
EXPOSE 9150

ENTRYPOINT ["sh","/build/docker_launcher.sh"]
CMD [""]

