"""
config.py
---------

Uygulama yapılandırması: yük boyutları, klasörler, desteklenen formatlar,
ASR/LLM/TTS ayarları ve HTTP zaman aşımları gibi tüm sabitler burada toplanır.

Kullanım:
    from config import Settings
    cfg = Settings.from_env()    # .env ve OS environment'tan okur
    cfg.ensure_directories()     # uploads/ & responses/ klasörlerini garanti eder
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Set


# -----------------------------------------------------------------------------
# Yardımcı dönüştürücüler
# -----------------------------------------------------------------------------

def _to_bool(value: str | None, default: bool = False) -> bool:
    """
    "true/1/yes/on" → True ; "false/0/no/off" → False ; None → default
    Büyük/küçük harf duyarsızdır.
    """
    if value is None:
        return default
    v = value.strip().lower()
    return v in {"1", "true", "yes", "on", "y"} if v else default


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


# -----------------------------------------------------------------------------
# Varsayılan modeller ve sınırlar
# -----------------------------------------------------------------------------

DEFAULT_WHISPER_MODEL: Final[str] = "base"  # tiny, base, small, medium, large
DEFAULT_HF_MODEL:     Final[str] = "mistralai/Mistral-7B-Instruct-v0.1"
DEFAULT_TOGETHER_MODEL: Final[str] = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

DEFAULT_MAX_UPLOAD_BYTES: Final[int] = 16 * 1024 * 1024  # 16 MB
DEFAULT_JSON_LOG_LEVEL:   Final[str] = "INFO"

DEFAULT_LLM_TIMEOUT_SECONDS: Final[int] = 60
DEFAULT_LLM_RETRY_COUNT:     Final[int] = 1   # toplam deneme = 1 + retry


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------

@dataclass(slots=True)
class Settings:
    """
    Uygulamanın tüm ayarlarını tek bir yerde toplayan veri sınıfı.

    Not: `from_env()` ile .env / environment’tan değerleri çekip oluşturun.
    """

    # Flask / App
    secret_key: str = field(default="dev-secret-key-change-in-production")
    max_content_length: int = field(default=DEFAULT_MAX_UPLOAD_BYTES)
    log_level: str = field(default=DEFAULT_JSON_LOG_LEVEL)
    debug: bool = field(default=False)
    port: int = field(default=8000)

    # Dosya/klasör
    upload_folder: str = field(default="uploads")
    response_folder: str = field(default="responses")
    allowed_extensions: Set[str] = field(
        default_factory=lambda: {"wav", "mp3", "mp4", "m4a", "flac", "ogg"}
    )

    # ASR (Whisper)
    whisper_model: str = field(default=DEFAULT_WHISPER_MODEL)
    asr_language: str | None = field(default="tr")  # None → otomatik tespit

    # LLM API anahtarları
    huggingface_api_key: str | None = field(default=None)
    together_api_key: str | None = field(default=None)
    replicate_api_key: str | None = field(default=None)
    openai_api_key: str | None = field(default=None)

    # LLM modelleri ve zaman aşımı
    hf_model: str = field(default=DEFAULT_HF_MODEL)
    together_model: str = field(default=DEFAULT_TOGETHER_MODEL)
    llm_timeout_seconds: int = field(default=DEFAULT_LLM_TIMEOUT_SECONDS)
    llm_retry_count: int = field(default=DEFAULT_LLM_RETRY_COUNT)

    # TTS
    elevenlabs_api_key: str | None = field(default=None)
    elevenlabs_voice_id: str = field(default="21m00Tcm4TlvDq8ikWAM")  # varsayılan örnek

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Ortam değişkenlerinden ayarları okur.
        `.env` kullanıyorsanız `dotenv.load_dotenv()` çağrısını app başlangıcında yapın.
        """
        return cls(
            # Flask / App
            secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
            max_content_length=_to_int(os.getenv("MAX_CONTENT_LENGTH"), DEFAULT_MAX_UPLOAD_BYTES),
            log_level=os.getenv("LOG_LEVEL", DEFAULT_JSON_LOG_LEVEL),
            debug=_to_bool(os.getenv("DEBUG"), False),
            port=_to_int(os.getenv("PORT"), 8000),

            # Dosya/klasör
            upload_folder=os.getenv("UPLOAD_FOLDER", "uploads"),
            response_folder=os.getenv("RESPONSE_FOLDER", "responses"),
            # allowed_extensions sabit set; istersen CSV'den okutacak bir parser ekleyebilirsin

            # ASR
            whisper_model=os.getenv("WHISPER_MODEL", DEFAULT_WHISPER_MODEL),
            asr_language=os.getenv("ASR_LANGUAGE", "tr") or None,

            # LLM
            huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY"),
            together_api_key=os.getenv("TOGETHER_API_KEY"),
            replicate_api_key=os.getenv("REPLICATE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),

            hf_model=os.getenv("HF_MODEL", DEFAULT_HF_MODEL),
            together_model=os.getenv("TOGETHER_MODEL", DEFAULT_TOGETHER_MODEL),
            llm_timeout_seconds=_to_int(os.getenv("LLM_TIMEOUT_SECONDS"), DEFAULT_LLM_TIMEOUT_SECONDS),
            llm_retry_count=_to_int(os.getenv("LLM_RETRY_COUNT"), DEFAULT_LLM_RETRY_COUNT),

            # TTS
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        )

    # ------------------------ Yardımcı metotlar ------------------------ #

    def ensure_directories(self) -> None:
        """Yükleme ve yanıt klasörlerinin varlığını garanti eder."""
        Path(self.upload_folder).mkdir(parents=True, exist_ok=True)
        Path(self.response_folder).mkdir(parents=True, exist_ok=True)

    # Flask app.config ile uyumlu key'ler gerekiyorsa bu metodu kullan
    def to_flask_config(self) -> dict[str, object]:
        """
        Flask `app.config.update(...)` için uygun sözlük döndürür.
        """
        return {
            "SECRET_KEY": self.secret_key,
            "MAX_CONTENT_LENGTH": self.max_content_length,
        }

    def is_extension_allowed(self, filename: str) -> bool:
        """
        Dosya uzantısının izinli olup olmadığını kontrol eder.
        """
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in self.allowed_extensions
