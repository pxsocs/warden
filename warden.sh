#!/bin/bash
source venv/bin/activate
sudo git tag >> version.txt
sudo python3 warden.py $1 $2