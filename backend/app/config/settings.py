from pydantic_settings import BaseSettings
import os
from typing import Optional

def get_env_file():
    """Determine which .env file to use based on the environment"""
    render_env = "/etc/secrets/credentials_cloudinary"
    return render_env if os.path.exists(render_env) else ".env"

class Settings(BaseSettings):
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    FIREBASE_CREDENTIALS: Optional[str] = None
    IS_RENDER: bool = os.path.exists("/etc/secrets/credentials_cloudinary")  # Añade esto

    class Config:
        env_file = get_env_file()
        extra = "ignore"  # Opcional: ignora atributos extras

settings = Settings()