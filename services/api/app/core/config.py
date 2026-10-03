"""App configuration — vertical slice.

Full config matrix is documented in docs/07-backend-api.md §8. Slice keeps a
small env-driven set; defaults work with zero setup (sqlite file DB).
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

def _find_repo_root(start: Path) -> Path:
    for parent in (start, *start.parents):
        if (parent / "infra").is_dir() or (parent / ".git").is_dir():
            return parent
    return start.parents[2] if len(start.parents) > 2 else start.parent


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
_ENV_FILES = (
    str(_REPO_ROOT / "infra" / ".env"),
    str(_REPO_ROOT / ".env"),
    ".env",
)


class Settings(BaseSettings):
    env: str = "dev"
    # Slice: sqlite file. Swap to postgres+pgvector in the content phase (06-database.md §4).
    database_url: str = "sqlite:///./data/pique.db"
    secret_key: str = "dev-secret-change-me"
    token_ttl_seconds: int = 30 * 24 * 3600  # 30 days (slice; rotation comes later, 07 §2)
    lock_default_minutes: int = 120
    duration_options: tuple[int, ...] = (5, 10, 15, 20)
    session_grace_seconds: int = 30

    # External content providers (docs/08 §7). Keys optional: these APIs work
    # anonymously at polite rate limits; registered keys raise limits later.
    openverse_enabled: bool = True
    wikimedia_enabled: bool = True
    wikipedia_enabled: bool = True   # REST summaries: free, no key
    gutenberg_enabled: bool = False  # gutendex unreachable/unreliable in some networks
    provider_user_agent: str = "FocusWarmup/0.1-slice (https://github.com/focuswarmup/focuswarmup; dev@focuswarmup.example)"  # contact info required by provider robot policies (08 §7)
    provider_connect_timeout: float = 3.0
    provider_read_timeout: float = 10.0
    on_demand_per_provider: int = 12  # caps on-demand fetch latency during session create

    # LLM layer (docs/02 §3, docs/21 idea: provider abstraction). Free tiers:
    #   gemini → Google AI Studio key  (aistudio.google.com/apikey)
    #   groq   → console.groq.com      (llama open models)
    # "none" keeps the heuristic parser + template generator (fully offline).
    llm_provider: str = "none"       # none | gemini | groq | comma chain "groq,gemini"
    llm_api_key: str | None = None
    gemini_api_key: str | None = None  # optional per-provider key (else llm_api_key shared)
    groq_api_key: str | None = None
    llm_model: str | None = None     # optional pin; aliases auto-resolve to live versions
    llm_timeout_s: float = 15.0
    # semantic ranking (docs/09-lite b): needs an LLM key with embedding quota left
    embeddings_enabled: bool = False
    embedding_model: str = "gemini-embedding-001"

    # generation-time media enrichers (free keys; absent → SVG fallback)
    giphy_api_key: str | None = None     # developers.giphy.com
    imgflip_username: str | None = None  # imgflip.com free account
    imgflip_password: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="PIQUE_",
        env_file=_ENV_FILES,
        extra="ignore",
    )


settings = Settings()
