#!/usr/bin/env bash

set -e

CONTAINER_TAG=job

docker build -t ${CONTAINER_TAG} --file binder/Dockerfile .
docker run -it --rm -p 8888:8888 --mount type=bind,source="$(pwd)",target=/home/jovyan/htcondor-job ${CONTAINER_TAG}
