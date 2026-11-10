FROM ginkgo-port-tools:erofs
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential autoconf automake libtool pkg-config \
    liblz4-dev libselinux1-dev uuid-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY prepare_builder.py /build/prepare_builder.py
RUN python3 /build/prepare_builder.py /build
WORKDIR /build/erofs-utils-1.8.6
RUN ./autogen.sh \
    && ./configure --prefix=/opt/erofs-v41 --enable-lz4 --with-selinux --disable-fuse \
    && make -j2 && make install
ENV PATH="/opt/erofs-v41/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
COPY audit.py /opt/erofs-v41/audit.py
RUN python3 -c "import sys; sys.path.insert(0,'/opt/erofs-v41'); from audit import probe; print('V41 SYMLINK PROBE:',probe())"
WORKDIR /work
ENTRYPOINT []
CMD ["mkfs.erofs", "--version"]
