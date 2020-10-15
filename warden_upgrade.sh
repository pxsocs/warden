#!/bin/bash
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

echo ""
echo "-----------------------------------------------------------------"
echo -e "${BLUE}"
echo "      _   _           __        ___    ____     _"
echo "     | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __"
echo "     | __|  _ \ / _ \  \ \ /\ / / _ \ | |_) / _  |/ _ \  _  |"
echo "     | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |"
echo "      \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"
echo ""
echo -e "${NC}"
echo "-----------------------------------------------------------------"
echo ""
echo " Starting Setup..."
echo " -----------------"
echo " Downloading the latest WARden source code from GitHub.... "

# Check if folder exists. If it does, update with git pull
# otherwise clone it

sudo git fetch --all
sudo git reset --hard origin/master

echo " Cleaning previous Virtual Environment...."
sudo rm -r venv

echo " Re-creating Virtual Environment...."
sudo pip3 install virtualenv
sudo virtualenv venv --system-site-packages

source venv/bin/activate

echo " Installing Python Dependencies...."
sudo pip3 install -r requirements.txt
echo " Making a tentative copy of files - it's ok if this fails..."
sudo cp /usr/lib/python3.7/lib-dynload/_bz2.cpython-37m-arm-linux-gnueabihf.so /usr/local/lib/python3.7/
echo " Opening port 25442 for connections...."
sudo ufw allow 25442/tcp
echo " Enable Executable Script...."
sudo chmod 755 warden.sh

echo -e "${BLUE}"
echo " -----------------------------------------------------"
echo "                      Done"
echo " -----------------------------------------------------"
echo " To launch the server: "
echo " $ ./warden.sh"
echo " "
echo -e "${NC}"
