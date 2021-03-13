# Welcome to the WARden

[![GitHub release](https://img.shields.io/github/release/pxsocs/warden.svg)](https://GitHub.com/pxsocs/warden/releases/)
[![Open Source? Yes!](https://badgen.net/badge/Open%20Source%20%3F/Yes%21/blue?icon=github)](https://GitHub.com/pxsocs/warden/releases/)
[![Powered by NGU](https://img.shields.io/badge/Powered%20by-NGU%20Technology-orange.svg)](https://bitcoin.org)

### Requirements:

> 🐍 Python 3.7 or later

This app was built with a couple of goals:

- Easily track portfolio values in fiat

When connected to Specter Server 👻 [optional]:

- Monitors Wallets and Addresses for activity using your own node and notifies user of activity
- Track your Bitcoin node status

# INSTALLATION

There are two methods to install the WARden. The recommended one is to install inside a docker container. This is typically more stable in most systems.

1. [Install using Docker](#docker_install)

2. [Regular Installation](#regular_install)

## <a name="docker_install"></a> 🐳 Docker Container instructions (recommended):

_If you don't want to have docker installed follow the regular instructions_

### Requirements:

> Docker needs to installed and running

Downloadn and build the container:

```bash
git clone https://github.com/pxsocs/warden
cd warden
sudo ./warden.sh --dockerbuild
```

Run:

```bash
sudo ./warden.sh --dockerrun
```

## <a name="regular_install"></a> Regular Instructions (without docker installation)

```bash
git clone https://github.com/pxsocs/warden
cd warden
python3 -m pip install -r requirements.txt
```

Then run the WARden server:

```bash
python3 warden
```

Upgrade:

```bash
git pull origin master
```

## Screenshot

![Screenshot](https://raw.githubusercontent.com/pxsocs/warden/master/warden/static/images/Screen%20Shot%202021-02-08%20at%209.19.28%20AM.png)

## This is an Open Source project

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

We believe Open Source is the future of development for bitcoin. There is no other way when transparency and privacy are critical.

The code is not compiled and it can be easily audited. It can also be modified and distributed as anyone wishes.

## Privacy

Most portfolio tracking tools ask for personal information and may track your IP and other information. Our experience is that even those who say they don't, may have log files at their systems that do track your IP and could be easily linked to your data.

### Troubleshooting

> If you get a message telling you that pip is not installed:

```bash
sudo apt-get -y install python3-pip
```

> If you get a message that git was not found:

```bash
sudo apt-get install git
```

> If Docker is not installed

[Docker Install Instructions for most OS systems can be found here](https://docs.docker.com/get-docker/)

Docker Installation Instructions for Debian (Most Raspberry Pi systems)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

Then get your user name by typing:

```bash
w
```

Then add this user to the docker group:

```bash
sudo usermod -aG docker <your-user>
```

**Please note that this is ALPHA software. There is no guarantee that the
information and analytics are correct. Also expect no customer support. Issues are encouraged to be raised through GitHub but they will be answered on a best efforts basis.**

> warden (wɔːʳdən )

> A warden is responsible for making sure that the laws or regulations are obeyed.
