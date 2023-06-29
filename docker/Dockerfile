FROM ubuntu:20.04

ARG DEVICE=cpu

ENV DEBIAN_FRONTEND noninteractive

# required
RUN    apt update \
    && apt install -y make git pkg-config libssl-dev cmake python3 python3-dev python3-pip binutils-dev libgoogle-glog-dev gcc g++

# optional
RUN    apt install -y libopencv-dev libomp-dev libtorch3-dev

RUN pip install setuptools timeout_decorator

COPY ./ /root/bmf/
WORKDIR /root/bmf/

# ffmpeg installed via apt has no development libraries, so we build it from source
RUN scripts/build_ffmpeg.sh $DEVICE nasm yasm x264 x265 fdk-aac opus

RUN ./build.sh disable cuda

ENV LD_LIBRARY_PATH=/root/bmf/output/bmf/lib
ENV PATH=${PATH}:/root/bmf/output/bmf/bin
ENV PYTHONPATH=/root/bmf/output
