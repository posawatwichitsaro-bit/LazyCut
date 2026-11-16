import os
import logging
from dataclasses import dataclass
from pathlib import Path
from backend.app.core.config import BASE_DIR
from backend.app.models.entities import ReelExport

logger = logging.getLogger("lazycut.youtube")

@dataclass
class YouTubeUploadResult:
    success: bool
    video_id: str | None = None
    video_url: str | None = None
    error: str | None = None
    is_configured: bool = True

class YouTubeUploader:
    def __init__(
        self,
        credentials_file: Path | None = None,
        token_file: Path | None = None
    ):
        self.credentials_file = credentials_file or (BASE_DIR / "client_secrets.json")
        self.token_file = token_file or (BASE_DIR / "token.json")

    def _get_authenticated_service(self):
        """Builds an authenticated YouTube Data API v3 service."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            scopes = ["https://www.googleapis.com/auth/youtube.upload"]
            creds = None

            if self.token_file.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_file), scopes)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), scopes)
                    creds = flow.run_local_server(port=0)

                with open(self.token_file, "w", encoding="utf-8") as token_out:
                    token_out.write(creds.to_json())

            return build("youtube", "v3", credentials=creds)
        except Exception as e:
            raise RuntimeError(f"Authentication failed: {e}")

    def upload_reel(
        self,
        export: ReelExport,
        privacy_status: str = "unlisted"
    ) -> YouTubeUploadResult:
        """
        Uploads a generated Reel to YouTube Data API v3.
        Non-destructive and decoupled: local export is always preserved.
        """
        if not self.credentials_file.exists():
            return YouTubeUploadResult(
                success=False,
                error="Credentials file not found. Place 'client_secrets.json' in the project root.",
                is_configured=False
            )

        try:
            service = self._get_authenticated_service()
            
            body = {
                "snippet": {
                    "title": export.ai_title or "LazyCut Highlight Reel",
                    "description": export.ai_description or (export.chapters_txt or ""),
                    "tags": ["Valorant", "Gaming", "Montage", "Shorts"],
                    "categoryId": "20"  # Gaming category ID
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }

            media_file = export.output_path
            if not Path(media_file).exists():
                return YouTubeUploadResult(
                    success=False,
                    error=f"Video export file not found at: {media_file}"
                )

            # Insert video
            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=str(media_file)
            )
            response = request.execute()
            video_id = response.get("id")

            return YouTubeUploadResult(
                success=True,
                video_id=video_id,
                video_url=f"https://youtu.be/{video_id}" if video_id else None,
                is_configured=True
            )
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            return YouTubeUploadResult(
                success=False,
                error=str(e),
                is_configured=True
            )
