import logging
from dataclasses import dataclass
from pathlib import Path
import httpx
from backend.app.models.entities import ReelExport

logger = logging.getLogger("lazycut.notifier")

@dataclass
class NotificationPayload:
    title: str
    duration_sec: float
    output_path: str
    chapters: str

class WebhookNotifier:
    def __init__(self):
        pass

    def build_discord_payload(self, export: ReelExport) -> dict:
        """Constructs a Discord Embed webhook payload."""
        filename = Path(export.output_path).name
        desc = (
            f"🎬 **New Reel Rendered Successfully!**\n\n"
            f"⏱️ **Duration**: {export.actual_duration}s\n"
            f"📐 **Aspect Ratio**: {export.aspect_ratio}\n"
            f"📁 **File**: `{filename}`\n\n"
            f"**Chapters**:\n```{export.chapters_txt}```"
        )
        return {
            "username": "LazyCut Bot",
            "avatar_url": "https://raw.githubusercontent.com/posawatwichitsaro-bit/LazyCut/main/docs/icon.png",
            "embeds": [
                {
                    "title": export.ai_title or "LazyCut Highlight Reel",
                    "description": desc,
                    "color": 0xF97316,  # Burnt-orange accent
                    "footer": {
                        "text": "LazyCut · Open-Source AI Video Automation Studio"
                    }
                }
            ]
        }

    def send_discord(self, webhook_url: str, export: ReelExport) -> bool:
        """Sends an async/sync notification to a Discord Webhook channel."""
        if not webhook_url or not webhook_url.startswith("http"):
            return False

        payload = self.build_discord_payload(export)
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(webhook_url, json=payload)
                if res.status_code in (200, 204):
                    logger.info("Discord webhook sent successfully.")
                    return True
                else:
                    logger.warning(f"Discord webhook failed with status {res.status_code}: {res.text}")
                    return False
        except Exception as e:
            logger.warning(f"Failed to deliver Discord webhook: {e}")
            return False

    def send_telegram(self, bot_token: str, chat_id: str, export: ReelExport) -> bool:
        """Sends a notification to a Telegram channel or chat."""
        if not bot_token or not chat_id:
            return False

        text = (
            f"🎬 *{export.ai_title or 'LazyCut Highlight Reel'}*\n\n"
            f"⏱️ Duration: {export.actual_duration}s\n"
            f"📐 Format: {export.aspect_ratio}\n"
            f"📁 File: `{Path(export.output_path).name}`\n\n"
            f"Chapters:\n{export.chapters_txt}"
        )
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
                return res.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to deliver Telegram notification: {e}")
            return False
