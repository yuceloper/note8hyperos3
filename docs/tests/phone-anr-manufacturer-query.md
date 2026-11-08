# Telefon ANR: üretici kimliği OEM sorgusunda bekleme

2026-11-08 kullanıcı DropBox ANR raporunun incelemesi. Ham kişisel içerik repoya alınmadı.

Üç telefon ANR raporu: 2026-11-07 15:02:08, 2026-11-08 05:43:06 ve 05:54:27. Tümünde ana iş parçacığı aynı zincirde:

```
XtsApp$1.handleMessage
XtsApp.onHookDone
XtsApp.onInitVerInfo
ModemUtils.getManufacturerId
MiRilHook.getXiaomiManufacturerId
MiRilHook.onHookCommonMsgSync
MiRilHookAidlQcom.sendQcRilHookMsgSync
IQcrilMsgTunnel.sendOemRilRequestRaw
BinderProxy.transactNative
```

Son raporda native Binder transact/ioctl beklemesi var. Bekleyen yayının hedefi StkCmdReceiver olsa da main thread STK kodunda değil; telefonun Xiaomi açılış OEM sorgusunda. Bu nedenle STK kaldırma/devre dışı bırakma bu kanıtla gerekçelendirilmez.

Kanıtlanan: senkron OEM çağrısı telefon ana iş parçacığını bloke ediyor; işlem ANR nedeniyle öldürülüyor. Kanıtlanmayan: RIL tünelinin alt tarafında hangi HAL/modem işleminin yanıtı geciktirdiği, sorgunun tüm yan etkileri, kesin düzeltme. V13'ten önceki 11-07 kaydında da görüldüğünden V13'e özgü bir başlangıç sorunu değil.

Sonraki adım: yüklü telefon APK'sında XtsApp.onInitVerInfo çağrılarını ve varsayılan değer davranışını incele. Gerekirse tünel uygulamasının Binder işleyicisi de karşılaştırılacak. Modem verisine kimlik uydurulmaz; genel OEM hook devre dışı bırakılmaz. Değişiklik öncesi kaynak hash'i, yedek ve geri alma zorunlu. Henüz yeni aday hazırlanmadı.
