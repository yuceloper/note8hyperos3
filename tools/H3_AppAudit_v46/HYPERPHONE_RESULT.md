# Donor communication component findings

Reviewed user archives components-v1.tar.gz and hyperphone-reference.tar.gz on 2026-11-11.

Direct binary manifest decoding (without parsing resources.arsc) identifies HyperPhone APK SHA256 852191540cdb02c675c1a1132b9adf731544bb62a3d92dae9ac71e51c25a664c as com.xiaomi.phone, versionName15.0.2/versionCode38, sharedUserId android.uid.phone. It declares network settings activities, MiTelephonyService in process com.android.phone, telephony jobs and satellite services. No InCallService, ACTION_DIAL activity or launcher dialer UI is declared. It cannot replace the Google dialer/answer UI; preserve this phone backend.

The local donor and work-tree mi_ext Contacts.apk, Dialer.apk, MtkContacts.apk and messaging.apk paths examined are zero-byte files. They are not usable APKs. MiuiMmsGlobal.apk is a valid com.android.mms package at mi_ext/product/priv-app/MiuiMmsGlobal (31861352 bytes, SHA256283ec662d986a9ba22f2f3e0488a2305274e2217916918f649eba8f01daf6330). It is not registered as a live package per V46 runtime dump. Google dialer/contacts/messages base APK hashes match between local donor mi_ext and effective port product paths. Live Google Phone has a userdata update (245 vs system192); this is a separate variable from source provenance.

Limits: old aapt still failed resource parsing for many nonzero APKs, including HyperPhone; its error text is not evidence of APK corruption. Exact regional activation rules are not established by nearby whitelist/permission snippets. Local donor-tree findings are not an independent audit of pristine downloaded partition images. Do not call the missing Xiaomi UI an accidental port deletion from this evidence.

Current donor contents do not provide a verified ready-to-install Xiaomi dialer/contacts UI set. A compatible external regional set and its signatures/dependencies must be identified before an offline integration candidate. Never uninstall Google Phone or reassign roles to com.xiaomi.phone on the basis of the HyperPhone filename. Incoming-call UI remains an unresolved blocker; V45 continuous capture is still pending.
