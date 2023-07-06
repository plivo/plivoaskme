FROM debian:bullseye-slim

ARG DEBIAN_FRONTEND=noninteractive

#RUN apk add --no-cache python3 redis py3-pip gcc g++ libc-dev git make python3-dev bash
RUN apt-get update && apt-get install -y --no-install-recommends \
	git \
	g++ \
	curl \
	ca-certificates \
	redis-server \
	python3 \
	python3-dev \
	python3-pip
RUN rm -rf /var/lib/apt/lists/* || true

WORKDIR /app
# Install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir  -r requirements.txt
RUN mkdir data || true
COPY entrypoint.sh .
COPY local_test.sh .
COPY *.py .
RUN chmod 755 ./entrypoint.sh

EXPOSE 50505

ENTRYPOINT ["/bin/bash", "-c", "./entrypoint.sh"]

