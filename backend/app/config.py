from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "StudyDesk API"
    database_url: str = "postgresql+psycopg://studydesk:studydesk@localhost:5432/studydesk"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
