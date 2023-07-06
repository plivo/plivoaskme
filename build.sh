#!/bin/bash
ARCH="amd64"
case $1 in
	"arm64"|"amd64")
		ARCH=$2
	;;
	"*")
		echo "Invalid architecture $2"
		exit 1
	;;
esac

set -x
docker build \
	-f Dockerfile \
	--platform linux/${ARCH} \
	--build-arg ARCH=${ARCH} \
	-t plivo/askme .
