# V43 camera fresh-process launch result — 2026-11-11

Reviewed archive: camera-v44-20261111-100724-386150.tar.gz. User observed no problem in either launch.

Verified live baseline: original-identity system camera APK a316586185bfa320d9c888667bf044d7ab835004b759a5f1b009c931d52bbeaa at /product/priv-app/MiuiCamera/MiuiCamera.apk; telephony V40 JAR 1279a5eb44e5a0ff6ca32943af7b7b31f793c668adff9c1849ff146c3f9fe5a0 (V43 system).

Both launches returned Status ok / LaunchState COLD. TotalTime 1675ms and 1517ms; distinct camera PIDs 11979 and 11980 survived the observation. Camera service connected rear device 0 in 97ms and 98ms respectively and reported zero camera error traces after each. Captured crash buffer is empty. User confirms preview worked without countdown/connection warning.

A binder-death entry occurs at the intentional inter-attempt force-stop; its reported PID is 1382, so do not infer its exact owner or a camera HAL crash from this entry alone. Both subsequent service connection and preview succeeded. Autofocus/SOF timeout configuration messages are not an observed timeout failure.

Result: two normal unlocked fresh-process launches passed; historical intermittent first-open error NOT REPRODUCED on V43. No camera patch justified. This does not prove the historical issue permanently fixed or that EROFS repair caused the improvement. First launch immediately after reboot, secure lockscreen launch, all sensors/modes, sustained recording, and repeated cycles are outside this test.

No ROM, permissions, settings or vendor changes were made. Keep V43 system + V26 vendor as working baseline. Prefer a small manual secure-camera and capture/playback regression check next; leave startup stutter for the user's requested final phase.
