# OEM isteklerinin içerik ve hata eşlemesi

2026-11-08. V13 canlı kayıt ve orijinal APK içindeki classes.dex yeniden incelendi. TeleService APK SHA256 6f1b70795f5ae6d93b8923d6c026b4483c1d4fcd540e1213879c7669e7a7e76f; ZIP içindeki classes.dex ve classes2.dex Adler32 değerleri doğrulandı. Önceden çıkartılmış yerel DEX kopyası checksum kontrolünü geçmediği için bu incelemede kullanılmadı; APK içinden yeniden okundu. ROM değiştirilmedi.

## Paket biçimi

Canlı logdaki outgoing hex QOEMHOOK başlığı, little-endian dış istek kimliği 0x802aa (524970), payload uzunluğu ve Xiaomi iç mesajını içeriyor. MiRilHookAidlQcom.onHookSendSync de aynı dış kimliği kullanıyor. Bu bir tahmini modem yanıtı değil, gönderilen paketin çözümüdür.

| İç mesaj | Gözlenen amaç | Toplam paket |
| --- | --- | --- |
| 24 / 0x18 | ro.vendor.radio.build_profile özelliğini NULL varsayılanıyla sorma | 77 bayt |
| 151 / 0x97 | getXiaomiManufacturerId | 36 bayt |
| 105 / 0x69 | isOemProduct | 36 bayt |
| 150 / 0x96 | isHalDecoupled | 36 bayt |

İç mesaj numaraları onPkHookCommonMsg ve ilgili çağrılardaki DEX sabitleri/log metinleriyle eşleşiyor. Paket biçimini saptamak vendor'ın bunu desteklediğini kanıtlamaz.

## -2 hatasının anlamı

Örnek sıra (log zamanları):

- 05:54:29.843: yeniden başlayan Telefon build_profile OEM isteğini gönderir.
- 05:54:34.844: QcrilMsgTunnelIfaceManager sendOemRilRequestRaw: Runtime Exception yazar.
- 05:54:34.845: Telefon sendOemRilRequestRaw returns value = -2 alır.
- 05:54:34.846: sıradaki üretici kimliği sorgusu başlar.

Aynı Runtime Exception / -2 sırası sonraki sorgularda tekrar ediyor. sendRequest command 1 zaman aşımından sonra null result döndürebiliyor. sendOemRilRequestRaw bu result üzerinden exception alanına erişiyor; RuntimeException catch yolu GENERIC_FAILURE enum ordinal'inin negatifini döndürüyor. Gözlenen zamanlama bu yerel timeout/null-result yoluyla uyumlu. Yakalamada exception alt türü yazılmadığı için kesin exception sınıfı belirlenemiyor. -2 tek başına modemden gelen REQUEST_NOT_SUPPORTED cevabı değildir.

HIDL OEM cevap handler'ının INFO seviyesindeki processOemHookResponse mesajı kayıtta yok. Buna karşılık Calling HIDL debug mesajı DBG/isLoggable ile koşullu; yokluğu gönderimin yapılmadığına kanıt değildir.

## Ayrı radyo yolları

QtiRadioHidlResponse içinde NrDcParam, NrBearerAllocation, UpperLayerIndInfo ve 5gConfigInfo callback'leri görülüyor. Bu, başka vendor radyo çağrılarının cevap alabildiğini gösterir; OEM hook'un sağlıklı olduğunu veya bu cihazın 5G desteklediğini göstermez. getQtiRadioCapability / getSecureModeStatus için API not available / Radio is not supported hataları ayrı ExtTelephony yollarında. Bunları OEM timeout'un doğrudan nedeni saymak için kanıt yok.

## Uygulama kararı

Sabit manufacturer değeri, genel SELinux izni veya timeout küçültmesi uygulanmadı. Lineage tünelinin süresiz wait davranışı nedeniyle doğrudan değişimi önerilmiyor. Vendor OEM request dispatcher ve callback yolu incelenmeden paketin desteklenmediği kesinleştirilemez. XTS ana-thread blokajı ise bu alt neden açıklanmasa da somut bir yazılım kusuru olarak kalıyor; çözümü imza/shared UID ilişkilerini korumalı.
