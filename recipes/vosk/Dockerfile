# Pinned MinGW cross-compilation environment for Vosk 0.3.38 candidate build
# Classification: Prospective replacement candidate with functional and ABI parity target.
# Upstream shipped binary (9EE0301E...) was compiled under Debian 10 / GCC 8.3.
# This container builds a prospective replacement library using Debian 12 MinGW-w64.
FROM debian:12-slim@sha256:a4672c0cb26fbdde88e38fa2dfb6c681942306680e41e4378b28770b6e79ee91

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++-mingw-w64-x86-64 \
    gcc-mingw-w64-x86-64 \
    make \
    cmake \
    libtool \
    automake \
    autoconf \
    pkg-config \
    ca-certificates \
    tar \
    gzip \
    dpkg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY sources/ /build/sources/

# Record exact toolchain package versions installed
RUN mkdir -p /dist && \
    dpkg -l build-essential g++-mingw-w64-x86-64 gcc-mingw-w64-x86-64 make cmake libtool automake autoconf pkg-config > /dist/toolchain-versions.txt && \
    x86_64-w64-mingw32-gcc --version >> /dist/toolchain-versions.txt && \
    x86_64-w64-mingw32-g++ --version >> /dist/toolchain-versions.txt

# 1. OpenFST (pinned commit 7dfd808)
RUN mkdir -p /build/openfst && \
    tar -xzf /build/sources/voskinput-alphacep-openfst-7dfd808194105162f20084bb4d8e4ee4b65266d5.tar.gz -C /build/openfst --strip-components=1 && \
    cd /build/openfst && \
    autoreconf -i && \
    CXX=x86_64-w64-mingw32-g++-posix CXXFLAGS="-O3 -ftree-vectorize -DFST_NO_DYNAMIC_LINKING" \
    ./configure --prefix=/opt/kaldi/local --enable-shared --enable-static --with-pic --disable-bin --host=x86_64-w64-mingw32 && \
    make -j$(nproc) && make install

# 2. OpenBLAS (pinned v0.3.20 release commit 0b678b1)
RUN mkdir -p /build/openblas && \
    tar -xzf /build/sources/ffinput-xianyi-OpenBLAS-0b678b19dc03f2a999d6e038814c4c50b9640a4e.tar.gz -C /build/openblas --strip-components=1 && \
    cd /build/openblas && \
    make HOSTCC=gcc BINARY=64 CC=x86_64-w64-mingw32-gcc ONLY_CBLAS=1 DYNAMIC_ARCH=1 TARGET=NEHALEM USE_LOCKING=1 USE_THREAD=0 -j$(nproc) && \
    make PREFIX=/opt/kaldi/local install

# 3. CLAPACK (pinned commit 931173d)
RUN mkdir -p /build/clapack && \
    tar -xzf /build/sources/voskinput-alphacep-clapack-931173de8032c9dbb588f82b58b66a57fce830eb.tar.gz -C /build/clapack --strip-components=1 && \
    mkdir -p /build/clapack/BUILD && cd /build/clapack/BUILD && \
    cmake -DCMAKE_C_COMPILER_TARGET=x86_64-w64-mingw32 -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc-posix -DCMAKE_SYSTEM_NAME=Windows -DCMAKE_CROSSCOMPILING=True .. && \
    make -C F2CLIBS/libf2c -j$(nproc) && \
    make -C BLAS -j$(nproc) && \
    make -C SRC -j$(nproc) && \
    find . -name "*.a" -exec cp {} /opt/kaldi/local/lib \;

# 4. Kaldi (pinned vosk-android commit 16ff67f)
RUN mkdir -p /build/kaldi && \
    tar -xzf /build/sources/voskinput-alphacep-kaldi-16ff67f515512a362d249b9b736aedc87e89b874.tar.gz -C /build/kaldi --strip-components=1 && \
    cd /build/kaldi/src && \
    CXX=x86_64-w64-mingw32-g++-posix CXXFLAGS="-O3 -ftree-vectorize -DFST_NO_DYNAMIC_LINKING" ./configure --shared --mingw=yes --use-cuda=no \
        --mathlib=OPENBLAS_CLAPACK --host=x86_64-w64-mingw32 --openblas-clapack-root=/opt/kaldi/local \
        --fst-root=/opt/kaldi/local --fst-version=1.8.0 && \
    make depend -j$(nproc) && \
    make -j$(nproc) online2 lm rnnlm

# 5. Vosk API C++ wrapper (pinned v0.3.38 release commit f73088d)
RUN mkdir -p /build/vosk-api && \
    tar -xzf /build/sources/vosk-api-f73088da5840f9a382eb949f65cbfeaef901e983.tar.gz -C /build/vosk-api --strip-components=1 && \
    cd /build/vosk-api/src && \
    EXTRA_LDFLAGS=-Wl,--out-implib,libvosk.lib CXX=x86_64-w64-mingw32-g++-posix EXT=dll KALDI_ROOT=/build/kaldi OPENFST_ROOT=/opt/kaldi/local OPENBLAS_ROOT=/opt/kaldi/local make -j$(nproc) && \
    cp libvosk.dll libvosk.lib /dist/ && \
    cp /usr/lib/gcc/x86_64-w64-mingw32/*-posix/libstdc++-6.dll /dist/ && \
    cp /usr/lib/gcc/x86_64-w64-mingw32/*-posix/libgcc_s_seh-1.dll /dist/ && \
    cp /usr/x86_64-w64-mingw32/lib/libwinpthread-1.dll /dist/
