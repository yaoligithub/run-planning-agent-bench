from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_ENV: str = "dev"

    STRAVA_CLIENT_ID: str | None = None
    STRAVA_CLIENT_SECRET: str | None = None
    STRAVA_REDIRECT_URI: str | None = None

    AI_DECISION_ENABLED: bool = False
    AI_API_KEY: str | None = None
    AI_API_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"
    AI_TIMEOUT_SEC: int = 25
    AI_RESEARCH_FILE: str = "/root/second-brain/02_projects/running-planner/coach_research.md"

    class Config:
        env_file = ".env"


settings = Settings()
