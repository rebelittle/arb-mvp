from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "arb-mvp-api"
    api_prefix: str = "/api"

    cors_origins: str = "http://localhost:5173"

    enable_mock_source: bool = True
    enable_odds_api_source: bool = False
    enable_scrapling_source: bool = False

    odds_api_key: str = ""
    odds_api_sport: str = "basketball_nba"

    scrapling_books: str = "draftkings,fanduel,betrivers,betmgm"

    # Auth
    api_key: str = ""  # empty = auth disabled (local dev)

    # Sports
    sports: str = "kbo,nba,mlb,nhl,soccer,ncaam"

    # Scrape loop intervals
    scrape_interval_seconds: int = 60           # legacy fallback
    playwright_interval_seconds: int = 10       # DraftKings / FanDuel / BetMGM (1 sport = ~15s run)
    api_interval_seconds: int = 5               # BetRivers / betPARX / BallyBet (~9s run → 14s cycle)

    # Per-book credentials
    draftkings_email: str = ""
    draftkings_password: str = ""
    fanduel_email: str = ""
    fanduel_password: str = ""

    # BetRivers state subdomain (oh, il, pa, mi, etc.)
    betrivers_state: str = "oh"


    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def scrapling_book_list(self) -> list[str]:
        return [book.strip() for book in self.scrapling_books.split(",") if book.strip()]

    @property
    def sports_list(self) -> list[str]:
        return [sport.strip() for sport in self.sports.split(",") if sport.strip()]


settings = Settings()
