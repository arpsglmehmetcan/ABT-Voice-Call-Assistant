"""
Voice Call Assistant API
------------------------

Ses dosyasını alır -> Whisper ile metne çevirir -> LLM'den yanıt üretir -> (ops.) TTS/placeholder üretir.

Öne çıkanlar
- UTF-8 JSON: Türkçe karakterler kaçışsız döner.
- Sağlam hata yönetimi: ASR/LLM hataları ayrıştırılır ve net mesajlar/loglar verilir.
- PEP 8 ve tip ipuçları: Okunabilirlik ve IDE desteği güçlendirildi.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Final

import whisper
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask.json.provider import DefaultJSONProvider
from werkzeug.utils import secure_filename


# =============================================================================
# Ortam ve Genel Ayarlar
# =============================================================================

# .env içeriğini (örn. WHISPER_MODEL, LOG_LEVEL) yükle
load_dotenv()

# Uygulama sabitleri (single source of truth)
MAX_UPLOAD_BYTES: Final[int] = 16 * 1024 * 1024
UPLOAD_DIR: Final[str] = "uploads"
RESPONSES_DIR: Final[str] = "responses"
ALLOWED_EXTENSIONS: Final[set[str]] = {"wav", "mp3", "mp4", "m4a", "flac", "ogg"}
WHISPER_MODEL_NAME: Final[str] = os.getenv("WHISPER_MODEL", "base")
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")


# =============================================================================
# Flask Uygulaması ve JSON Sağlayıcı
# =============================================================================

class UTF8JSONProvider(DefaultJSONProvider):
    """
    Flask'ın varsayılan JSON sağlayıcısını UTF-8 için yapılandırır.
    ensure_ascii=False ile Türkçe karakterler \u00e7 gibi kaçışsız döner.
    """
    ensure_ascii = False


def create_app() -> Flask:
    """
    Flask uygulamasını oluşturur ve yapılandırır.
    App factory deseni test ve genişletilebilirlik için faydalıdır.
    """
    app = Flask(__name__)
    app.json = UTF8JSONProvider(app)  # UTF-8 JSON
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES  # 16MB yük limiti

    # Klasörleri garanti altına al
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(RESPONSES_DIR).mkdir(parents=True, exist_ok=True)

    return app


# Uygulama örneği ve logger
app = create_app()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("voice-assistant")


# =============================================================================
# Whisper Modeli (Lazy yükleme yerine burada tek sefer)
# =============================================================================

logger.info("FFMPEG PATH: %s", shutil.which("ffmpeg"))
logger.info("Loading Whisper model: %s", WHISPER_MODEL_NAME)
try:
    WHISPER_MODEL = whisper.load_model(WHISPER_MODEL_NAME)
    logger.info("Whisper model loaded successfully")
except Exception:
    logger.exception("Failed to load Whisper model")
    WHISPER_MODEL = None


# =============================================================================
# Yardımcı Fonksiyonlar
# =============================================================================

def is_allowed_file(filename: str) -> bool:
    """
    Dosya uzantısının desteklenip desteklenmediğini döner.

    Örn: "audio.mp3" -> True, "archive.zip" -> False
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def transcribe_audio(file_path: str, language: str = "tr") -> str:
    """
    Whisper ile sesi metne çevirir.
    Hata durumunda istisna fırlatır; üst seviye handler JSON hata döndürür.

    Args:
        file_path: Diskteki ses dosyasının tam yolu.
        language: Dil ipucu. (Otomatik tespit istenirse None/"" verilebilir.)

    Returns:
        Transkriptten elde edilen temizlenmiş metin.

    Raises:
        RuntimeError: Model yoksa veya sonuç boşsa.
        Exception: Whisper/ffmpeg kaynaklı diğer hatalar.
    """
    if WHISPER_MODEL is None:
        raise RuntimeError("Whisper model not available")

    result = WHISPER_MODEL.transcribe(
        file_path,
        language=language or None,  # boş/None -> otomatik dil tespiti
        fp16=False,                  # CPU ortamlarında güvenli seçenek
        verbose=False,
    )
    text = (result.get("text") or "").strip()
    if not text:
        raise RuntimeError("Empty transcription")
    return text


def save_text_response(text: str) -> str:
    """
    TTS henüz bağlı değilse yanıtı .txt olarak kaydeder ve public URL döner.

    Returns:
        İstemcinin GET ile indirebileceği /responses/<dosya> URL'i.
    """
    path = Path(RESPONSES_DIR) / f"response_{uuid.uuid4().hex}.txt"
    path.write_text(text, encoding="utf-8")
    return f"/responses/{path.name}"


# LLM servisi (Together/HF yoksa lokal fallback)
from llm_service import llm_service  # import en sonda olmalı; döngüsel importu önler


# =============================================================================
# Endpoint'ler
# =============================================================================

@app.post("/ask_assistant")
def ask_assistant():
    """
    Ses dosyası alır, transkripsiyon yapar ve LLM yanıtı üretir.
    Request (multipart/form-data):
        - audio_file: (zorunlu) Ses dosyası (mp3, wav, m4a vb.)
    Response (application/json; charset=utf-8):
        {
          "transcribed_text": "<kullanıcı konuşması>",
          "assistant_response": "<asistan yanıtı>",
          "response_audio_url": "/responses/response_xxx.txt"  # placeholder
        }
    """
    try:
        # 1) Dosyayı al/validasyon
        uploaded = request.files.get("audio_file") or request.files.get("file")
        if uploaded is None:
            return jsonify({"error": "No audio file provided"}), 400
        if uploaded.filename == "":
            return jsonify({"error": "No file selected"}), 400
        if not is_allowed_file(uploaded.filename):
            return jsonify({"error": "File type not allowed"}), 400

        # 2) Geçici kaydetme (güvenli dosya adı + zaman damgası)
        safe_name = secure_filename(uploaded.filename)
        unique_name = f"{datetime.now():%Y%m%d_%H%M%S}_{safe_name}"
        temp_path = str(Path(UPLOAD_DIR) / unique_name)
        uploaded.save(temp_path)
        logger.info("Audio file saved: %s", temp_path)

        # 3) ASR (Whisper)
        try:
            text = transcribe_audio(temp_path, language=os.getenv("ASR_LANGUAGE", "tr"))
            logger.info("Transcribed text: %s", text)
        except Exception as exc:
            logger.exception("ASR failed")
            return jsonify({"error": "transcription_failed", "details": str(exc)}), 500
        finally:
            # 4) Temizleme (başarılı/başarısız)
            try:
                os.remove(temp_path)
            except Exception:
                pass

        # 5) LLM cevabı
        try:
            answer = llm_service.generate_response(text)
            logger.info("Generated response (len=%d)", len(answer))
        except Exception as exc:
            logger.exception("LLM failed")
            return jsonify({"error": "llm_failed", "details": str(exc), "transcribed_text": text}), 500

        # 6) Placeholder TTS (metni txt olarak yayınla)
        response_url = save_text_response(answer)

        return jsonify(
            {
                "transcribed_text": text,
                "assistant_response": answer,
                "response_audio_url": response_url,
            }
        ), 200

    except Exception:
        logger.exception("Error in /ask_assistant")
        return jsonify({"error": "Internal server error"}), 500


@app.post("/ask_text")
def ask_text():
    """
    Metin tabanlı test endpoint'i.
    Request (application/json):
        { "text": "Kullanıcı meselesi..." }

    Response:
        Aynı yapı ask_assistant ile birebir uyumludur.
    """
    try:
        data = request.get_json(force=True, silent=False) or {}
        user_text = (data.get("text") or "").strip()
        if not user_text:
            return jsonify({"error": "No text provided"}), 400

        answer = llm_service.generate_response(user_text)
        response_url = save_text_response(answer)

        return jsonify(
            {
                "transcribed_text": user_text,
                "assistant_response": answer,
                "response_audio_url": response_url,
            }
        ), 200

    except Exception:
        logger.exception("Error in /ask_text")
        return jsonify({"error": "Internal server error"}), 500


@app.get("/responses/<path:filename>")
def serve_response_file(filename: str):
    """
    Placeholder çıktı dosyalarını public olarak servis eder.
    Not: Üretimde kimlik doğrulama/kota vb. eklemeyi değerlendirin.
    """
    try:
        return send_from_directory(RESPONSES_DIR, filename, mimetype="text/plain; charset=utf-8")
    except Exception:
        logger.exception("Error serving response file")
        return jsonify({"error": "File not found"}), 404


@app.get("/health")
def health_check():
    """Hızlı sağlık kontrolü (ASR ve ffmpeg görünürlüğü dahil)."""
    return jsonify(
        {
            "status": "healthy",
            "whisper_loaded": WHISPER_MODEL is not None,
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "timestamp": datetime.now().isoformat(),
        }
    ), 200


@app.get("/")
def index():
    """Basit servis bilgisi ve desteklenen formatlar."""
    return jsonify(
        {
            "service": "Voice Call Assistant API",
            "version": "1.0.0",
            "endpoints": {
                "ask_assistant": "/ask_assistant (POST: audio_file=file)",
                "ask_text": "/ask_text (POST: json {text})",
                "health": "/health (GET)",
                "responses": "/responses/<filename> (GET)",
            },
            "supported_formats": sorted(list(ALLOWED_EXTENSIONS)),
        }
    ), 200


# =============================================================================
# Hata Handler'ları
# =============================================================================

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "File too large. Maximum size is 16MB."}), 413


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(_):
    return jsonify({"error": "Internal server error"}), 500


# =============================================================================
# Çalıştırma
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    logger.info("Starting Voice Assistant API on port %s (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
