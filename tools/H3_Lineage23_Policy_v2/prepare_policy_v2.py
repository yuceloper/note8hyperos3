PUB_HASH = '9f1c71b751fd94686808efb926cb5ca310434420dc2f612b180da97db2aa53ec'
from pathlib import Path
import hashlib, json, subprocess
PATCHES = [['(allow hal_atrace_default debugfs_tracing_debug_202504 (file (ioctl read write getattr lock append map open watch watch_reads)))\n', ''], ['(allow hal_hwcrypto_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow hal_keymint_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow hal_keymint_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow ot_rcp self (netlink_route_socket (nlmsg)))\n', ''], ['(allowx ot_rcp self (nlmsg netlink_route_socket (0x16 0x1a 0x22 0x26 0x2a 0x2e 0x32 0x3a 0x3e 0x4a 0x4e 0x52 0x56 0x5a 0x5c 0x5e 0x60 0x66 0x6a 0x72 0x76 0x7a)))\n', ''], ['(allowx ot_rcp self (nlmsg netlink_route_socket (0x12)))\n', ''], ['(allow vendor_hal_alarm_qti_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow vendor_hal_qvrservice_qti_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow vendor_hal_sxrservice_qti_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow domain coredump_file_202504 (dir (ioctl read write create getattr setattr lock rename open watch watch_reads add_name remove_name reparent search rmdir)))\n', ''], ['(allow domain coredump_file_202504 (file (ioctl read write create getattr setattr lock append map unlink rename open watch watch_reads)))\n', ''], ['(dontaudit vendor-qti-testscripts kernel_202504 (system (ipc_info syslog_read syslog_mod syslog_console module_request module_load firmware_load kexec_image_load kexec_initramfs_load policy_load x509_certificate_load)))\n', '(dontaudit vendor-qti-testscripts kernel_202504 (system (ipc_info syslog_read syslog_mod syslog_console module_request module_load)))\n'], ['(dontaudit vendor-qti-testscripts domain (netlink_route_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_readpriv nlmsg_getneigh nlmsg)))\n(dontaudit vendor-qti-testscripts domain (netlink_tcpdiag_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg)))\n', '(dontaudit vendor-qti-testscripts domain (netlink_route_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_readpriv nlmsg_getneigh)))\n(dontaudit vendor-qti-testscripts domain (netlink_tcpdiag_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write)))\n'], ['(dontaudit vendor-qti-testscripts domain (netlink_xfrm_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg)))\n', '(dontaudit vendor-qti-testscripts domain (netlink_xfrm_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write)))\n'], ['(dontaudit vendor-qti-testscripts domain (netlink_audit_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_relay nlmsg_readpriv nlmsg_tty_audit nlmsg)))\n', '(dontaudit vendor-qti-testscripts domain (netlink_audit_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_relay nlmsg_readpriv nlmsg_tty_audit)))\n'], ['(dontaudit vendor-qti-testscripts port_type (netlink_route_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_readpriv nlmsg_getneigh nlmsg)))\n(dontaudit vendor-qti-testscripts port_type (netlink_tcpdiag_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg)))\n', '(dontaudit vendor-qti-testscripts port_type (netlink_route_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_readpriv nlmsg_getneigh)))\n(dontaudit vendor-qti-testscripts port_type (netlink_tcpdiag_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write)))\n'], ['(dontaudit vendor-qti-testscripts port_type (netlink_xfrm_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg)))\n', '(dontaudit vendor-qti-testscripts port_type (netlink_xfrm_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write)))\n'], ['(dontaudit vendor-qti-testscripts port_type (netlink_audit_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_relay nlmsg_readpriv nlmsg_tty_audit nlmsg)))\n', '(dontaudit vendor-qti-testscripts port_type (netlink_audit_socket (ioctl read write create getattr setattr lock relabelfrom relabelto append map bind connect listen accept getopt setopt shutdown recvfrom sendto name_bind nlmsg_read nlmsg_write nlmsg_relay nlmsg_readpriv nlmsg_tty_audit)))\n'], ['(allow hal_fingerprint_default su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow hal_lineage_health_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow hal_lineage_livedisplay_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow hal_lineage_powershare_server su_202504 (tcp_socket (read write accept getopt)))\n', ''], ['(allow hal_lineage_touch_server su_202504 (tcp_socket (read write accept getopt)))\n', '']]
SOURCE_HASH = '625ac2b5df60a15c8854feb6816efcc2070007283f70e4341bb7606050d413d4'
out=Path('/out')
source=out/'vendor/selinux/vendor_sepolicy.cil'
raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()==SOURCE_HASH, 'Vendor kaynak hash uyusmuyor'
text=raw.decode()
for old,new in PATCHES:
    assert text.count(old)>=1, 'Beklenen kural blogu bulunamadi'
    text=text.replace(old,new,1)
assert hashlib.sha256(text.encode()).hexdigest()=='250d7e4f4576e5d89b7cffde52592fbd71f1afb486a6e35ddc8b00e60066957f', 'Aday hash uyusmuyor'
candidate=out/'vendor_sepolicy.compat-v2.cil'
assert not candidate.exists(), 'v2 aday zaten mevcut; uzerine yazilmadi'
candidate.write_text(text)
base=Path('/linux/source/creek-tr-3.0.302.0')
inputs=[]
for part,name in [('system/system','plat'),('system_ext','system_ext'),('product','product')]:
    d=base/part/'etc/selinux'
    inputs.extend([d/f'{name}_sepolicy.cil',d/'mapping/202504.cil'])
pubsource=out/'vendor/selinux/plat_pub_versioned.cil'
pubraw=pubsource.read_bytes()
assert hashlib.sha256(pubraw).hexdigest()==PUB_HASH, 'Public kaynak hash uyusmuyor'
rule='(allow vendor_init_202504 vendor_persist_camera_prop_202504 (property_service (set)))'
pubtext=pubraw.decode()
assert pubtext.count(rule)==1
pubcandidate=out/'plat_pub_versioned.compat-v2.cil'
assert not pubcandidate.exists(), 'Public aday zaten mevcut'
pubcandidate.write_text(pubtext.replace(rule,'; Removed conflicting legacy camera property setter'))
inputs += [pubcandidate,candidate]
odm=out/'odm/selinux/odm_sepolicy.cil'
if odm.is_file() and odm.read_text().strip(): inputs.append(odm)
assert all(p.is_file() for p in inputs)
print('Kaynak dogrulandi. Neverallow kontrolleriyle derleniyor...',flush=True)
policy=out/'combined-compat-v2.policy'
log=out/'compile-compat-v2.log'
with log.open('w') as f:
    r=subprocess.run(['secilc','-v','-m','-M','true','-G','-c','30',*map(str,inputs),'-o',str(policy),'-f',str(out/'file_contexts-compat-v2')],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:
    print('\n'.join(log.read_text().splitlines()[-100:]))
    raise SystemExit(r.returncode)
print('NEVERALLOW DAHIL DERLEME BASARILI')
print('SHA256:',hashlib.sha256(policy.read_bytes()).hexdigest())
print('CALISMA AGACINA KURULMADI. TELEFONA YAZILMADI.')
