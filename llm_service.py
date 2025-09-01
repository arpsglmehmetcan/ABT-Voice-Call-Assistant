"""
LLM Service
-----------

Birden fazla LLM sağlayıcısını sıralı şekilde deneyerek yanıt üretir:
Together → Hugging Face → Local (kural tabanlı fallback).

Çevresel Değişkenler (opsiyonel):
- TOGETHER_API_KEY
- HUGGINGFACE_API_KEY
- REPLICATE_API_KEY (şimdilik kullanılmıyor)
- TOGETHER_MODEL         (varsayılan: meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo)
- HF_MODEL               (varsayılan: mistralai/Mistral-7B-Instruct-v0.1)
- LLM_TIMEOUT_SECONDS    (varsayılan: 60)
- LLM_RETRY_COUNT        (varsayılan: 1)

Not: Bu modül, dışarıya tek bir global örnek (`llm_service`) sunar.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Final, Optional

import requests
from requests import Response, Session

logger = logging.getLogger(__name__)


# =============================================================================
# Sabitler / Varsayılanlar
# =============================================================================

DEFAULT_TOGETHER_MODEL: Final[str] = os.getenv(
    "TOGETHER_MODEL",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
)

DEFAULT_HF_MODEL: Final[str] = os.getenv(
    "HF_MODEL",
    "mistralai/Mistral-7B-Instruct-v0.1",
)

DEFAULT_TIMEOUT: Final[int] = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
DEFAULT_RETRIES: Final[int] = int(os.getenv("LLM_RETRY_COUNT", "1"))  # toplam deneme = 1 + retries


# =============================================================================
# Yardımcı: HTTP istemcisi (timeout + basit retry)
# =============================================================================

@dataclass
class HttpClient:
    """requests.Session sarmalayıcısı: ortak header, timeout ve basit retry yönetimi."""
    session: Session
    timeout_seconds: int = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES

    def post_json(self, url: str, headers: dict, payload: dict) -> Response:
        """
        JSON POST eder. Basit retry uygular (ağ/transient hatalarda).
        UYARI: 4xx türü kalıcı hatalarda retry yapmaz.
        """
        last_exc: Optional[Exception] = None
        attempts = 1 + max(0, self.retries)

        for attempt in range(1, attempts + 1):
            try:
                resp = self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                return resp
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                logger.warning(
                    "POST %s attempt %d/%d failed: %s",
                    url, attempt, attempts, exc
                )
        # tüm denemeler bitti
        if last_exc:
            raise last_exc
        raise RuntimeError("Unknown error in HttpClient.post_json")


# Tek bir Session kullan (keep-alive faydası)
_http = HttpClient(session=requests.Session())


# =============================================================================
# LLM Servisi
# =============================================================================

class LLMService:
    """
    LLM entegrasyonu: Together → Hugging Face → Lokal fallback.
    Çalışma sırası ve sağlayıcılar `generate_response` içinde belirlenir.
    """

    def __init__(self) -> None:
        self.together_api_key: Optional[str] = os.getenv("TOGETHER_API_KEY")
        self.huggingface_api_key: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")
        self.replicate_api_key: Optional[str] = os.getenv("REPLICATE_API_KEY")  # şimdilik kullanılmıyor

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def generate_response(self, text: str) -> str:
        """
        Kullanıcı metnine yanıt üretir.
        Sağlayıcı sırası: Together → Hugging Face → Local fallback.

        Args:
            text: Kullanıcı girdisi.

        Returns:
            Üretilen asistan yanıtı (boşsa fallback döner).

        Not:
            Boş/yalnızca boşluk içeren girişlerde kısa uyarı döner.
        """
        text = (text or "").strip()
        if not text:
            return "Seni duyamadım, tekrar eder misin?"

        # 1) Together
        out = self._generate_together(text)
        if out:
            return out

        # 2) Hugging Face
        out = self._generate_huggingface(text)
        if out:
            return out

        # 3) Lokal fallback
        logger.info("Using local LLM fallback")
        return self._generate_local(text)

    # --------------------------------------------------------------------- #
    # Together (primary)
    # --------------------------------------------------------------------- #
    def _generate_together(self, text: str) -> Optional[str]:
        """Together Chat Completions API kullanarak yanıt üretir."""
        if not self.together_api_key:
            logger.debug("Together.ai API key not set; skipping Together provider.")
            return None

        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.together_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DEFAULT_TOGETHER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sen bir e-ticaret müşteri hizmetleri asistanısın. "
                        "Kısa, açık ve çözüm odaklı yanıt ver. "
                        "Gerekirse takip/işlem adımlarını net sırala."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "max_tokens": 200,
            "temperature": 0.5,
        }

        try:
            resp = _http.post_json(url, headers, payload)
        except Exception as exc:
            logger.error("Together.ai request failed: %s", exc)
            return None

        if resp.status_code != 200:
            self._log_api_error("Together.ai", resp)
            return None

        try:
            data = resp.json()
            choice0 = (data.get("choices") or [{}])[0]
            message = choice0.get("message") or {}
            content = (message.get("content") or "").strip()
            return content or None
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("Together.ai JSON parse error: %s", exc)
            return None

    # --------------------------------------------------------------------- #
    # Hugging Face Inference (secondary)
    # --------------------------------------------------------------------- #
    def _generate_huggingface(self, text: str) -> Optional[str]:
        """Hugging Face Inference API kullanarak yanıt üretir (text2text)."""
        if not self.huggingface_api_key:
            logger.debug("Hugging Face API key not set; skipping HF provider.")
            return None

        url = f"https://api-inference.huggingface.co/models/{DEFAULT_HF_MODEL}"
        headers = {
            "Authorization": f"Bearer {self.huggingface_api_key}",
            "Content-Type": "application/json",
        }

        prompt = (
            "Sen bir e-ticaret müşteri hizmetleri asistanısın. "
            "Müşteri sorusuna kısa, açık ve yardımcı bir yanıt ver.\n\n"
            f"Müşteri sorusu: {text}\n\nYanıt:"
        )
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False,
            },
        }

        try:
            resp = _http.post_json(url, headers, payload)
        except Exception as exc:
            logger.error("Hugging Face request failed: %s", exc)
            return None

        if resp.status_code != 200:
            self._log_api_error("Hugging Face", resp)
            return None

        try:
            data = resp.json()
            # HF bazen liste döndürür, bazen obje
            if isinstance(data, list) and data:
                out = (data[0].get("generated_text") or "").strip()
                return out or None
            out = (data.get("generated_text") or "").strip()
            return out or None
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("Hugging Face JSON parse error: %s", exc)
            return None

    # --------------------------------------------------------------------- #
    # Local fallback (kural tabanlı)
    # --------------------------------------------------------------------- #
    def _generate_local(self, text: str) -> str:
        """
        Basit kural tabanlı yanıtlar.
        Üretimde yalnızca acil durum/fallback olarak kullanın.
        """
        try:
            t = (text or "").lower()

            if any(w in t for w in ("sipariş", "order", "nerede", "durum", "status", "takip")):
                responses = (
                    "Siparişiniz kargoya verilmiştir; 2-4 iş günü içinde teslim edilmesi beklenir. "
                    "Takip numaranız SMS/e-posta ile iletilecektir.",
                    "Siparişiniz hazırlanıyor; kısa süre içinde kargoya teslim edilecektir.",
                    "Siparişiniz depo çıkışı yapılmıştır; 1-2 iş günü içinde adresinize teslim edilmesi beklenir.",
                )
                return responses[hash(t) % len(responses)]

            if any(w in t for w in ("iade", "return", "geri", "değişim", "exchange")):
                return (
                    "İade/Değişim işleminizi hesabınızdaki ‘Siparişlerim’ bölümünden başlatabilirsiniz. "
                    "İade süreci 14 gün içinde tamamlanır; ücret iadesi 3-5 iş günü içinde hesabınıza geçer."
                )

            if any(w in t for w in ("ürün", "product", "stok", "stock", "var mı", "mevcut")):
                return "Güncel stok durumu ürün sayfasında yer alır. Stok dışı ürünler için bildirim oluşturabilirsiniz."

            if any(w in t for w in ("kargo", "shipping", "teslimat", "delivery", "gönderi")):
                return "Kargo süremiz şehir içi 1-2, şehir dışı 2-4 iş günüdür. 150 TL üzeri siparişlerde kargo ücretsizdir."

            if any(w in t for w in ("fiyat", "price", "indirim", "discount", "kampanya", "promosyon")):
                return "Güncel kampanyaları kampanyalar sayfasından takip edebilirsiniz. Yeni üyeler için ek indirimler bulunur."

            if any(w in t for w in ("ödeme", "payment", "kredi kartı", "card", "taksit")):
                return "Kredi/banka kartı, havale/EFT ve kapıda ödeme desteklenir. Uygun kartlara taksit seçenekleri mevcuttur."

            if any(w in t for w in ("müşteri hizmetleri", "customer service", "iletişim", "telefon")):
                return "Müşteri hizmetlerine 444 0 123 üzerinden ulaşabilir veya canlı destekten yazabilirsiniz."

            if any(w in t for w in ("hesap", "account", "üyelik", "membership", "şifre", "password")):
                return "Hesap işlemleri için ‘Hesabım’ bölümünü kullanın. Şifre sıfırlama için ‘Şifremi Unuttum’ bağlantısını tıklayın."

            if any(w in t for w in ("yardım", "help", "destek", "support", "problem", "sorun")):
                return "Size nasıl yardımcı olabiliriz? Teknik destek, sipariş takibi ve ürün bilgileri konularında yardımcı olabiliriz."

            return (
                "Müşteri hizmetlerimiz size yardımcı olmak için burada. "
                "Sipariş, kargo, iade ve ürün bilgileriyle ilgili sorularınızı yanıtlayabilirim."
            )
        except Exception as exc:
            logger.error("Local fallback failed: %s", exc)
            return "Üzgünüm, şu anda yanıt üretemiyorum. Lütfen daha sonra tekrar deneyin."

    # --------------------------------------------------------------------- #
    # Yardımcılar
    # --------------------------------------------------------------------- #
    @staticmethod
    def _log_api_error(provider: str, resp: Response) -> None:
        """Sağlayıcıya ait HTTP hata detayını güvenli şekilde loglar."""
        text = resp.text
        # Çok uzun body’leri logu boğmamak için kısalt
        body = text[:800] + ("…(truncated)" if len(text) > 800 else "")
        logger.error("%s API error: %s %s | body=%s", provider, resp.status_code, resp.reason, body)


# Dışarıya tek örnek ver
llm_service = LLMService()
