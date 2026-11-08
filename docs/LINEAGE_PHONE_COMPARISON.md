# Ginkgo Lineage telefon/OEM tüneli karşılaştırması

2026-11-08. Kullanıcının lineage-phone-reference.tar.gz girdisi incelendi. Manifestteki üç dosya hash'i doğrulandı. İki tünel yolu aynı APK içeriğine sahip; iki farklı implementasyon değil. APK veya ROM değiştirilmedi.

## Girdiler

| Dosya | SHA256 |
| --- | --- |
| Lineage TeleService.apk | 749484662c6eb025cb065d092ea113f89cc4a718fd9ae7bbe2bbb1e97b74183a |
| Lineage qcrilmsgtunnel.apk (iki yol aynı içerik) | e6bb1958f3fe81d4f298a2fe2fb1da9a7719a127dd19de2039ed33915a5b8e81 |
| HyperOS qcrilmsgtunnel.apk | 0f5a015cc4063e25c54234928250f1ccc37f40fcafb4cc381124da2130d311d1 |

## DEX bulguları

- Lineage TeleService içindeki 4833 sınıf arasında Xiaomi namespace / XtsApp yok. Bu, donor TeleService'deki Xiaomi XTS açılış sorgularının Lineage'da aynı biçimde çalışmadığını gösterir; telefon framework'lerinin bütünüyle eşdeğer olduğunu göstermez.
- Lineage tüneli 40 sınıf; HyperOS tüneli 268 sınıf içeriyor. Sınıf sayısı performans ölçüsü değildir.
- İkisi de uygulamalar arası IQcrilMsgTunnel.sendOemRilRequestRaw(byte[], byte[], int) arayüzüne sahip.
- Lineage vendor.qti.hardware.radio.qcrilhook@1.0::IQtiOemHook HIDL servisini kullanır. HyperOS'un mevcut cihazda seçtiği HIDL yolunda da oemHookRawRequest(int, ArrayList) çağrısı var. Vendor AIDL'i zorlamak için kanıt yok.
- Lineage QcrilMsgTunnelIfaceManager.sendRequest, result dolana kadar Object.wait() ile süresiz bekler.
- HyperOS aynı bekleme noktasında command 1 için uptime tabanlı 5000 ms kontrolü ekler; diğer command yolunda süresiz bekleme kalır. wait(5000) kullanıldığı için uyandırılma/zamanlama koşullarına göre tam 5000 ms üst sınırı garanti edilmez.
- Dolayısıyla Lineage tünelini doğrudan almak mevcut Xiaomi OEM sorguları cevapsız kalırsa beklemeyi sınırsız hale getirebilir. Bu karşılaştırma APK değişimini desteklemiyor.

## Canlı kayıtla sınırlandırılmış sonuç

v13-boot-live-20261108-055256 logcat içinde seri 1000–1008 OEM sorgu girişleri görülüyor. processOemHookResponse mesajı, Calling HIDL debug mesajı veya remote-error mesajı bu yakalamada bulunmadı. Debug mesajının yokluğu çağrının yapılmadığını kanıtlamaz. HIDL callback implementasyonu mevcut ve cevap handler'ına yönlendiriyor; alt katmanın neden cevap vermediği bu kayıtla kesinleştirilemez. Servis kaydı/callback kurulumu, gerçek OEM isteğinin başarılı olduğu anlamına gelmez.

Doğrulanmış sorun: donor Telefon ana Looper'ında senkron Xiaomi OEM başlangıç sorguları ve buna eşlik eden ANR. Alt neden için modem isteğinin desteklenmemesi, cevap/callback kaybı veya başka bir uyumluluk sorunu henüz ayrıştırılmadı. Lineage APK'sının daha eski/uygun olması tek başına bunu çözmez.

## Karar

V13 korunur. Lineage TeleService veya tünel APK'sı doğrudan değiştirilmez. Xiaomi OEM sorguları için uydurma manufacturer/chip değerleri verilmez. İmza/shared-UID engeli çözülmeden donor APK yaması flash adayı yapılmaz. Ana iş parçacığını bekletmeyen XTS başlangıç tasarımı ve gerçek OEM cevap yolunun incelenmesi ayrı işlerdir; hiçbirisi henüz uygulanmış düzeltme değildir.

## Sonraki doğrulama

Önce OEM istek kimliği ve vendor cevabı uçtan uca eşlenmeli; mevcut HIDL callback kaydı ve aynı servis örneğinin başka istemci tarafından yeniden bağlanma ihtimali kanıt üzerinden incelenmeli. Telefon ANR düzeltmesi; PIN/sinyal zamanları, arama/ses/SMS/veri ve ortak UID izinlerinin regresyon testiyle doğrulanmalı. Körlemesine APK değişimi veya ortak timeout küçültmesi kabul ölçütü değildir.
