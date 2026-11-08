# Telefon açılışı: OEM sorgusu incelemesi

2026-11-08. Üç cihaz APK'sı kullanıcı girdilerinin SHA256 değerleriyle doğrulandı; DEX talimatları incelendi. APK değiştirilmedi, yeni ROM adayı hazırlanmadı.

## Girdiler

| Paket | Yol | SHA256 |
| --- | --- | --- |
| com.android.phone | /system/priv-app/TeleService/TeleService.apk | 6f1b70795f5ae6d93b8923d6c026b4483c1d4fcd540e1213879c7669e7a7e76f |
| com.qti.phone | /system_ext/priv-app/QtiTelephony/QtiTelephony.apk | 19ca84b605a405a2b7374b242268fd7d5749edbf381d02d6474b14a994a2f742 |
| com.qualcomm.qcrilmsgtunnel | /system_ext/priv-app/qcrilmsgtunnel/qcrilmsgtunnel.apk | 0f5a015cc4063e25c54234928250f1ccc37f40fcafb4cc381124da2130d311d1 |

## Kod ve runtime birlikte

PhoneGlobals.onCreate doğrudan XtsApp.make çağırıyor; bu çağrı çevresinde XTS'yi kapatan property/resource koşulu görülmedi. XtsApp'ın Handler'ı parametresiz Handler constructor ile oluşturuluyor; gözlenen ANR ana thread üzerinde.

XtsApp.onHookDone sırası:

1. Hook ready kaydını kaldırır; OemHookAgent ve ModemUtils hook bağlantısını kurar.
2. Hook-ready registrant'larını bilgilendirir.
3. onInitVerInfo(OemHookAgent) senkron sorgularını yapar.
4. isXtsSupported kontrolünden sonra XtsService / modem dump init yolunu çalıştırır.

onInitVerInfo sorguları: hal chip, modem chip, build profile, Xiaomi manufacturer, OEM product flag ve HAL-decoupled durumu. isXtsSupported kontrolü bu sorgulardan sonra olduğu için unsupported sonucu donmayı önleyemiyor.

ModemUtils.getManufacturerId() başlangıçta ro.vendor.radio.manufacturer_id okur. Değer 0 ise hook'lu getter getXiaomiManufacturerId çağrısına düşer. 1–5 cache değerleri bu tek sorguyu atlayabilir; fakat getBuildProfile(hook), getOemProductFlag(hook), isHalDecoupled(hook) gibi başka senkron sorgular kalır. Bu nedenle manufacturer property tek başına tam ANR çözümü değildir ve başka cihazın değerlerini kopyalamak gerekçesizdir.

QcrilMsgTunnelIfaceManager.sendRequest, command 1 için 5000 ms bekleme döngüsü içeriyor. Diğer command yolunda süresiz wait var. Canlı kayıtta ardışık sorgular yaklaşık beşer saniye sürüyor. Bu ortak timeout değerini küçültmek bütün OEM işlemlerine etki eder; genel timeout yaması önerilmiyor.

Vendor HIDL OEM hook 0 ve 1 kayıtlı; tünel uygulaması HIDL'i seçip callback bağlıyor. Yalnızca MiRilHookAidlQcom sınıf adından vendor AIDL/HIDL yanlış seçilmiş sonucu çıkarılamaz: bu sınıf uygulamalar arası Binder tünelini temsil ediyor.

Üç ANR'nin main stack'i aynı manufacturer sorgusunda; STK yayını bu sırada işlenemeyen olaydır. STK'yı kapatmak kök neden çözümü değildir.

## İmza ve dağıtım sınırı

Üç APK da Xiaomi/MIUI imzası taşıyor; V1/V2/V3 signing block mevcut (tam kriptografik doğrulama ayrıca yapılmalı). Sertifika SHA256: c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025.

Telefon sharedUserId android.uid.phone; diğer ikisi android.uid.qtiphone. APK DEX değişikliği mevcut imzayı geçersiz kılar. Başka anahtarla tek APK'yı yeniden imzalamak ortak UID/signature izin ilişkilerini bozabilir. Sistem taramasının doğrulamayı atlamasına güvenen, eski signing block'u bırakan bir dağıtım kabul edilmez. Genel signature kontrolü kapatılmayacak. Donor private signing key mevcut değil.

## Önerilen kod davranışı; henüz uygulanmadı

OEM version sorguları ve bunlara bağlı XTS ek başlatması ayrı, tek worker üzerinde çalışmalı. Telefon ana Looper'ı bu worker sonucunu beklememeli. Gerçek değerler sorgu tamamlanınca yayımlanmalı; sabit modem/manufacturer cevabı uydurulmamalı. Hook bağlantısı, temel RIL çağrıları ve STK korunmalı. Callback tekrarları/worker ömrü/timeout ve hook-disconnect senaryoları kapsanmalı. Mevcut shared-UID/signature ilişkilerini koruyan dağıtım yolu belirlenmeden bu değişiklik flash adayı olarak sunulamaz.

Alternatif araştırma: eski ginkgo OEM hook uygulamasıyla yeni istek protokolünü karşılaştırıp dar, doğru yerden uyumluluk düzeltmesi mümkün mü incelemek. Root nedenin alt taraftaki modem implementasyonunda olduğu henüz kanıtlanmadı.

## Kabul ölçütleri

Beş açılışta telefon ANR'si yok; PIN ekranı/sinyal zamanları ölçülür. Gelen/giden arama, iki yönlü ses, SMS, veri, iki SIM davranışı, OEM hook'un diğer kullanıcıları ve imza/UID izinleri test edilir. V13 performans sonucu bu telefon değişikliğinin kanıtı değildir.
