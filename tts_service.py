"""
Text-to-Speech (TTS) servis entegrasyonu.
Sıralı deneme stratejisi uygular:
1) ElevenLabs
2) Replicate (Coqui XTTS)
3) Lokal placeholder (development için)

Not: ElevenLabs ve Replicate API anahtarları .env üzerinden alınır.
"""

from __future__ import annotations

import os
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech servis sınıfı.

    Özellikler:
        - ElevenLabs API (yüksek kalite)
        - Replicate Coqui XTTS
        - Lokal placeholder (geliştirme/test için)
    """

    def __init__(self) -> None:
        self.elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
        self.replicate_api_key: Optional[str] = os.getenv("REPLICATE_API_KEY")

    # ------------------------------------------------------------------ #
    # ElevenLabs
    # ------------------------------------------------------------------ #
    def generate_audio_elevenlabs(
        self, text: str, output_path: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    ) -> bool:
        """
        ElevenLabs API kullanarak ses üretir.

        Args:
            text: Seslendirilecek metin
            output_path: Çıktı dosyası yolu
            voice_id: ElevenLabs ses kimliği

        Returns:
            bool: True = başarılı, False = başarısız
        """
        if not self.elevenlabs_api_key:
            logger.debug("ElevenLabs API key bulunamadı, atlanıyor.")
            return False

        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key,
            }
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
            }

            resp = requests.post(url, json=data, headers=headers, timeout=30)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return True

            logger.error("ElevenLabs API error: %s %s", resp.status_code, resp.text)
            return False
        except Exception as exc:
            logger.error("ElevenLabs TTS error: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # Replicate / Coqui XTTS
    # ------------------------------------------------------------------ #
    def generate_audio_replicate(self, text: str, output_path: str) -> bool:
        """
        Replicate (Coqui XTTS) kullanarak ses üretir.

        Args:
            text: Seslendirilecek metin
            output_path: Çıktı dosyası yolu

        Returns:
            bool: True = başarılı, False = başarısız
        """
        if not self.replicate_api_key:
            logger.debug("Replicate API key bulunamadı, atlanıyor.")
            return False

        try:
            headers = {
                "Authorization": f"Token {self.replicate_api_key}",
                "Content-Type": "application/json",
            }
            data = {
                "version": "cjwbw/xtts-v2:5e7e2b2c6c2e1db3a1e9e5c1c6f4b5e1b5e1b5e1",
                "input": {
                    "text": text,
                    "speaker": "Ana",  # Türkçe kadın sesi
                    "language": "tr",
                    "cleanup_voice": True,
                },
            }

            resp = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json=data,
                timeout=30,
            )
            if resp.status_code != 201:
                logger.error("Replicate API error: %s %s", resp.status_code, resp.text)
                return False

            prediction = resp.json()
            prediction_id = prediction["id"]

            # Tamamlanana kadar bekle
            for _ in range(30):
                status_resp = requests.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers=headers,
                    timeout=10,
                )
                if status_resp.status_code != 200:
                    continue

                status = status_resp.json()
                if status.get("status") == "succeeded":
                    audio_url = status.get("output")
                    if not audio_url:
                        logger.error("Replicate: çıktı URL'si bulunamadı")
                        return False

                    audio_resp = requests.get(audio_url, timeout=30)
                    if audio_resp.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(audio_resp.content)
                        return True
                    return False
                if status.get("status") == "failed":
                    logger.error("Replicate tahmin başarısız")
                    return False

                time.sleep(1)

            logger.error("Replicate prediction timeout")
            return False
        except Exception as exc:
            logger.error("Replicate TTS error: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # Lokal Placeholder
    # ------------------------------------------------------------------ #
    def generate_audio_local_placeholder(self, text: str, output_path: str) -> bool:
        """
        Geliştirme/test için basit placeholder dosya oluşturur.
        Ses yerine bir text dosyası yazılır.

        Args:
            text: Seslendirilecek metin
            output_path: Çıktı dosyası yolu

        Returns:
            bool: True = başarılı, False = başarısız
        """
        try:
            placeholder = (
                f"# Audio Placeholder\n"
                f"# Text: {text}\n"
                f"# Path: {os.path.basename(output_path)}\n"
                f"# Burada normalde gerçek ses dosyası olurdu.\n"
            )
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(placeholder)

            logger.info("Placeholder audio file created: %s", output_path)
            return True
        except Exception as exc:
            logger.error("Error creating placeholder audio: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # Router
    # ------------------------------------------------------------------ #
    def generate_audio(self, text: str, output_path: str) -> bool:
        """
        Sıralı olarak TTS sağlayıcılarını dener:
        1) ElevenLabs
        2) Replicate Coqui XTTS
        3) Placeholder

        Args:
            text: Seslendirilecek metin
            output_path: Çıktı dosyası yolu
        """
        if self.generate_audio_elevenlabs(text, output_path):
            logger.info("Audio generated using ElevenLabs")
            return True

        if self.generate_audio_replicate(text, output_path):
            logger.info("Audio generated using Replicate Coqui XTTS")
            return True

        logger.info("Falling back to placeholder TTS")
        return self.generate_audio_local_placeholder(text, output_path)


# Global TTS service instance
tts_service = TTSService()
