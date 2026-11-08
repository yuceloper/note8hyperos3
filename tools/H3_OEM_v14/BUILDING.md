# V14 vendor imajı hazırlama

build_vendor.py, orijinal Lineage vendor.img üzerinde değişiklik yapmadan ayrı bir test imajı üretir. Yalnızca beklenen e8f49bb8c25cb983caee5249ba08b4c72c74fa68600538d13e5fa5e69fd505f6 imajını ve 68f026e5d2a3da6c2ddb451d847e6624ffb19ce43f7a767d8bd85ec20417ef7b kütüphane adayını kabul eder. debugfs, e2fsck ve Python 3.11+ gerekir; prepare.py aynı dizinde bulunmalı.

Hedef dosya /lib64/libril-qc-hal-qmi.so. debugfs yalnızca salt okunur kullanılır. bmap ile 40 baytlık dosya bölgesinin fiziksel blok konumu bulunur. Orijinal baytlar hem çıkarılmış kütüphanede hem fiziksel imaj bölgesinde doğrulanır. Kaynak imaj ayrı .partial dosyasına kopyalanır ve yalnız bu veri bölgesi değiştirilir. Dosya silme/ekleme, inode yeniden oluşturma veya filesystem metadata yazımı yapılmaz.

Kontroller: tam kaynak imaj hash'i; kaynak kütüphanenin hash'i ve exact patch; ham ext4 magic/blok boyutu; bigalloc ve verity/encryption inode flag reddi; IMA/EVM etiketi reddi; kaynak ve aday salt okunur e2fsck; tam imaj karşılaştırmasıyla yalnız izinli 37 bayt değerinin değişmesi; stat ve ea_list çıktılarının aynı olması; aday imajdan geri çıkarılmış kütüphane hash'i; kaynak imajın sonunda hâlâ aynı olması. Başarısızlıkta .partial dosyası flash adayı sayılmaz. Mevcut çıktı dizini reddedilir.

Başarıda vendor-ginkgo-v14.img, validation.json ve iki e2fsck kaydı oluşur. İmaj boyutu kaynakla aynı kalır. Çıktı hash'i validation.json ve terminalde bulunur. ADB/fastboot çalıştırılmaz; system, boot veya veri bölümü değişmez.

Yerel doğrulama: 64 MiB ext4 fixture içine gerçek 33,462,032 baytlık kaynak kütüphane ve security.selinux xattr yerleştirildi. Test harness yalnız fixture imajının allowlist hash'ini değiştirdi; üretim CLI'da hash override seçeneği yok. Aday geri okuma hash'i doğru; yalnız 37 bayt değeri değişti; inode ve SELinux xattr aynı; iki e2fsck temiz; mevcut çıktı üzerine yazma reddedildi. Bu sonuç kullanıcının gerçek vendor imajının yerini tutmaz; gerçek imajda bütün kontroller tekrar çalışır.

Bu doğrulama AVB imzasını yeniden üretmez ve cihaz açılış testi değildir. Kaynak imajın hash alanlarını değiştiren bir patch, mevcut AVB digest'i varsa onu geçersiz kılabilir. Flash öncesi çalışan boot/fstab doğrulama düzeni, kurulu vendor ile kaynak eşleşmesi ve vendor geri dönüş kopyası ayrıca doğrulanmalı. V13 system/boot korunmalı. PIN, ANR, arama/ses/SMS/veri ve SIM slot regresyonları cihazda ölçülmeden başarı ilan edilmez.
