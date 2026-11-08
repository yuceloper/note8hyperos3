# V14: yalnızca Xiaomi 0x802aa için desteklenmiyor cevabı

Durum: OFFLINE CANDIDATE — cihazda denenmedi, vendor imajına kurulmadı. İlgili önceki analiz: PR #3.

## Girdi

Lineage ginkgo vendor imajından çıkarılmış /lib64/libril-qc-hal-qmi.so:

- Boyut: 33462032 bayt
- Kaynak SHA256: 81dfdda1848b39995ccabe99a04c616972f6330372ce69c3ed724781bc3a82d8
- Aday SHA256: 68f026e5d2a3da6c2ddb451d847e6624ffb19ce43f7a767d8bd85ec20417ef7b

## Kanıt ve hedef

Donor Telefon'un XTS başlangıcı QOEMHOOK dış kimliği 0x802aa üzerinden Xiaomi iç sorgularını gönderiyor. Canlı kayıtta sorgular 5 saniyelik bekleme, yerel Runtime Exception ve -2 ile sonuçlanıyor; ana thread ANR'si oluşuyor.

Vendor OemHookImpl::oemHookRawRequest (VA 0x1b50bac, 3272 bayt) tanıdığı istekleri doğrudan işler. Diğerleri 0x1b51820 üzerinden processIncomingOemhookMessage yoluna geçer. 0x802aa bu doğrudan listede yok. qcril_qmi_oem_events_init içindeki 62 başlangıç event anahtarı arasında da yok. Bu, incelenen ikilide bu komut için kayıtlı bir işleyici bulunmadığını destekler; bütün çalışma zamanı durumları cihaz testi olmadan kanıtlanamaz.

## Değişiklik

0x1b51820–0x1b51847 arasındaki 40 bayt yeniden düzenlenir:

```asm
sub w8, w9, #0x80, lsl #12
cmp w8, #0x2aa
b.eq 0x1b50cb0
ldr x8, [sp, #0x1e0]
ldr w0, [x8, #0x20]
ldr w1, [sp, #0x214]
ldr x2, [sp, #0x1f0]
ldr x3, [sp, #0x200]
bl 0x1d16d90
b 0x1b50e90
```

Fallback bloğunun tek doğrudan giriş dalı 0x1b512c8; buraya gelindiğinde w9 istek kimliğini taşıyor. Yalnızca 0x802aa, mevcut boş-vector REQUEST_NOT_SUPPORTED (6) callback bloğuna yönlenir. Orijinal serial korunur. Diğer kimlikler aynı instance, serial, data ve length ile orijinal processIncomingOemhookMessage çağrısına gider, ardından mevcut Return<void> constructor/epilogue kullanılır. Desteklenen doğrudan istek dalları değiştirilmez.

Yeni başarılı modem cevabı, üretici kimliği veya chipset bilgisi uydurulmaz. Bu Xiaomi uzantısını destekli hale getirmez; desteklenmeyen isteğin uzun beklemek yerine hata almasını amaçlar. 0x802aa altındaki bütün iç mesajlar bu kapsamda; gelecekte gerçek destek eklenirse bu aday kaldırılmalı.

## Doğrulama

- Beş vendor dosyasının manifest SHA256 değerleri doğrulandı.
- ELF boyutu değişmedi. Yalnızca .text değişti; dynamic/linker metadata ve diğer section içerikleri aynı.
- 40 baytlık bölgede 37 bayt değeri değişti; kalan dosya aynı.
- Capstone ile yeni talimatlar ve branch hedefleri doğrulandı.
- Unicorn ARM64 emülasyonunda fallback girişinden 135 kimlik × 2 instance = 270 senaryo geçti. Hedef kimlik mevcut callback çağrısına serial=1004, error=6 ile ulaşıyor. Diğer kimliklerde eski legacy argümanları/return yolu ve SP korundu. Dış fonksiyonlar/callback nesnesi fixture ile taklit edildi: gerçek HIDL/Binder/modem entegrasyonu test edilmedi.
- Hazırlama betiği exact candidate hash'i üretir; yanlış/truncated/already patched girdiyi ve mevcut çıktı dizinini reddeder. python -O altında kontroller aktif.

## Yerel hazırlama

Python 3.11+; adb veya Docker gerektirmez. İmajdan çıkarılmış kaynak dosya korunur:

```sh
python3 prepare.py --source out/vendor-oem-offline/lib64/libril-qc-hal-qmi.so --out out/oem-v14-offline
```

Bu komut yalnızca aday kütüphane ve validation.json yazar. İmaj kurucusu veya flash aracı değildir. Çıktı dosyasının Mac metadata'sı telefona taşınacak metadata olarak kullanılmamalı; ileride vendor imajına kurulum inode izin/sahiplik/SELinux etiketini koruyup doğrulamalı.

## Cihaz testi öncesi ve sonrası

Kurulu vendor'ın kullanılan Lineage imajıyla eşleşmesi, vendor yedeği/geri dönüş ve mevcut V13 system/boot korunması doğrulanmalı. Bu değişiklik yalnızca vendor/lib64 dosyasına ait; V13 performans yamaları veya APK imzaları değiştirilmez.

Beş açılışta Telefon ANR'si, PIN ekranı ve sinyal süreleri ölçülmeli. Gelen/giden arama, iki yönlü ses, SMS, veri ve SIM slotları denenmeli. Callback hatasının Telefon tarafından güvenle işlendiği, crash loop veya yeni OEM hata döngüsü oluşmadığı kontrol edilmeli. Bu ölçümler olmadan V14 başarılı/stabil ilan edilmez.
