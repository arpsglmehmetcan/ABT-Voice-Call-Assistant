# Sesli Çağrı Asistanı (Voice Call Assistant)

Bu proje, e-ticaret müşteri hizmetleri için geliştirilmiş Python tabanlı bir REST API servisidir. Kullanıcılardan gelen sesli soruları metne çevirir, AI destekli yanıtlar üretir ve JSON formatında döndürür.

## 🎯 Proje Özeti

**Senaryo**: Bir e-ticaret şirketinin temel müşteri hizmetleri sorularını yanıtlayan sesli asistan prototipi.

**Temel İşlevler**:
- Sesli soruları metne çevirme (Speech-to-Text)
- AI destekli müşteri hizmetleri yanıtları üretme
- İsteğe bağlı: Yanıtları seslendirme (Text-to-Speech)

## 🏗️ Sistem Mimarisi

```
[Ses Dosyası] → [Whisper STT] → [LLM] → [JSON Yanıt] → [TTS (Opsiyonel)]
```

### Kullanılan Teknolojiler

- **Backend Framework**: Flask
- **Speech-to-Text**: OpenAI Whisper
- **LLM**: Mistral-7B / LLaMA (Hugging Face, Together.ai, Replicate)
- **Text-to-Speech**: Coqui XTTS, ElevenLabs (opsiyonel)

## 📁 Proje Yapısı

```
voice-assistant/
├── app.py                 # Ana Flask uygulaması
├── llm_service.py         # LLM entegrasyonu
├── tts_service.py         # Text-to-Speech servisi
├── config.py              # Konfigürasyon ayarları
├── requirements.txt       # Python bağımlılıkları
├── .env.example          # Örnek environment dosyası
├── README.md             # Bu dosya
├── uploads/              # Yüklenen ses dosyaları (geçici)
├── responses/            # Üretilen ses yanıtları
└── tests/
    ├── test_app.py       # Unit testler
    └── test_audio/       # Test ses dosyaları
```

## 🚀 Kurulum

### 1. Depoyu Klonlayın

```bash
git clone https://github.com/username/voice-assistant.git
cd voice-assistant
```

### 2. Virtual Environment Oluşturun

```bash
# Python 3.8+ gerekli
python -m venv venv

# Aktivasyon (Windows)
venv\Scripts\activate

# Aktivasyon (Linux/Mac)
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

**Not**: Whisper ilk çalışmada model dosyalarını (~150MB) otomatik indirecektir.

### 4. Environment Değişkenlerini Ayarlayın

`.env` dosyası oluşturun:

```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin:

```env
# Flask ayarları
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Whisper model (tiny, base, small, medium, large)
WHISPER_MODEL=base

# LLM API anahtarları (opsiyonel - yerel simülasyon kullanılabilir)
HUGGINGFACE_API_KEY=your-huggingface-key
TOGETHER_API_KEY=your-together-key
REPLICATE_API_KEY=your-replicate-key

# TTS API anahtarları (opsiyonel)
ELEVENLABS_API_KEY=your-elevenlabs-key

# Sunucu ayarları
PORT=8000
DEBUG=true
```

### 5. Servisi Başlatın

```bash
python app.py
```

Servis `http://localhost:5000` adresinde çalışmaya başlayacaktır.

## 📡 API Kullanımı

### Ana Endpoint: `/ask_assistant`

**Method**: POST  
**Content-Type**: multipart/form-data

**Parametre**:
- `audio_file`: Ses dosyası (.wav, .mp3, .mp4, .m4a, .flac, .ogg)

**Örnek İstek**:

```bash
curl -X POST \
  http://localhost:5000/ask_assistant \
  -F "audio_file=@test_audio.wav"
```

**Örnek Yanıt**:

```json
{
  "transcribed_text": "Siparişim ne zaman gelecek?",
  "assistant_response": "Siparişiniz kargoya verilmiş olup, 2-4 iş günü içinde teslim edilmesi beklenmektedir.",
  "response_audio_url": "/responses/response_12345.wav"
}
```

### Diğer Endpointler

#### Sağlık Kontrolü
```bash
GET /health
```

#### Ana Sayfa
```bash
GET /
```

#### Ses Yanıtları
```bash
GET /responses/<filename>
```

## 🔧 Detaylı Konfigürasyon

### Whisper Model Seçimi

Whisper modelleri performans ve kalite açısından farklılık gösterir:

- `tiny`: En hızlı, düşük kalite (~39 MB)
- `base`: Dengeli performans (~74 MB) **[Varsayılan]**
- `small`: İyi kalite (~244 MB)
- `medium`: Yüksek kalite (~769 MB)
- `large`: En iyi kalite (~1550 MB)

### LLM Entegrasyonu

#### 1. Hugging Face Integration

```python
# .env dosyasına ekleyin
HUGGINGFACE_API_KEY=your-token-here
```

Hugging Face hesabınızdan ücretsiz API token alabilirsiniz.

#### 2. Together.ai Integration

```python
# .env dosyasına ekleyin
TOGETHER_API_KEY=your-api-key-here
```

Together.ai'dan API anahtarı alın ve Mistral modellerine erişim sağlayın.

#### 3. Replicate Integration

```python
# .env dosyasına ekleyin
REPLICATE_API_KEY=your-api-token-here
```

### TTS (Text-to-Speech) Konfigürasyonu

#### ElevenLabs (Önerilen)

```python
# .env dosyasına ekleyin
ELEVENLABS_API_KEY=your-api-key-here
```

#### Coqui XTTS (Ücretsiz Alternatif)

```bash
pip install TTS
```

Yerel Coqui XTTS kurulumu için `tts_service.py` dosyasındaki yorum satırlarını açın.

## 🐳 Docker ile Çalıştırma

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Gerekli klasörleri oluştur
RUN mkdir -p uploads responses

# Port aç
EXPOSE 5000

# Uygulamayı başlat
CMD ["python", "app.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  voice-assistant:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - WHISPER_MODEL=base
    volumes:
      - ./uploads:/app/uploads
      - ./responses:/app/responses
    restart: unless-stopped
```

Çalıştırma:

```bash
docker-compose up -d
```

## 🧪 Test Etme

### Unit Testler

```bash
# Testleri çalıştır
python -m pytest tests/ -v

# Coverage ile
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=html
```

### Manuel Test

```bash
# Sağlık kontrolü
curl http://localhost:5000/health

# Ses dosyası ile test
curl -X POST \
  http://localhost:5000/ask_assistant \
  -F "audio_file=@test_audio.wav"
```

### Test Ses Dosyası Oluşturma

Python ile test ses dosyası:

```python
import numpy as np
import soundfile as sf

# 3 saniyelik test sesi oluştur
sample_rate = 16000
duration = 3
t = np.linspace(0, duration, int(sample_rate * duration))
audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440 Hz ton

sf.write('test_audio.wav', audio, sample_rate)
```

## 🚀 Production Deployment

### Gunicorn ile

```bash
# Gunicorn yükle
pip install gunicorn

# Servisi başlat
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

### Nginx Konfigürasyonu

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 20M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### Environment Variables (Production)

```env
FLASK_ENV=production
SECRET_KEY=very-secure-random-key
WHISPER_MODEL=small
DEBUG=false
PORT=5000

# API Keys
HUGGINGFACE_API_KEY=your-production-key
TOGETHER_API_KEY=your-production-key
ELEVENLABS_API_KEY=your-production-key
```

## 🔍 Örnek Kullanım Senaryoları

### 1. Sipariş Durumu Sorgulama

**Ses Girdi**: "Merhaba, siparişim nerede?"  
**AI Yanıt**: "Siparişiniz kargoya verilmiş olup, 2-4 iş günü içinde teslim edilmesi beklenmektedir."

### 2. Ürün İadesi

**Ses Girdi**: "Aldığım ürünü iade etmek istiyorum."  
**AI Yanıt**: "Ürün iade işleminizi web sitemizden başlatabilirsiniz. İade süreci 14 gün içinde tamamlanır."

### 3. Kargo Bilgisi

**Ses Girdi**: "Kargo ne zaman gelir?"  
**AI Yanıt**: "Kargo süremiz şehir içi 1-2 iş günü, şehir dışı 2-4 iş günüdür."

## 🛠️ Geliştirme Notları

### Whisper Model Optimizasyonu

```python
# Daha hızlı transkripsiyon için
import whisper

model = whisper.load_model("base")
result = model.transcribe("audio.wav", fp16=False, language="tr")
```

### LLM Response Geliştirme

Daha akıllı yanıtlar için `llm_service.py`'de:

1. Daha fazla anahtar kelime ekleyin
2. Context-aware yanıtlar geliştirin
3. Gerçek e-ticaret API'leri entegre edin

### Performans Optimizasyonu

```python
# Async işleme için
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

# Background task olarak TTS
future = executor.submit(tts_service.generate_audio, text, output_path)
```

## 🔐 Güvenlik

### API Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/ask_assistant', methods=['POST'])
@limiter.limit("10 per minute")
def ask_assistant():
    # ...
```

### File Validation

```python
import magic

def validate_audio_file(file_path):
    """Validate uploaded file is actually audio"""
    file_type = magic.from_file(file_path, mime=True)
    return file_type.startswith('audio/')
```

## 📊 Monitoring ve Logging

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

logger.info("Processing request", 
           user_id=user_id, 
           file_size=file_size,
           transcription_time=duration)
```

### Health Check Endpoint

`/health` endpoint servise şunları kontrol eder:
- Whisper model durumu
- Disk alanı
- API bağlantıları

## 🌐 Cloud Deployment Seçenekleri

### 1. Google Colab

```python
# Colab'da çalıştırmak için
!pip install -r requirements.txt
!python app.py

# Ngrok ile public URL
!pip install pyngrok
from pyngrok import ngrok
public_url = ngrok.connect(5000)
```

### 2. Replicate Deployment

```python
# replicate.yaml
version: "1"
image: "python:3.9"
predict: "predict.py:predict"
```

### 3. Together.ai Integration

```python
import together

together.api_key = "your-key"

response = together.Complete.create(
    prompt=f"Customer service response to: {text}",
    model="mistralai/Mistral-7B-Instruct-v0.1",
    max_tokens=150
)
```

## 🎨 Frontend Entegrasyonu

### JavaScript Client Örneği

```javascript
async function sendAudioToAssistant(audioBlob) {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.wav');
    
    try {
        const response = await fetch('/ask_assistant', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        // Transkripsiyon göster
        document.getElementById('transcription').textContent = result.transcribed_text;
        
        // AI yanıtını göster
        document.getElementById('response').textContent = result.assistant_response;
        
        // Ses yanıtını çal (varsa)
        if (result.response_audio_url) {
            const audio = new Audio(result.response_audio_url);
            audio.play();
        }
        
    } catch (error) {
        console.error('Error:', error);
    }
}
```

### React Component Örneği

```jsx
import React, { useState } from 'react';

const VoiceAssistant = () => {
    const [recording, setRecording] = useState(false);
    const [response, setResponse] = useState(null);
    
    const handleRecording = async (audioBlob) => {
        const formData = new FormData();
        formData.append('audio_file', audioBlob);
        
        const result = await fetch('/ask_assistant', {
            method: 'POST',
            body: formData
        });
        
        const data = await result.json();
        setResponse(data);
    };
    
    return (
        <div>
            <button onClick={startRecording}>
                {recording ? 'Kaydı Durdur' : 'Konuşmaya Başla'}
            </button>
            
            {response && (
                <div>
                    <p><strong>Anladığım:</strong> {response.transcribed_text}</p>
                    <p><strong>Yanıtım:</strong> {response.assistant_response}</p>
                </div>
            )}
        </div>
    );
};
```

## 📈 Performans ve Ölçeklendirme

### Benchmark Sonuçları

| İşlem | Süre | Kaynak Kullanımı |
|-------|------|------------------|
| Whisper (base) | ~2-5s | 500MB RAM |
| LLM Response | ~1-3s | 200MB RAM |
| TTS Generation | ~3-8s | 300MB RAM |

### Ölçeklendirme Önerileri

1. **Redis Cache**: Sık sorulan soruların yanıtlarını önbelleğe alın
2. **Queue System**: Celery ile background processing
3. **Load Balancing**: Nginx ile multiple worker instance
4. **GPU Support**: CUDA destekli Whisper ve LLM

## 🔧 Sorun Giderme

### Yaygın Sorunlar

#### 1. Whisper Model Yüklenmiyor

```bash
# Manuel model indirme
python -c "import whisper; whisper.load_model('base')"
```

#### 2. Ses Dosyası Format Hatası

```python
# FFmpeg ile format dönüştürme
import subprocess

subprocess.run([
    'ffmpeg', '-i', 'input.mp3', 
    '-ar', '16000', '-ac', '1', 
    'output.wav'
])
```

#### 3. Memory Hatası

```python
# Model boyutunu küçültün
WHISPER_MODEL=tiny

# Veya swap alanı artırın
sudo swapon --show
sudo fallocate -l 2G /swapfile
```

### Log Seviyesi Ayarlama

```python
import logging

# Debug için
logging.basicConfig(level=logging.DEBUG)

# Production için
logging.basicConfig(level=logging.WARNING)
```

## 📝 API Dokümantasyonu

### OpenAPI/Swagger Spec

```yaml
openapi: 3.0.0
info:
  title: Voice Call Assistant API
  version: 1.0.0
  description: E-ticaret müşteri hizmetleri sesli asistan

paths:
  /ask_assistant:
    post:
      summary: Sesli soru sorma
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                audio_file:
                  type: string
                  format: binary
      responses:
        200:
          description: Başarılı yanıt
          content:
            application/json:
              schema:
                type: object
                properties:
                  transcribed_text:
                    type: string
                  assistant_response:
                    type: string
                  response_audio_url:
                    type: string
```

## 🧪 Test Senaryoları

### Test Komutları

```bash
# Sipariş durumu testi
curl -X POST http://localhost:5000/ask_assistant \
  -F "audio_file=@tests/audio/order_status.wav"

# İade testi  
curl -X POST http://localhost:5000/ask_assistant \
  -F "audio_file=@tests/audio/return_request.wav"

# Kargo bilgisi testi
curl -X POST http://localhost:5000/ask_assistant \
  -F "audio_file=@tests/audio/shipping_info.wav"
```

### Load Testing

```bash
# Apache Bench ile
ab -n 100 -c 10 -p test_audio.wav -T multipart/form-data \
   http://localhost:5000/ask_assistant

# Locust ile
pip install locust
locust -f tests/load_test.py --host=http://localhost:5000
```

## 📚 Gelişmiş Özellikler

### 1. Çoklu Dil Desteği

```python
# Whisper otomatik dil algılama
result = whisper_model.transcribe(audio_path, language=None)
detected_language = result["language"]
```

### 2. Konuşma Analizi

```python
# Duygu analizi için
from transformers import pipeline

sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="savasy/bert-base-turkish-sentiment-cased"
)

sentiment = sentiment_analyzer(transcribed_text)
```

### 3. Conversation History

```python
# Redis ile konuşma geçmişi
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

def save_conversation(user_id, question, response):
    conversation = {
        'timestamp': datetime.now().isoformat(),
        'question': question,
        'response': response
    }
    r.lpush(f"conversations:{user_id}", json.dumps(conversation))
```

## 🔄 Sürekli İyileştirme

### Model Fine-tuning

```python
# Whisper fine-tuning için domain-specific data
# Custom e-ticaret terimleri ile model eğitimi

# LLM fine-tuning
# Gerçek müşteri hizmetleri konuşmaları ile eğitim
```

### A/B Testing

```python
# Farklı LLM modellerini test etme
import random

models = ["mistral-7b", "llama-7b", "gpt-3.5-turbo"]
selected_model = random.choice(models)
```

## 📞 Destek ve İletişim

### Geliştirici Notları

- **Proje Yöneticisi**: Mehmetcan Arapisaoğlu
- **Repository**: https://github.com/username/voice-assistant

**Son Güncelleme**: 1 Eylül 2025  
**Versiyon**: 1.0.0
