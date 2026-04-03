from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DuckDB
    db_path: str = "smartnews.duckdb"
    github_repository: str = "hacktan/smartnews"
    github_release_tag: str = "db-latest"
    github_db_asset_name: str = "smartnews.duckdb"

    # App
    cors_origins: str = "*"
    cache_ttl_seconds: int = 180
    home_top_stories_limit: int = 10
    category_page_size: int = 20
    search_max_results: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
