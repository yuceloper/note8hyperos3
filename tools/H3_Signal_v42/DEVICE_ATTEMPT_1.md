# Isolated probe attempt 1 — 2026-11-11

Archive: ginkgo-signal-probe-20261111-091843-871376.tar.gz.
Probe SHA256: 61d7d19c0a23a4eb08074991026ed75ab97a64b66ed98b3b5508293c9906e57c.
Remote temporary directory setup/push/chmod succeeded.
app_process64 returned 137 with only `Killed` in captured output.
No negative-control or positive conversion success markers were printed.
com.android.phone PID remained 3157 before/after.

Status remains REVIEW_REQUIRED. This is not proof the V40 converter failed,
nor evidence that the negative control executed. The available output does
not identify who sent the kill or whether memory pressure, execution policy,
or another runtime problem caused it. Do not silently retry, disable global
security controls, change memory settings or advance to a signal image.
Next collect existing lmkd/kill/execution-related logs and current memory
context read-only, then choose a bounded targeted test based on evidence.
V41 continues as the user-confirmed working calls/data packaging baseline.
