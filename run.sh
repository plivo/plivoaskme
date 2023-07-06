#!/bin/bash
MYENV="prod"
case $1 in
	"prod"|"dev"|"ingest")
		MYENV="$1"
	;;
	"*")
		echo "Usage: $0 (prod|dev) [amd64|arm64]"
		echo "	Default is: prod amd64"
		exit 1
	;;
esac

ARCH="amd64"
case $2 in
	"arm64"|"amd64")
		ARCH=$2
	;;
	"*")
		echo "Invalid architecture $2"
		exit 1
	;;
esac


if [ -z "$SLACK_TOKEN_ID" ]; then
	echo "SLACK_TOKEN_ID is not set"
	exit 1
fi
if [ -z "$OPENAI_API_KEY" ]; then
	echo "OPENAI_API_KEY is not set"
	exit 1
fi
if [ -z "$OPENAI_MODEL" ]; then
	OPENAI_MODEL="gpt-3.5-turbo"
fi 
if [ -z "$VECTOR_DATABASE" ]; then
	VECTOR_DATABASE="data/codebot.faiss.${ARCH}"
fi
if [ "$MYENV" = "prod" ] || [ "$MYENV" = "dev" ]; then
	extra_args="-p 50505:50505"
fi

docker run --platform "linux/${ARCH}" \
	--rm \
	-ti \
	-e SLACK_TOKEN_ID="$SLACK_TOKEN_ID" \
	-e OPENAI_API_KEY="$OPENAI_API_KEY" \
	-e OPENAI_MODEL="$OPENAI_MODEL" \
	-e VECTOR_DATABASE="$VECTOR_DATABASE" \
	-e ARCH="$ARCH" \
	-e ENV="$MYENV" \
	-v "${PWD}/data:/app/data" $extra_args \
	plivo/askme

