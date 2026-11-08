#!/usr/bin/env python3
"""Read-only OEM/RIL vendor reference collection. Requires host adb."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from datetime import datetime

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--serial", default="12da33e7")
    ap.add_argument("--output", default="logs")
    args = ap.parse_args()
    dest = Path(args.output).expanduser().resolve() / (
        "vendor-oem-reference-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    dest.mkdir(parents=True, exist_ok=False)
    records = []

    def adb(*parts, timeout=45):
        try:
            r = subprocess.run(
                ["adb", "-s", args.serial, *parts],
                capture_output=True, timeout=timeout
            )
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return 124, b"", b"Host timeout"
        except FileNotFoundError:
            raise SystemExit("adb bulunamadi.")

    rc, stdout, stderr = adb("get-state")
    if rc or stdout.strip() != b"device":
        raise SystemExit("Android ADB hazir degil: " + stderr.decode(errors="replace"))
    rc, stdout, stderr = adb("shell", "getprop ro.product.device")
    if rc or stdout.strip() != b"ginkgo":
        raise SystemExit("Cihaz ginkgo olarak dogrulanamadi.")

    command = (
        "find /vendor/lib /vendor/lib64 /vendor/bin /vendor/etc/init "
        "-type f 2>/dev/null"
    )
    rc, stdout, stderr = adb("shell", command)
    (dest / "vendor-file-list.txt").write_bytes(stdout)
    (dest / "listing-status.json").write_text(json.dumps({
        "exit_code": rc, "stderr": stderr.decode(errors="replace")
    }, indent=2) + "\n")
    selected = sorted({
        p.strip() for p in stdout.decode(errors="replace").splitlines()
        if p.startswith("/vendor/")
        and any(word in Path(p.strip()).name.lower()
                for word in ("ril", "oemhook"))
    })
    if not selected:
        raise SystemExit("RIL/OEM dosyasi bulunamadi; liste: " + str(dest))

    for remote in selected:
        local = dest / remote.lstrip("/")
        local.parent.mkdir(parents=True, exist_ok=True)
        rc, _, err = adb("pull", remote, str(local), timeout=120)
        record = {"source": remote, "exit_code": rc,
                  "stderr": err.decode(errors="replace")}
        if rc == 0 and local.is_file():
            record["size"] = local.stat().st_size
            with local.open("rb") as stream:
                record["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        records.append(record)
        print(("OK " if rc == 0 else "ATLANDI ") + remote, flush=True)

    (dest / "manifest.json").write_text(
        json.dumps(records, indent=2) + "\n"
    )
    archive = dest.with_suffix(".tar.gz")
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(dest, arcname=dest.name)
    print("PAKET:", archive)
    print("Telefona yazma, reboot veya flash yapilmadi.")
    if not any(r.get("sha256") for r in records):
        raise SystemExit("Hicbir dosya cekilemedi; hata manifesti pakette.")

if __name__ == "__main__":
    main()
