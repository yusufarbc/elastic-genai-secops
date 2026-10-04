# Elastic-GenAI-SOC 🛡️🧠

**Next-Generation Unified NOC/SOC Platform powered by Elastic Stack, Windows Defender & GenAI (MCP)**

`Elastic-GenAI-SOC`; geleneksel ve yüksek maliyetli güvenlik operasyonlarını, **Açık Standartlar (MCP)** ve **Üretken Yapay Zeka (GenAI)** gücüyle yeniden tanımlayan bir **AI-Driven SecOps** projesidir.

## 🚀 Proje Vizyonu

Bu proje, kurumların veya bireysel araştırmacıların **lisans maliyeti ödemeden**, kurumsal seviyede bir "Gözlem ve Müdahale" (Observability & Response) yeteneğine sahip olmasını amaçlar.

**Neden Elastic-GenAI-SOC?**
* **Unified Operations:** NOC (Sistem Sağlığı) ve SOC (Siber Güvenlik) verileri tek bir Elastic Dashboard üzerinde birleştirilir.
* **GenAI Integration:** Yerel LLM (Large Language Model), **Model Context Protocol (MCP)** aracılığıyla Windows Defender'ı yöneten bir "Güvenlik Analisti" gibi çalışır.
* **Cost-Effective Architecture:** Elastic Basic License + Native Windows Defender kullanır. Ekstra EDR lisansı gerektirmez.

## 🏗️ Mimari (The Stack)

| Bileşen | Teknoloji | Görev |
| :--- | :--- | :--- |
| **Gözlem (Observer)** | **Elastic Agent & Fleet** | Sistem metriklerini ve `Windows Defender/Operational` loglarını toplar. |
| **Koruma (Protector)** | **Windows Defender** | Yerel tehdit engelleme ve karantina işlemlerini yapar. |
| **Zeka (Brain)** | **Local LLM (Llama 3 / Qwen)** | Olayları analiz eder ve aksiyon kararı verir. |
| **Protokol (Bridge)** | **Python & MCP** | LLM'in güvenli bir şekilde Defender komutlarını (Scan, Status) çağırmasını sağlar. |

## ⚙️ Kurulum ve Kullanım


### Gereksinimler
* Python 3.10+
* Windows 10/11 veya Server 2019+
* Elastic Stack (Self-Hosted veya Cloud)

## 📚 Dokümantasyon
**🚀 Başlangıç Noktası:**
Tüm kurulum sürecini (Kubernetes -> Elastic -> GPO -> AI) adım adım anlatan tek bir rehber hazırladık. Lütfen buradan başlayın:

👉 **[MASTER INSTALL GUIDE (Adım Adım Kurulum)](docs/MASTER_INSTALL_GUIDE.md)**

---

### Referans Dökümanlar (Detaylar)
Eğer belirli bir konuda derinleşmek isterseniz:
*   [📄 Mimari ve Kaynaklar](docs/ARCHITECTURE.md)
*   [☸️ Kubernetes Cluster Kurulumu](docs/KUBERNETES_SETUP.md)
*   [🛡️ GPO ve Log Politikaları](docs/GPO_CONFIGURATION.md)
*   [🤖 AI Server Deployment](docs/DEPLOYMENT.md)
*   [☸️ Elastic Stack YAML Detayları](docs/SETUP_GUIDE.md)




### 1. Kurulum
Depoyu klonlayın ve bağımlılıkları yükleyin:
```bash
git clone [https://github.com/kullaniciadi/Elastic-GenAI-SOC.git](https://github.com/kullaniciadi/Elastic-GenAI-SOC.git)
cd Elastic-GenAI-SOC
pip install -r requirements.txt

Elastic-GenAI-SOC/
│
├── docs/                      # Dokümantasyon ve diyagramlar
├── elastic/                   # Fleet politikaları ve KQL sorguları
├── src/                       # Python MCP Sunucusu kodları
│   └── server.py
├── scripts/                   # Yardımcı PowerShell araçları
├── .gitignore
├── requirements.txt
└── README.md
