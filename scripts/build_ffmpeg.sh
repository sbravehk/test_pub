#!/bin/bash

set -exuo pipefail

OS=$(uname)
. /etc/os-release

if [ $# -eq 0 ]
then
    echo "Which version of ffmpeg do you want to compile, GPU or CPU?"
    exit 1
fi
DEVICE=$(echo $1 | tr 'A-Z' 'a-z')
shift 1


function install_dependencies_linux() {
    if [[ ${NAME} =~ "CentOS" ]]
    then
        yum install -y autoconf automake bzip2 bzip2-devel cmake gcc gcc-c++ git libtool make pkgconfig zlib-devel wget
    elif [[ ${NAME} == "Ubuntu" ]]
    then
        apt install -y autoconf automake bzip2 cmake gcc g++ git libtool make pkg-config wget curl
    fi

}

function install_dependencies_macos() {
    brew install automake git libtool wget 
}

function build_nasm_unix() {
    cd $1
    curl -O -L https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/nasm-2.15.05.tar.bz2
    tar xjvf nasm-2.15.05.tar.bz2
    cd nasm-2.15.05
    ./autogen.sh
    ./configure --enable-shared
    make -j $2
    make install
}

function build_yasm_unix() {
    cd $1
    curl -O -L https://www.tortall.net/projects/yasm/releases/yasm-1.3.0.tar.gz
    tar xzvf yasm-1.3.0.tar.gz
    cd yasm-1.3.0
    ./configure
    make -j $2
    make install
}

function build_x264_unix() {
    cd $1
    git clone --branch stable --depth 1 https://code.videolan.org/videolan/x264.git
    cd x264
    ./configure --enable-shared
    make -j $2
    make install
}

function build_x265_unix() {
    cd $1
    git clone --branch stable --depth 2 https://bitbucket.org/multicoreware/x265_git
    cd $1/x265_git/build/linux
    cmake -G "Unix Makefiles" -DENABLE_SHARED:bool=off ../../source
    make -j $2
    make install
}

function build_fdk-aac_unix() {
    cd $1
    git clone --depth 1 https://github.com/mstorsjo/fdk-aac
    cd fdk-aac
    autoreconf -fiv
    ./configure --enable-shared
    make -j $2
    make install
}

function build_mp3lame_unix() {
    cd $1
    curl -O -L https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz
    tar xzvf lame-3.100.tar.gz
    cd lame-3.100
    ./configure --enable-shared --enable-nasm
    make -j $2
    make install
}

function build_opus_unix() {
    cd $1
    curl -O -L https://archive.mozilla.org/pub/opus/opus-1.3.1.tar.gz
    tar xzvf opus-1.3.1.tar.gz
    cd opus-1.3.1
    ./configure --enable-shared
    make -j $2
    make install
}

function build_vpx_unix() {
    cd $1
    git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git
    cd libvpx
    ./configure --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=yasm
    make -j $2
    make install
}

function build_ffmpeg_unix() {
    cd $1
    if [ ! -e ffmpeg-4.4 ]
    then
        curl -O -L https://ffmpeg.org/releases/ffmpeg-4.4.tar.bz2
        tar xjvf ffmpeg-4.4.tar.bz2
    fi
    cd ffmpeg-4.4

    if [ ${OS} == "Linux" ] && [ ${DEVICE} == "gpu" ] && [ $(uname -m) == "x86_64" ]
    then
	sed -i 's/gencode arch=compute_30,code=sm_30/gencode arch=compute_52,code=sm_52/g' configure

        ## https://stackoverflow.com/questions/6622454/cuda-incompatible-with-my-gcc-version
	## gcc-10 is not supported by cuda11, so we use the older gcc temporary.
	#mv /opt/rh/devtoolset-10{,.bak}
	#hash -r

        #recover() {
        #    mv /opt/rh/devtoolset-10{.bak,}
        #    hash -r
        #}
        #trap 'recover' RETURN
	which gcc
	gcc --version
    fi

    trap 'cat ffbuild/config.log' ERR
    ./configure \
      --pkg-config-flags="--static" \
      --enable-shared \
      --disable-static \
      --disable-autodetect \
      --extra-libs=-lpthread \
      --extra-libs=-lm \
      ${@:3}
    trap - ERR

    make -j $2
    make install
}

function install_cuda_linux() {
    cd $1
    if [[ ${NAME} =~ "CentOS" ]]
    then
        wget -q http://developer.download.nvidia.com/compute/cuda/11.0.2/local_installers/cuda-repo-rhel7-11-0-local-11.0.2_450.51.05-1.x86_64.rpm
        rpm -i cuda-repo-rhel7-11-0-local-11.0.2_450.51.05-1.x86_64.rpm
        yum clean all
        yum -y install nvidia-driver-latest-dkms cuda
        yum -y install cuda-drivers
        export PATH=${PATH}:/usr/local/cuda/bin
    elif [[ ${NAME} == "Ubuntu" ]]
    then
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
        wget http://developer.download.nvidia.com/compute/cuda/11.0.2/local_installers/cuda-repo-ubuntu2004-11-0-local_11.0.2-450.51.05-1_amd64.deb
        dpkg -i cuda-repo-ubuntu2004-11-0-local_11.0.2-450.51.05-1_amd64.deb
        apt-key add /var/cuda-repo-ubuntu2004-11-0-local/7fa2af80.pub
        apt-get update
        apt-get -y install cuda
    fi
    cd -
}

function build_ffnvcodec_linux() {
    cd $1
    git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git
    cd nv-codec-headers
    make install
}

function check_lib() {
    cd $1
    if [ ! -e ffmpeg-4.4 ]
    then
        curl -O -L https://ffmpeg.org/releases/ffmpeg-4.4.tar.bz2
        tar xjvf ffmpeg-4.4.tar.bz2
    fi

    cd ffmpeg-4.4
    str="\-\-enable-lib"$2
    ./configure --help | grep ''${str}''
    if [ $? -eq 0 ]
    then
        return 0
    fi
    return 1
}

if [ ${OS} == "Linux" ] || [ ${OS} == "Darwin" ]
then
    disable_asm="--disable-x86asm"
    ffmpeg_opts="--enable-gpl --enable-nonfree"
    mkdir -p ffmpeg_source

    if [ ${OS} == "Linux" ]
    then
        (install_dependencies_linux)
        if [ ${DEVICE} == "gpu" ] && [ $(uname -m) == "x86_64" ]
        then
            install_cuda_linux $(pwd)/ffmpeg_source
	    (build_ffnvcodec_linux $(pwd)/ffmpeg_source)
	    ffmpeg_opts="${ffmpeg_opts} --enable-cuda-nvcc --enable-libnpp --extra-cflags=-I/usr/local/cuda/include --extra-ldflags=-L/usr/local/cuda/lib64"
        fi
	cores=$(nproc)
    else
        (install_dependencies_macos)
	cores=$(sysctl -n hw.logicalcpu)
    fi

    for arg in $@
    do
        (build_${arg}_unix $(pwd)/ffmpeg_source ${cores})

	if [ ${arg} == "nasm" ] || [ ${arg} == "yasm" ]
	then
            disable_asm=""
	fi

        set +e
	(check_lib $(pwd)/ffmpeg_source ${arg})
	if [ $? -eq 0 ]
	then
            ffmpeg_opts="${ffmpeg_opts} --enable-lib${arg}"
	fi
	set -e
    done
    
    ffmpeg_opts="${ffmpeg_opts} ${disable_asm}"

    printf "ffmpeg_opts: %s\n" ${ffmpeg_opts}
    build_ffmpeg_unix $(pwd)/ffmpeg_source ${cores} ${ffmpeg_opts}
else
    printf "the system %s is not supported!" ${OS}
    exit 1
fi
