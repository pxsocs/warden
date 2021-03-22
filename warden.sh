#!/bin/bash

helpFunction()
{
    echo ""
    echo "\tWARden Run Script"
    echo "\t-------------------------------------------------------------------------------------"
    echo "\tUsage: $0 --parameters"
    echo ""
    echo "\tParameters:"
    echo "\t --help\t\t\tDisplays this help"
    echo "\t --host [0.0.0.0]\t\tDefines which ip address to host the server"
    echo "\t\t\t\t\t0.0.0.0   uses your local IP address and allows outside access"
    echo "\t\t\t\t\t127.0.0.1 defaults to localhost"
    echo "\t --port [5000]\t\tDefines which port to run the server"
    echo "\t --debug\t\t\tEnables debug mode"
    echo "\t --setup\t\t\tFirst time setup"
    echo "\t --upgrade\t\t\tUpgrade to latest version"
    echo "\t --dockerbuild\t\t\tBuilds Docker Container"
    echo "\t --dockerrun\t\t\tRuns app from within a built docker container"
    echo ""
    exit 1 # Exit script after printing help
}

pythonNotFound()
{
    echo ""
    echo "\tPython3 does not seem to be installed in this machine"
    echo "\tplease install to use WARden. Download and instructions:"
    echo "\thttps://www.python.org/"
    echo ""
    exit 1
}

installPackages()
{
    python3 -m pip install -r requirements.txt
}

python_params=()
# Get Arguments from shell script
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -h|--help)
    HELP=true
    shift # past argument
    ;;
    --docker)
    DOCKER=true
    shift # past argument
    ;;
    -s|--setup)
    SETUP=true
    shift # past argument
    ;;
    -t|--host)
    HOST="$2"
    python_params+="--host ${HOST}"
    shift # past argument
    shift # past value
    ;;
    -p|--port)
    PORT="$2"
    python_params+="--port ${PORT}"
    shift # past argument
    shift # past value
    ;;
    -d|--debug)
    DEBUG=true
    python_params+="--debug"
    shift # past argument
    ;;
    -u|--upgrade)
    UPGRADE=true
    shift # past argument
    ;;
    -b|--dockerbuild)
    DOCKERBUILD=true
    shift # past argument
    ;;
    -r|--dockerrun)
    DOCKERRUN=true
    shift # past argument
    ;;

    *)    # unknown option - pass to python
    python_params+=("$1")
    shift # past argument
    ;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

if [ "$HELP" = true ] ; then
    helpFunction
fi

if [ "$DOCKER" = true ] ; then
    # If inside Docker container
    cd /build
    service tor start
fi

if [ "$DOCKERBUILD" = true ] ; then
    # clean up older and stopped images
    docker rm -v $(docker ps --filter status=exited -q 2>/dev/null) 2>/dev/null
    docker rmi $(docker images --filter dangling=true -q 2>/dev/null) 2>/dev/null
    # build
    docker build -t warden:latest .
    exit 1
fi

if [ "$DOCKERRUN" = true ] ; then
    docker run -it -p 5000:5000 warden
    exit 1
fi

if [ "$SETUP" = true ] ; then
    # Check if Python3 is installed
    command -v python3 2>&1 || pythonNotFound
    # install package requirements
    installPackages
fi

if [ "$UPGRADE" = true ] ; then
    # Get new git
    echo Upgrading from GitHub:
    git fetch --all
    git reset --hard origin/master
    # install package requirements
    echo Installing Python Package Requirements
    installPackages
    echo Done
    echo Now remember to rebuild
fi

# Launch app
# Check for Python 3
command -v python3 2>&1 || pythonNotFound


python3 warden