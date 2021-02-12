FROM python:3.9.1


RUN apt-get update && \
    apt-get -y install python3-pandas

RUN python -m pip install --upgrade pip

WORKDIR /app

COPY . /app

RUN python -m pip install Cython
RUN python -m pip install pysocks
RUN python -m pip install -r requirements.txt

# This is the port that WARden runs from
EXPOSE 5000

# Install Tor
RUN apt-get install -y tor

# These are Tor ports
EXPOSE 9050
EXPOSE 9150

ENTRYPOINT ["/app/docker_launcher.sh"]
CMD [""]

