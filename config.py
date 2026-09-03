import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _normalize_db_url(url: str) -> str:
    # Render/Supabase の接続文字列は postgres:// で始まることがあるが
    # SQLAlchemy は postgresql:// を要求するため変換する
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'agri.db')}")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme")
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "agri-photos")
    MAX_CONTENT_LENGTH = 40 * 1024 * 1024  # 4枚まで、1枚あたり目安10MBを想定
    APP_VERSION = "1.0.1"
