set CONTAINER_TAG=job


docker build -t %CONTAINER_TAG% --file binder/Dockerfile .
docker run -it --rm -p 8888:8888 --mount type=bind,source="%cd%",target=/home/jovyan/htcondor-job %CONTAINER_TAG%
