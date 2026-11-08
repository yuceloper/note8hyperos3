# V15 ilk cihaz sonucu — 2026-11-08

Kullanıcının yerel üretimde bildirdiği vendor-ginkgo-v15.img SHA256: eb8c211c391d6753c81287d02112c50949667f7ca4665da0bd08f9f2a16a8f31. Offline builder tamamlandı; V14 temel imajı ve modem düzeltmesi korunuyor. Kullanıcı V15 yükleme talimatından sonra aşağıdaki sonucu bildirdi.

## Doğrulanan ilk davranış

- Bluetooth açılıyor ve çevredeki cihazları tarıyor (kullanıcı testi).
- lshal, vendor.qti.hardware.btconfigstore@2.0::IBTConfigStore/default için gerçek kayıtlı servis satırı gösteriyor: PID1155, thread1155. Yalnız manifestteki DM satırı değil, FC/PID satırı mevcut.
- com.android.bluetooth PID2983 olarak çalışıyor.
- Son 3000 all-buffer log satırında BLE_START_TIMEOUT, BLE_STOP_TIMEOUT, ConfigStore registration error ve ConfigStore wait filtreleri sonuç vermedi. Bu, tüm açılış kaydının hatasız olduğu iddiası değil.

V14'teki kayıtlı olmayan ConfigStore ve Bluetooth timeout/restart döngüsüne karşı V15'in ilk cihaz sonucu olumlu. Süreç PID'sinin beş dakika boyunca sabit kaldığı henüz ölçülmedi.

## Kullanıcı gözlemi

Telefonun toparlanması daha kısa sürmüş; şebeke yaklaşık 15 saniyede gelmiş. Önceki yaklaşık bir dakika gözlemine göre iyileşme var; kronometre/aynı başlangıç noktasıyla çoklu açılış ölçümü yapılmadı. Şebeke süresindeki değişimin yalnız Bluetooth yamasından kaynaklandığı kesinleştirilmedi.

## Eksik doğrulamalar

Eşleştirme, A2DP müzik, HFP çağrı/mikrofon, BLE bağlantısı, Wi-Fi ile birlikte kullanım, uyku/uyanma ve beş açılış testi bekliyor. Telefon/SMS/mobil veri regresyonları da tekrar denenmeli. İmaj hazır/ilk cihaz testi olumlu; günlük kullanıma hazır veya kusursuz ROM olarak sınıflandırılmıyor.

## Sonraki hata

Önceki V14 startup kaydında Find Device PID4112'nin MTD AIDL/HIDL servis araması 2443 audit satırı oluşturuyordu. Bu sorun V15 ile hedeflenmedi. Gerçek MTD servisi, VINTF, dosya/servis contextleri ve storage erişimi birlikte incelenmeli; default service türlerine genel izin veya Find Device'a sahte başarı eklenmemeli. Kimliği belirlenemeyen init alt süreç SIGABRT ve kamera uyumsuzluğu da açık.
