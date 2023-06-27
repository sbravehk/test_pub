FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN    apt update \
    && apt install -y make git pkg-config libssl-dev cmake python3 python3-dev python3-pip binutils-dev libgoogle-glog-dev gcc g++

RUN pip install setuptools timeout_decorator

COPY . /root/bmf
WORKDIR /root/bmf
# ffmpeg installed from apt has no include files, so we build from source
RUN scripts/build_ffmpeg.sh cpu
RUN ./build.sh

ENV LD_LIBRARY_PATH=/root/bmf/output/bmf/lib
ENV PATH=${PATH}:/root/bmf/output/bmf/bin
ENV PYTHONPATH=/root/bmf/output
