FROM debian:bookworm-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 apktool apksigner zipalign aapt default-jdk-headless \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
ENTRYPOINT ["python3", "/package/build_test_apk.py"]
