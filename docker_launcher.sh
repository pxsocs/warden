#!/bin/sh
cd /build
service tor start
python3 warden
