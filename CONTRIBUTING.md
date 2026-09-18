# PyreSwarm Katkı Kılavuzu (Contributing)

PyreSwarm açık kaynaklı bir otonom orman yangını tespit ve sürü optimizasyon platformudur. Katkılarınızı memnuniyetle karşılıyoruz!

## Çekme İsteği (PR) Süreci
1. İlgili özelliği veya hata düzeltmesini açıklayan bir Issue açın.
2. Ana daldan (`master`) yeni bir özellik dalı oluşturun: `git checkout -b feature/yeni-ozellik`.
3. Yeni fonksiyonlar için ilgili `tests/` birim testlerini ekleyin.
4. Tüm testlerin başarıyla geçtiğini doğrulayın: `pytest tests/`.
5. PR açıklamasına çözülen sorunu ve test sonuçlarını ekleyerek gönderin.
