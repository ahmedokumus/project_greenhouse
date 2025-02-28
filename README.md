# 🌱 Sera Kontrol Sistemi

Sera Kontrol Sistemi, akıllı seracılık için Siemens PLC sistemleri ve yapay zeka teknolojilerini birleştiren kapsamlı bir otomasyon çözümüdür. Sistem, sera içindeki çeşitli sensörlerden (sıcaklık, nem, toprak nemi, CO2, ışık) veri alır, bu verileri yapay zeka ile analiz eder ve optimum sera koşullarını sağlamak için gerekli ekipmanları otomatik olarak kontrol eder.

## 📋 Özellikler

- **Gerçek Zamanlı Sensör Takibi**: Sıcaklık, nem, toprak nemi, CO2 ve ışık seviyelerini sürekli izleme
- **AI Tabanlı Karar Verme**: OpenAI API entegrasyonu ile sensör verilerinin analizi ve akıllı kontrol önerileri
- **Otomatik Ekipman Kontrolü**: Havalandırma, ısıtma, soğutma, sulama gibi ekipmanların duruma göre otomatik kontrolü
- **Esnek Yapılandırma**: Farklı PLC sistemleri ve sensör yapılandırmaları için kolay uyarlama
- **Türkçe Dil Desteği**: Hem kod hem de yapay zeka çıktıları için tam Türkçe dil desteği

## 🔧 Kurulum

### Gereksinimler

- Python 3.8 veya üzeri
- Siemens PLC sistemi (S7-300, S7-400, S7-1200 veya S7-1500)
- İnternet bağlantısı (AI servisi için)

### Çevresel Değişkenler

`.env` dosyası oluşturun ve aşağıdaki değişkenleri ayarlayın:

```
BASE_URL=<ai_servisi_api_url> # Opsiyonel, eğer varsayılan OpenAI url'inden farklı ise
GEMINI_API_KEY=<api_anahtarı>
GEMINI_MODEL=<model_adı>
```

## 🚀 Kullanım

1. PLC sisteminizi yapılandırın ve sensörleri bağlayın
2. `.env` dosyasını gerekli anahtarlarla düzenleyin
3. `main.py` dosyasındaki PLC yapılandırmasını kontrol edin:

```python
plc_config = {
    "ip_address": "192.168.0.1",  # PLC IP adresi
    "rack": 0,                    # PLC rack numarası
    "slot": 1,                    # PLC slot numarası
    "monitoring_interval": 60     # Kontrol aralığı (saniye)
}
```

4. Programı çalıştırın:

```bash
py main.py
```

## 🧩 Sistem Mimarisi

Sistem üç ana bileşenden oluşur:

1. **PLCConnection**: Siemens PLC ile iletişim kurar, sensör verilerini okur ve ekipmanları kontrol eder
2. **AIAgent**: OpenAI API'sini kullanarak sera verilerini analiz eder ve kontrol önerileri üretir
3. **SeraKontrolSistemi**: PLC bağlantısı ve AI analizini koordine eder, düzenli aralıklarla izleme yapar

## 📟 PLC Konfigürasyonu

### Sensör Adresleri (Bellek Alanları)

- Işık: MD0 (Float)
- CO2: MD2 (Float)
- Toprak Nemi: MD4 (Float)
- Nem: MD6 (Float)
- Sıcaklık: MD8 (Float)

### Ekipman Çıkışları

- Havalandırma: Q0.0
- Gölgelendirme: Q0.1
- Isıtıcı: Q0.2
- Nemlendirici: Q0.3
- Sulama: Q0.4
- Drenaj: Q0.5
- CO2 Tüpü: Q0.6
- LED Aydınlatma: Q0.7

### Durum Bildirimleri (DB Alanları)

- Analiz Bilgisi: DB1.0 (String, 100 karakter)
- Analiz Bilgisi (Devam): DB2.0 (String, 100 karakter)
- Analiz Bilgisi (Devam): DB3.0 (String, 50 karakter)
- Uyarılar: DB4.0 - DB8.0 (String, her biri 100 karakter)

## 🤖 AI Analiz Detayları

Sistem aşağıdaki optimal sera koşullarını sağlamak için çalışır:

- **Sıcaklık**: 20-28°C arası
- **Nem**: %60-80 arası
- **Toprak Nemi**: %70-90 arası
- **CO2**: 800-1200 ppm arası
- **Işık**: Gün ışığına bağlı olarak değişken (sabah/öğlen yüksek, akşam düşük)

AI sistemi bu parametrelere göre ekipmanların ne zaman açılıp kapanacağına karar verir.

## 📝 Örnek AI Analizi

```json
{
  "analiz": "Sera koşulları genel olarak iyi durumda. Sıcaklık optimal aralıkta, nem biraz düşük, CO2 seviyesi normal.",
  "eylemler": [
    {
      "ekipman": "Nemlendirici",
      "durum": true,
      "neden": "Nem seviyesi %55 ile optimal değerin altında"
    },
    {
      "ekipman": "Gölgelendirme",
      "durum": false,
      "neden": "Işık seviyesi yüksek değil"
    }
  ],
  "uyarılar": [
    "Öğleden sonra sıcaklık artışı bekleniyor, havalandırma hazırlığı yapılmalı"
  ]
}
```

## 🔍 Hata Ayıklama

Sistem, detaylı günlük kayıtları tutar. Sorun giderme için logları kontrol edin:

```
2025-02-28 14:22:15 - sera_ai_agent - INFO - Sera Işık Değeri: 856.2
2025-02-28 14:22:15 - sera_ai_agent - INFO - CO2 Seviyesi: 950.5
2025-02-28 14:22:15 - sera_ai_agent - INFO - Toprak Nemi: 72.3
```

## 🤝 Katkıda Bulunma

1. Bu depoyu fork edin
2. Özellik dalınızı oluşturun (`git checkout -b yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik: X özelliği eklendi'`)
4. Dalınıza push yapın (`git push origin yeni-ozellik`)
5. Bir Pull Request oluşturun

## 👥 İletişim

Sorularınız veya önerileriniz için lütfen [issue açın](https://github.com/kullaniciadi/sera-kontrol-sistemi/issues) veya doğrudan iletişime ahakanokumuss@gmail.com maili ile geçin.
