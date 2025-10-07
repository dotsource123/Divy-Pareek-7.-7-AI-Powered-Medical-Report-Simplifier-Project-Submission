from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This tells pydantic to load variables from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    google_api_key: str

# Create a single instance of the settings to be used across the application
settings = Settings()