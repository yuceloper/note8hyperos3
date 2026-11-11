# Camera fresh-launch investigation on V43

V43 user reports working signal bars, calls, mobile data and reconnection. System image SHA256 ed4fdb10b91b90bb839de2bbc58e6867fc49b5430d7dd77962d721a64d8b23aa; V26 vendor retained. V43 is the current rollback baseline.

The occasional first camera launch error was observed before V41 EROFS symlink repair; it has not yet been reproduced on V43. Older v35-first-lockscreen-camera.txt includes a CameraDeviceImpl onDeviceError/close lock sample, insufficient to identify the initiating cause. Do not assume a permission, timeout, driver or startup-check root cause from that sample.

collect.py verifies the exact V43 telephony JAR and system V35 camera APK/path, captures camera service state, then force-stops and opens only com.android.camera twice, observing each for eight seconds. Run with phone unlocked and no recording/call in progress. It reads existing logs from a device-clock boundary without clearing buffers, changing settings, rebooting or installing code. The second camera remains open. It saves a host archive even when a launch collection fails. Each ADB command uses DEVNULL stdin and a timeout. PID survival alone is not a preview/recording success criterion.

Run: python3 tools/H3_Camera_v44/collect.py --reveal

User should report which of the two launches, if either, displayed the countdown or connection error. If both pass, include this result before deciding whether another reproduction condition is necessary. No workaround or camera binary patch is included here.
