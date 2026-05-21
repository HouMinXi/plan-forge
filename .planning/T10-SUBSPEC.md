# T10 SUBSPEC: LLM client + multi-provider + cache + dual-backend corpus DB

Status: draft for subagent implementation.
Depends on: T05 skeleton, T06 parser+verdict, T07 F1-F7, T08 PBR
P1/P2/P5, T09 api.check_mechanical.
Scope: Largest task in plan-forge v0.1.  7 phases.  ~13 new modules
in src/plan_forge/llm/, 1 cache table in corpus DB, dual-backend
support (SQLite default + Postgres opt-in via SQLAlchemy URL),
modify Verdict dataclass (T06 file) to add active_providers
field.

## 0. Phase overview

Implement in this order; each phase has its own verification gate
so the subagent can checkpoint progress:

| Phase | Scope | Files touched |
|---|---|---|
| 0 | Dual-backend DB infra (SQLite default + Postgres opt-in) | pyproject.toml + alembic.ini + migrations/env.py + README + docker-compose.yml |
| 1 | Cache subsystem | corpus/models.py + corpus/db.py + llm/cache.py + first Alembic migration |
| 2 | Provider infrastructure (no real clients yet) | llm/client.py + llm/registry.py + llm/credentials.py + llm/health.py + llm/tool_use.py + llm/mocks.py |
| 3 | 4 real provider clients | llm/anthropic_client.py + kimi_client.py + deepseek_client.py + mimo_client.py |
| 4 | search_vote with N-active majority | llm/search_vote.py |
| 5 | M4: Verdict.active_providers | verdict.py (modify T06 file) + downstream test fixups |
| 6 | Test pass: full suite green | conftest.py + all phase tests passing |

## 1. Design decisions (load-bearing, do not deviate)

Five decisions resolved before this SUBSPEC was written.

### D1: Test strategy is live + mock dual mode

Tests marked `@pytest.mark.live` run real API calls (cost real
money, need real keys).  Default tests use mock providers
(deterministic, free, fast).  pytest startup scans env / pass for
available credentials per provider; if a provider's credentials
are present, its `live` tests are enabled; otherwise its `live`
tests skip with reason "no credentials".  No half-mocks (i.e., do
not mock partial responses for "live" tests -- if it is live, it
is real).

### D2: Credentials via `pass` with key pool, env var fallback

Primary source: `pass` (Unix password-store).  Convention:
entries under `plan-forge/<provider>/key<N>` (N = 1, 2, 3, ...).
Provider's `get_pool()` enumerates via `pass ls plan-forge/<provider>`
and reads each.

Fallback: env var `PLAN_FORGE_<PROVIDER>_API_KEY` (single key).
Used when `pass` is unavailable (e.g., CI environment).

Implementation: `ChainedCredentialResolver` tries `pass` first;
empty pool -> falls through to env.

### D3: Feature-detection at startup, cached 7-day

Each provider implements `health_check()` returning
`HealthStatus(auth_ok, tool_use_ok, last_checked, error)`.  Result
cached in `llm_cache` table with key `health:<provider>:<model>`,
TTL class `never_expire` overridden by explicit 7-day check at
read time (read returns None if older than 7 days, triggering
re-probe).

Probe = minimal token call (~3-5 input tokens, 1-token reply
constraint) verifying both auth and tool_use schema accepted.
Cost per probe: ~$0.0001-0.001 per provider.

If `auth_ok=False`: provider excluded from active list for the
run.  If `auth_ok=True, tool_use_ok=False`: provider included but
all its evidence tagged `UNCLASSIFIED` (per PLAN line 2090
"no_search_judgment" tier fallback).

### D4: corpus DB is dual-backend (SQLite default + Postgres opt-in)

v0.1 dogfood path uses SQLite (zero setup); v0.2 multi-user path
uses Postgres.  Both go through the same SQLAlchemy engine
abstraction.  Backend swap is a URL change, not a schema rewrite.

v0.1 default corpus URL:
`sqlite:///{xdg_data}/plan-forge/corpus.db`
where `{xdg_data}` resolves to `$XDG_DATA_HOME` or
`~/.local/share`.  Override priority: `PLAN_FORGE_CORPUS_URL` env
var first, then config file (out of scope until T16 CLI),
then default.

Postgres opt-in: set `PLAN_FORGE_CORPUS_URL=postgresql+psycopg://...`
and start the Postgres service (docker-compose provided for
convenience).  No code change.

Schema MUST be dialect-agnostic.  Use SQLAlchemy generic types
exclusively:

- `JSON` (NOT `JSONB`; the generic JSON type maps to JSONB on
  Postgres and TEXT-with-json-serialization on SQLite)
- `LargeBinary` (NOT `BYTEA` literal)
- `DateTime(timezone=True)` (both backends support)
- `String(N)` with explicit length (NOT bare `TEXT`)
- `Integer, primary_key=True, autoincrement=True` (NOT SQLite
  shorthand `INTEGER PRIMARY KEY`)

UPSERT MUST use one of:
- `session.merge(instance)` (SELECT-then-INSERT/UPDATE; one
  extra round-trip but dialect-agnostic; preferred for v0.1
  cache writes which are infrequent)
- Try `session.add` then catch `IntegrityError` and update on
  conflict (acceptable for hot paths)

Do NOT use Postgres-only `on_conflict_do_update` or SQLite-only
`INSERT OR REPLACE`.  These are dialect-specific and break the
dual-backend contract.

Indexes: use SQLAlchemy `Index` objects (no dialect-specific
GIN / partial / expression indexes in v0.1).  Postgres-specific
performance optimizations are a v0.2 candidate, recorded in
GAPS.md.

### D5: Provider registry is plug-in, search_vote handles N=0,1,2,3+

Providers register at module import.  Active list is computed at
run start from `available_providers = [p for p in registry if
credentials.get_pool(p.name) and health.last_known(p.name).auth_ok]`.

search_vote handles four arities explicitly:

| Active N | Behavior |
|---|---|
| 0 | Return `VoteResult(status="no_providers", verdict=None, ...)`. Caller (T11+) interprets as "LLM Part B unavailable, mechanical-only fallback". |
| 1 | Return `VoteResult(status="single_opinion", verdict=<that one verdict>, ...)`. tier upgraded conservatively (defaults to UNCLASSIFIED unless evidence tier upgrades). Warning emitted. |
| 2 | Return `VoteResult(status="consensus", ...)` if both agree, `status="indeterminate"` if disagree. No majority possible. |
| 3+ | Standard majority: ceil(N/2)+1 strict majority required. status="majority" if found, "indeterminate" otherwise. |

## 2. M4 deferred to phase 5 (read this before touching verdict.py)

Verdict gains a new field `active_providers: list[str]` (default
empty list).  Rationale: multi-user reproducibility -- two users
running plan-forge on the same plan with different provider mixes
will produce different verdicts; `active_providers` makes that
explicit so comparison code can detect "configurations differ,
verdicts not comparable".

This breaks T06 read-only.  Acceptable cost: alternative is a
v0.2 schema migration touching corpus.findings + JSON dataclass
round-trip; one-line field add now avoids that.

Downstream impact:
- All T06/T07/T08/T09 test code that constructs Verdict with
  positional or keyword args MUST still pass (default empty list
  for backward compat).
- T09 api.check_mechanical does NOT populate active_providers
  (no LLM ran); leaves default empty list.
- T11+ (later) populates active_providers from search_vote
  output.

## 3. Phase 0: Dual-backend DB infra (SQLite default + Postgres opt-in)

### 3.1 pyproject.toml

Add `"psycopg[binary]>=3.2"` to a new
`[project.optional-dependencies] postgres` extra (NOT to runtime
dependencies; SQLite ships with Python).

Add `"testcontainers[postgres]>=4.0"` and
`"pytest-asyncio>=0.23"` to a new `[project.optional-dependencies] dev`
extra (testcontainers used only by Postgres-marked tests).

### 3.2 alembic.ini

Change `sqlalchemy.url = sqlite:///plan_forge_corpus.db` to
`sqlalchemy.url = sqlite:///plan_forge_corpus.db`.

This stays SQLite default.  The actual runtime URL is computed
from `PLAN_FORGE_CORPUS_URL` env var via migrations/env.py.

### 3.3 migrations/env.py

Add env var override (this is what enables Postgres opt-in):

```python
import os
config = context.config
url = os.environ.get("PLAN_FORGE_CORPUS_URL")
if not url:
    # Resolve XDG default for SQLite
    xdg = os.environ.get("XDG_DATA_HOME",
                         os.path.expanduser("~/.local/share"))
    db_dir = os.path.join(xdg, "plan-forge")
    os.makedirs(db_dir, exist_ok=True)
    url = f"sqlite:///{os.path.join(db_dir, 'corpus.db')}"
config.set_main_option("sqlalchemy.url", url)
```

Placed after `config = context.config` and before
`fileConfig(config.config_file_name)`.

### 3.4 docker-compose.yml (new file at repo root, for Postgres opt-in)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: plan_forge
      POSTGRES_USER: plan_forge
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U plan_forge -d plan_forge"]
      interval: 5s
      timeout: 5s
      retries: 5
volumes:
  pgdata:
```

This file is OPT-IN.  Users who do not need Postgres ignore it.

### 3.5 README.md additions

Add a "Development setup" section near the top:

```markdown
## Development setup

Prerequisites: Python 3.13+, uv.

1. Install plan-forge in editable mode:
   ```
   uv venv --python 3.13
   uv pip install -e .[dev] --python .venv/bin/python
   ```
2. Apply database migrations (creates SQLite corpus DB at
   `~/.local/share/plan-forge/corpus.db`):
   ```
   .venv/bin/alembic upgrade head
   ```
3. Run tests:
   ```
   .venv/bin/pytest tests/ -q
   ```

### Optional: switch to Postgres

For multi-user / production use, start the bundled Postgres
service and point plan-forge at it:

```
docker compose up -d
uv pip install -e .[dev,postgres] --python .venv/bin/python
export PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge
.venv/bin/alembic upgrade head  # re-runs migrations on Postgres
```

The same migrations and ORM models work on both backends.
```

### 3.6 Phase 0 verification

```
# Default path: SQLite, no docker needed.
.venv/bin/python -c "
from sqlalchemy import create_engine, text
import os
url = os.environ.get('PLAN_FORGE_CORPUS_URL',
    'sqlite:///' + os.path.expanduser('~/.local/share/plan-forge/corpus.db'))
e = create_engine(url)
with e.connect() as c:
    v = c.execute(text('SELECT 1')).scalar()
    assert v == 1
    print('Phase 0 OK (default):', url)
"
.venv/bin/alembic upgrade head  # creates the SQLite file
```

Postgres path verification (only if user opted in):

```
docker compose up -d
sleep 5
PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge \
    .venv/bin/python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['PLAN_FORGE_CORPUS_URL'])
with e.connect() as c:
    v = c.execute(text('SELECT version()')).scalar()
    assert 'PostgreSQL 16' in v
    print('Phase 0 OK (postgres):', v.split(',')[0])
"
PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge \
    .venv/bin/alembic upgrade head
```

Run BOTH verifications.  Both must pass.  If subagent environment
lacks docker, the Postgres path is BLOCKED, not skipped; document
in report.

## 4. Phase 1: Cache subsystem

### 4.1 corpus/db.py (new module)

Exposes a singleton-style `get_engine()` and `session_scope()`:

```python
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

_engine = None
_SessionFactory = None

def get_engine():
    global _engine, _SessionFactory
    if _engine is None:
        url = os.environ.get(
            "PLAN_FORGE_CORPUS_URL",
            "postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge",
        )
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionFactory = sessionmaker(bind=_engine)
    return _engine

@contextmanager
def session_scope():
    get_engine()
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
```

### 4.2 corpus/models.py (new module)

SQLAlchemy 2.0 declarative ORM.  T10 creates ONLY the LLMCache
model.  T22 will add the 6 corpus event tables (plan_runs,
findings, llm_evidence, arbitrations, outcomes, schema_version).

```python
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Index
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class LLMCache(Base):
    __tablename__ = "llm_cache"
    key = Column(String(64), primary_key=True)  # SHA-256 hex
    provider = Column(String(32), nullable=False)
    model = Column(String(64), nullable=False)
    prompt_version = Column(String(32), nullable=False)
    payload = Column(JSON, nullable=False)  # generic JSON: JSONB on PG, TEXT on SQLite
    ttl_class = Column(String(16), nullable=False)  # canonical / recent / never_expire
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(),
    )

Index("idx_llm_cache_expires_at", LLMCache.expires_at)
Index("idx_llm_cache_provider_model", LLMCache.provider, LLMCache.model)
```

Note: `JSON` is the dialect-agnostic SQLAlchemy type.  On Postgres
it maps to JSONB; on SQLite it serializes as TEXT with automatic
JSON encoding/decoding.  Do NOT import from
`sqlalchemy.dialects.postgresql` -- that locks the model to PG.

### 4.3 migrations/versions/0001_llm_cache.py

First Alembic migration.  Creates `llm_cache` table per the
model above.  Use `op.create_table` (high-level API).  Include
all indexes.  Downgrade drops the table.

The migration file's `revision` should be the string
`"0001_llm_cache"`; `down_revision` is `None` (this is the first
migration).

### 4.4 llm/cache.py (new module)

```python
from typing import Protocol
from datetime import datetime, timezone, timedelta
from plan_forge.corpus.db import session_scope
from plan_forge.corpus.models import LLMCache

# TTL class -> seconds.  Read by lazy-TTL get.
TTL_SECONDS = {
    "canonical": 7 * 24 * 3600,
    "recent": 24 * 3600,
    "never_expire": None,  # caller must invalidate explicitly
}

class CacheBackend(Protocol):
    def get(self, key: str) -> dict | None: ...
    def set(self, key: str, value: dict, *,
            provider: str, model: str, prompt_version: str,
            ttl_class: str) -> None: ...
    def invalidate(self, key: str) -> None: ...
    def stats(self) -> dict: ...

class SqlAlchemyCacheBackend:
    def get(self, key: str) -> dict | None:
        with session_scope() as s:
            row = s.get(LLMCache, key)
            if row is None:
                return None
            if row.expires_at is not None and row.expires_at < datetime.now(timezone.utc):
                s.delete(row)
                return None
            return row.payload

    def set(self, key, value, *, provider, model, prompt_version, ttl_class):
        if ttl_class not in TTL_SECONDS:
            raise ValueError(f"unknown ttl_class: {ttl_class}")
        seconds = TTL_SECONDS[ttl_class]
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=seconds)) if seconds else None
        # Dialect-agnostic UPSERT via merge: SELECT-then-INSERT/UPDATE.
        # Acceptable cost: cache writes are infrequent (per-prompt).
        with session_scope() as s:
            s.merge(LLMCache(
                key=key, provider=provider, model=model,
                prompt_version=prompt_version, payload=value,
                ttl_class=ttl_class, expires_at=expires_at,
            ))

    def invalidate(self, key):
        with session_scope() as s:
            row = s.get(LLMCache, key)
            if row is not None:
                s.delete(row)

    def stats(self) -> dict:
        with session_scope() as s:
            from sqlalchemy import func
            total = s.query(func.count(LLMCache.key)).scalar()
            expired = s.query(func.count(LLMCache.key)).filter(
                LLMCache.expires_at < datetime.now(timezone.utc)
            ).scalar()
            return {"total": total, "expired": expired}
```

### 4.5 Phase 1 verification

Default (SQLite) path:

```
.venv/bin/alembic upgrade head
.venv/bin/python -c "
from plan_forge.llm.cache import SqlAlchemyCacheBackend
c = SqlAlchemyCacheBackend()
c.set('test:abc', {'hello': 'world'},
      provider='test', model='test', prompt_version='v0', ttl_class='recent')
assert c.get('test:abc') == {'hello': 'world'}
c.invalidate('test:abc')
assert c.get('test:abc') is None
print('Phase 1 OK (sqlite)')
"
```

Postgres path (only if docker available and user opted in):

```
docker compose up -d
PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge \
    .venv/bin/alembic upgrade head
PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge \
    .venv/bin/python -c "
from plan_forge.llm.cache import SqlAlchemyCacheBackend
c = SqlAlchemyCacheBackend()
c.set('test:abc', {'hello': 'world'},
      provider='test', model='test', prompt_version='v0', ttl_class='recent')
assert c.get('test:abc') == {'hello': 'world'}
c.invalidate('test:abc')
assert c.get('test:abc') is None
print('Phase 1 OK (postgres)')
"
```

Both paths must succeed.  Same code, same migrations, different
backend.  If Postgres path BLOCKED by missing docker, document
in report -- do not silently skip.

After both paths verified, run the full test suite to confirm
baseline regression:

```
.venv/bin/pytest tests/ -q  # 137 baseline tests still pass
```

## 5. Phase 2: Provider infrastructure

### 5.1 llm/client.py (Protocol + dataclasses)

```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class HealthStatus:
    auth_ok: bool
    tool_use_ok: bool
    last_checked: datetime
    error: str | None = None

@dataclass
class LLMResponse:
    verdict: str               # provider-specific verdict text
    reasoning: str
    cited_instances: list[dict]
    search_evidence: list[dict]
    cost_usd: float
    raw_response: dict        # provider native response, for debugging

@runtime_checkable
class LLMClient(Protocol):
    name: str          # "anthropic" / "kimi" / "deepseek" / "mimo"
    model: str

    def health_check(self) -> HealthStatus: ...
    def call(self, prompt: str, *, tool_use_schema: dict | None = None,
             cache_key_inputs: dict) -> LLMResponse: ...
```

`cache_key_inputs` is a dict whose stable JSON-serialization plus
the provider+model+tool_use-version forms the SHA-256 cache key.
Each provider client computes the key the same way.

### 5.2 llm/credentials.py

```python
import os
import subprocess
from typing import Protocol

class CredentialResolver(Protocol):
    def get_pool(self, provider: str) -> list[str]: ...

class PassCredentialResolver:
    def get_pool(self, provider):
        try:
            out = subprocess.run(
                ["pass", "ls", f"plan-forge/{provider}"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode != 0:
                return []
            # parse pass tree output for keyN entries
            keys = []
            for line in out.stdout.splitlines():
                line = line.strip().lstrip("`- |").strip()
                if line.startswith("key"):
                    val = subprocess.run(
                        ["pass", "show", f"plan-forge/{provider}/{line}"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if val.returncode == 0 and val.stdout.strip():
                        keys.append(val.stdout.strip().splitlines()[0])
            return keys
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

class EnvCredentialResolver:
    def get_pool(self, provider):
        envvar = f"PLAN_FORGE_{provider.upper()}_API_KEY"
        val = os.environ.get(envvar, "").strip()
        return [val] if val else []

class ChainedCredentialResolver:
    def __init__(self, resolvers: list[CredentialResolver]):
        self.resolvers = resolvers
    def get_pool(self, provider):
        for r in self.resolvers:
            pool = r.get_pool(provider)
            if pool:
                return pool
        return []
```

Default resolver (used by registry):
`ChainedCredentialResolver([PassCredentialResolver(), EnvCredentialResolver()])`.

### 5.3 llm/registry.py

```python
from typing import Type
from .client import LLMClient

_REGISTRY: dict[str, Type[LLMClient]] = {}

def register(name: str):
    def deco(cls):
        _REGISTRY[name] = cls
        return cls
    return deco

def list_registered() -> list[str]:
    return list(_REGISTRY.keys())

def get_class(name: str) -> Type[LLMClient]:
    return _REGISTRY[name]

def build_active_list(
    credentials: CredentialResolver | None = None,
    cache: CacheBackend | None = None,
) -> list[LLMClient]:
    """Instantiate clients for providers with credentials AND
    passing health check."""
    from .credentials import ChainedCredentialResolver, PassCredentialResolver, EnvCredentialResolver
    from .cache import SqlAlchemyCacheBackend
    credentials = credentials or ChainedCredentialResolver([
        PassCredentialResolver(), EnvCredentialResolver(),
    ])
    cache = cache or SqlAlchemyCacheBackend()
    active = []
    for name, cls in _REGISTRY.items():
        pool = credentials.get_pool(name)
        if not pool:
            continue
        client = cls(api_key=pool[0])  # round-robin in v0.2; v0.1 first key
        health = _cached_health(client, cache)
        if health.auth_ok:
            active.append(client)
    return active

def _cached_health(client, cache):
    from datetime import datetime, timezone, timedelta
    from .client import HealthStatus
    key = f"health:{client.name}:{client.model}"
    cached = cache.get(key)
    if cached:
        last = datetime.fromisoformat(cached["last_checked"])
        if datetime.now(timezone.utc) - last < timedelta(days=7):
            return HealthStatus(**{**cached, "last_checked": last})
    fresh = client.health_check()
    cache.set(key,
              {"auth_ok": fresh.auth_ok, "tool_use_ok": fresh.tool_use_ok,
               "last_checked": fresh.last_checked.isoformat(),
               "error": fresh.error},
              provider=client.name, model=client.model,
              prompt_version="health_v1", ttl_class="never_expire")
    return fresh
```

### 5.4 llm/health.py (optional thin wrapper)

If `_cached_health` logic grows beyond 30 lines, extract to
`health.py`.  For v0.1 keep inside registry.py.  If kept inside
registry, do NOT create llm/health.py; mention the design choice
in registry.py docstring.

### 5.5 llm/tool_use.py

Provider-specific tool_use web search schemas.  Each provider's
schema differs in tool name, parameter names, allowed search
query forms.  Centralize so provider clients import shared
schemas.

```python
ANTHROPIC_WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",  # check current API version
    "name": "web_search",
    "max_uses": 3,
}

# Kimi uses OpenAI-compatible function calling
KIMI_WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
}

DEEPSEEK_WEB_SEARCH_TOOL = {
    # DeepSeek tool_use known buggy per project memory.
    # If buggy at runtime, provider client should catch and return
    # tool_use_ok=False in health check.
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

# Mimo native tool_use may not exist.  Probe in health_check.
MIMO_WEB_SEARCH_TOOL = None  # placeholder until provider verified
```

Subagent: confirm current API tool names by reading provider docs
(Context7 / web fetch) before hardcoding.  Document any 2026 API
deprecations as code comments.

### 5.6 llm/mocks.py

Deterministic mock providers for unit tests (not `live`).

```python
from .client import LLMClient, LLMResponse, HealthStatus
from datetime import datetime, timezone

class MockClient:
    """Returns deterministic responses based on prompt content.
    Used in unit tests; bypass cache via cache_key_inputs trick."""
    name = "mock"
    model = "mock-1"
    def __init__(self, name="mock", responses=None):
        self.name = name
        self._responses = responses or {}
    def health_check(self):
        return HealthStatus(auth_ok=True, tool_use_ok=True,
                            last_checked=datetime.now(timezone.utc))
    def call(self, prompt, *, tool_use_schema=None, cache_key_inputs):
        for key, resp in self._responses.items():
            if key in prompt:
                return resp
        return LLMResponse(
            verdict="unknown", reasoning="no mock match",
            cited_instances=[], search_evidence=[], cost_usd=0.0,
            raw_response={},
        )
```

### 5.7 Phase 2 verification

```
.venv/bin/python -m py_compile \
    src/plan_forge/llm/client.py \
    src/plan_forge/llm/credentials.py \
    src/plan_forge/llm/registry.py \
    src/plan_forge/llm/tool_use.py \
    src/plan_forge/llm/mocks.py
.venv/bin/pytest tests/unit/test_llm_credentials.py \
                 tests/unit/test_llm_registry.py \
                 tests/unit/test_llm_mocks.py -xvs
```

Tests for Phase 2 must include:
- `test_pass_credential_resolver_no_pass_binary` (FileNotFoundError handling)
- `test_env_credential_resolver_returns_single_or_empty`
- `test_chained_resolver_fallback_order`
- `test_registry_decorator_registers`
- `test_build_active_list_filters_by_auth_ok`
- `test_mock_client_returns_canned_response`

## 6. Phase 3: 4 real provider clients

Each provider client file (~150-200 lines) follows the same
structure:

1. Import the SDK (`anthropic`, `openai`, `deepseek` patterns -- some
   use OpenAI-compatible endpoints).
2. Register via `@register("provider_name")` decorator.
3. Implement `__init__(api_key)`.
4. Implement `health_check()` per provider's minimal call shape.
5. Implement `call(prompt, *, tool_use_schema, cache_key_inputs)`:
   - Compute cache key: `sha256(json.dumps(cache_key_inputs, sort_keys=True) + self.name + self.model + tool_use_schema_hash)`
   - Try cache get; if hit, return LLMResponse from cached payload
   - Otherwise call SDK, build LLMResponse, set cache, return
   - cost_usd: estimate from token counts in response

### 6.1 Anthropic specifics

- Model: `claude-opus-4-7` per project memory (most recent Opus)
- SDK: `anthropic.Anthropic(api_key=...)`
- Web search: built-in `web_search_20250305` tool (no custom impl)
- Cache TTL: respect `cache_key_inputs["prompt_version"]` and
  `ttl_class` (canonical or recent per caller)

### 6.2 Kimi specifics

- Use OpenAI-compatible endpoint: `https://api.moonshot.cn/v1`
- Model: `moonshot-v1-32k` (or current); verify via project memory
  `reference_kimi_api.md` (memory says "verified 2026-05-03")
- Known quirk per memory: cache_control quirks -- do NOT use the
  Anthropic cache_control header here
- Web search: OpenAI-style function calling (model decides when to
  call)

### 6.3 DeepSeek specifics

- Use OpenAI-compatible endpoint
- Model: per project memory `reference_deepseek_compact.md` --
  best for cc-wrapper reviewer; tool_use has known bugs
- Health check should specifically probe tool_use; if it fails,
  return `tool_use_ok=False`; provider stays auth_ok=True and
  gets included in active list but with tool_use_ok=False (caller
  in T11+ may still use it for non-tool-use prompts)

### 6.4 Mimo specifics

- Endpoint: per project memory (verify via memory or env hint)
- Tool_use: NOT guaranteed; health_check must determine
- Fallback: PLAN line 2092 "Mimo confirmed OR falls back to
  no_search_judgment tier UNCLASSIFIED" -- if tool_use_ok=False at
  startup, all Mimo evidence is tagged UNCLASSIFIED downstream
  (Phase 4 search_vote responsibility)

### 6.5 Phase 3 tests

- For each provider: `test_<provider>_health_check_mock`
  (mock the SDK call, assert HealthStatus shape).
- For each provider: `test_<provider>_call_caches`
  (mock SDK, call twice, assert SDK called once + cache hit
  on second call).
- For each provider: `test_<provider>_call_live` marked
  `@pytest.mark.live` and skipped without credentials.  These
  are smoke tests, not assertion-heavy -- just verify a real call
  returns a non-empty verdict string.

### 6.6 Phase 3 verification

```
.venv/bin/pytest tests/unit/test_anthropic_client.py \
                 tests/unit/test_kimi_client.py \
                 tests/unit/test_deepseek_client.py \
                 tests/unit/test_mimo_client.py -xvs
# Live tests skipped unless creds present
```

## 7. Phase 4: search_vote with N-active majority

### 7.1 llm/search_vote.py

```python
from collections import Counter
from dataclasses import dataclass
from .client import LLMClient, LLMResponse

@dataclass
class VoteResult:
    status: str    # "majority" / "consensus" / "indeterminate" / "single_opinion" / "no_providers"
    verdict: str | None
    evidences: list[LLMResponse]
    active_providers: list[str]
    threshold: int | None   # required votes for majority (None for N<3)

def search_vote(
    prompt: str,
    active_clients: list[LLMClient],
    *,
    cache_key_inputs: dict,
    tool_use_schemas: dict,  # provider_name -> schema | None
) -> VoteResult:
    n = len(active_clients)
    if n == 0:
        return VoteResult(status="no_providers", verdict=None,
                          evidences=[], active_providers=[], threshold=None)

    evidences = []
    for client in active_clients:
        schema = tool_use_schemas.get(client.name)
        resp = client.call(prompt, tool_use_schema=schema,
                           cache_key_inputs={**cache_key_inputs,
                                             "provider": client.name})
        evidences.append(resp)

    active_names = [c.name for c in active_clients]

    if n == 1:
        return VoteResult(
            status="single_opinion", verdict=evidences[0].verdict,
            evidences=evidences, active_providers=active_names,
            threshold=None,
        )

    verdicts = [e.verdict for e in evidences]

    if n == 2:
        if verdicts[0] == verdicts[1]:
            return VoteResult(status="consensus", verdict=verdicts[0],
                              evidences=evidences,
                              active_providers=active_names,
                              threshold=None)
        return VoteResult(status="indeterminate", verdict=None,
                          evidences=evidences,
                          active_providers=active_names, threshold=None)

    counts = Counter(verdicts)
    top_verdict, top_count = counts.most_common(1)[0]
    threshold = (n // 2) + 1
    if top_count >= threshold:
        return VoteResult(status="majority", verdict=top_verdict,
                          evidences=evidences,
                          active_providers=active_names,
                          threshold=threshold)
    return VoteResult(status="indeterminate", verdict=None,
                      evidences=evidences,
                      active_providers=active_names,
                      threshold=threshold)
```

### 7.2 Phase 4 tests

- `test_search_vote_n0_returns_no_providers`
- `test_search_vote_n1_returns_single_opinion`
- `test_search_vote_n2_agree_returns_consensus`
- `test_search_vote_n2_disagree_returns_indeterminate`
- `test_search_vote_n3_majority`  (2/3 agree -> majority)
- `test_search_vote_n3_split_returns_indeterminate` (all 3 differ)
- `test_search_vote_n4_majority`  (3/4 agree -> majority; 2/2 split -> indeterminate)

Use MockClient instances with canned verdicts to control vote
outcomes.

## 8. Phase 5: M4 Verdict.active_providers

### 8.1 verdict.py edit (T06 file)

Add `active_providers: list[str] = field(default_factory=list)`
after `tier_summary` and before `arbitration_resolution`:

```python
@dataclass
class Verdict:
    engineering: EngineeringVerdict
    epistemic: EpistemicVerdict
    findings: list[Finding] = field(default_factory=list)
    corpus_run_id: int | None = None
    arbitration_triggered: bool = False
    tier_summary: dict = field(default_factory=dict)
    active_providers: list[str] = field(default_factory=list)  # NEW (T10 M4)
    arbitration_resolution: str | None = None
```

Field ordering: still non-defaulted before defaulted (engineering
+ epistemic first).  `active_providers` slots in among the
defaulted fields; order among defaulted fields is API surface but
not Python-required; place per the spec above.

### 8.2 Downstream test compat

Search the codebase for ALL `Verdict(...)` instantiations.
Confirm none use positional args past `epistemic` (would break on
field insertion).  Existing tests use keyword args based on T06
prior pattern, so positional-arg risk is low.

Run full test suite; all 137 baseline tests must still pass.

### 8.3 Phase 5 tests

- `test_verdict_active_providers_default_empty`
- `test_verdict_active_providers_round_trips` (set, read, assert
  list shape)
- T09 regression: `test_api_check_mechanical_leaves_active_providers_empty`

## 9. Phase 6: Conftest + full suite green

### 9.1 tests/conftest.py (new file)

Provide pytest fixtures:

1. `corpus_engine` (session scope): yields a SQLAlchemy engine
   bound to `PLAN_FORGE_CORPUS_URL` if set, otherwise to a
   per-test-session SQLite file under `tmp_path_factory`.  This
   avoids polluting the user's `~/.local/share/plan-forge/corpus.db`
   during tests.  Runs `alembic upgrade head` against the test
   engine at session start.  Yields the engine.

2. `clean_cache` (function scope): deletes all rows from
   `llm_cache` before each test that needs an empty cache.  Mark
   tests needing it with `@pytest.mark.usefixtures("clean_cache")`.
   Use `session.query(LLMCache).delete()` (dialect-agnostic) NOT
   `TRUNCATE TABLE` (Postgres-only).

3. `postgres_engine` (session scope, optional): only constructed
   when `PLAN_FORGE_TEST_POSTGRES_URL` env var is set.  Used by
   tests marked `@pytest.mark.postgres` to verify dual-backend
   parity.  Without that env var, postgres-marked tests skip
   with reason "PLAN_FORGE_TEST_POSTGRES_URL not set".

4. `has_<provider>_credentials` markers: at collection time, scan
   `pass` and env for each provider; populate a pytest-level
   state.  Use:

   ```python
   def pytest_collection_modifyitems(config, items):
       has_creds = _scan_credentials()
       for item in items:
           if "live" in item.keywords:
               provider = _provider_from_test(item)
               if not has_creds.get(provider):
                   item.add_marker(pytest.mark.skip(
                       reason=f"no {provider} credentials"))
   ```

5. `pytest.ini` (or `[tool.pytest.ini_options]` in pyproject):
   register custom markers:

   ```ini
   [pytest]
   markers =
       live: real API calls; requires credentials
       postgres: requires running Postgres
   ```

### 9.2 Full suite verification

```
# Default (SQLite) path -- no docker needed.
.venv/bin/alembic upgrade head
.venv/bin/pytest tests/ -q 2>&1 | tail -10
# Expect ~137 baseline + ~50 new T10 tests = ~187 total
# Live tests skipped unless creds; postgres-marked tests skipped
# unless PLAN_FORGE_TEST_POSTGRES_URL set.
```

Optional Postgres parity run (only if docker available):

```
docker compose up -d && sleep 5
PLAN_FORGE_TEST_POSTGRES_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge \
    .venv/bin/pytest tests/ -q -m postgres 2>&1 | tail -10
```

## 10. Verification gates (final, all phases)

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t10-llm-postgres

# Gate A: default (SQLite) path works without docker.
.venv/bin/alembic upgrade head  # creates SQLite file

# Gate A2 (optional, only if docker available): Postgres path.
# docker compose up -d && sleep 5
# PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge \
#     .venv/bin/alembic upgrade head

# Gate B: alembic up/down/up clean on default backend.
.venv/bin/alembic downgrade -1
.venv/bin/alembic upgrade head

# Gate C: full test suite (SQLite default).
.venv/bin/pytest tests/ -q 2>&1 | tail -10
# Expect ~187 passing; postgres-marked skipped without
# PLAN_FORGE_TEST_POSTGRES_URL; live tests skipped without creds.

# Gate D: py_compile clean
.venv/bin/python -m py_compile \
    src/plan_forge/corpus/db.py \
    src/plan_forge/corpus/models.py \
    src/plan_forge/llm/client.py \
    src/plan_forge/llm/credentials.py \
    src/plan_forge/llm/registry.py \
    src/plan_forge/llm/cache.py \
    src/plan_forge/llm/tool_use.py \
    src/plan_forge/llm/mocks.py \
    src/plan_forge/llm/search_vote.py \
    src/plan_forge/llm/anthropic_client.py \
    src/plan_forge/llm/kimi_client.py \
    src/plan_forge/llm/deepseek_client.py \
    src/plan_forge/llm/mimo_client.py \
    src/plan_forge/verdict.py

# Gate E: ASCII clean (every new file + the verdict.py edit)
for f in $(git diff --name-only HEAD | grep -vE "\.png$|\.lock$"); do
    n=$(python3 -c "print(sum(1 for b in open('$f','rb').read() if b>127))")
    test "$n" = "0" || { echo "FAIL: $f has $n non-ASCII"; exit 1; }
done
echo "ASCII gate OK"

# Gate F: scope creep -- only T10 files modified
git diff --name-only HEAD | grep -vE "^(pyproject\.toml|alembic\.ini|docker-compose\.yml|README\.md|migrations/|src/plan_forge/corpus/|src/plan_forge/llm/|src/plan_forge/verdict\.py|tests/conftest\.py|tests/unit/test_llm_|tests/unit/test_(anthropic|kimi|deepseek|mimo|search_vote|verdict)_|tests/integration/test_(llm_|search_vote_)|\.planning/)"
# Expect zero output

# Gate G: coverage on llm/
.venv/bin/pytest --cov=src/plan_forge/llm \
    --cov-report=term-missing tests/unit/test_llm_*.py \
    tests/unit/test_anthropic_client.py \
    tests/unit/test_kimi_client.py \
    tests/unit/test_deepseek_client.py \
    tests/unit/test_mimo_client.py \
    tests/unit/test_search_vote.py 2>&1 | tail -25
# Expect >= 80% on llm/ (lower than 90% threshold of earlier tasks
# because live-only paths in provider clients are skipped)
```

## 11. Hard constraints

1. ASCII only in all `.py` / `.md` / `.yml` / `.ini` files.  No
   em-dashes, no smart quotes, no arrows.
2. No AI markers in any file ("Generated by Claude", "Co-Authored-
   By", "Anthropic" / "GPT" / "Opus" / "Sonnet" only allowed as
   product names in user-facing text, never as origin attribution).
3. Dependencies:
   Runtime (always installed):
   - `anthropic` (Anthropic client)
   - `openai` (Kimi/DeepSeek/Mimo OpenAI-compatible SDK)
   Optional extras:
   - `psycopg[binary]>=3.2` in `[project.optional-dependencies] postgres`
     (only needed when using Postgres backend)
   - `testcontainers[postgres]>=4.0` in `[project.optional-dependencies] dev`
   - `pytest-asyncio>=0.23` in `[project.optional-dependencies] dev`
   T05 already has SQLAlchemy + Alembic + pytest + pytest-cov in
   runtime deps.  SQLite ships with Python stdlib, no driver
   needed.
4. SUBSPEC wins on contradictions with PLAN.  If SUBSPEC ambiguous,
   document interpretation as `# SUBSPEC interpretation: ...`
   comment.
5. Phase order is a constraint: do NOT start Phase 3 until Phase 2
   green; do NOT start Phase 4 until Phase 3 green.  This keeps
   the test suite passing at every checkpoint.
6. Read-only files:
   - parser.py
   - All checks/ modules (T07 + T08)
   - All test_parser.py / test_verdict.py / test_f*.py / test_p*.py
   - All existing fixtures
   - The api.py from T09 (do NOT add LLM calls to api.check_mechanical;
     T13 wires LLM into the broader check() pipeline)
7. T06 file modification permitted ONLY for the single Verdict
   field add (M4); no other changes to verdict.py.
8. No subprocess calls to other Claude Code skills.
9. Provider clients MUST NOT bypass the cache: every `call()`
   goes through `cache.get` first, `cache.set` after.  Live
   tests are the exception; they explicitly invalidate the cache
   key before calling.
10. Dialect-agnostic schema writing nursery (dual-backend
    contract).  ALL of the following are bans:
    - NO `from sqlalchemy.dialects.postgresql import ...` for
      column types in ORM models.  Use SQLAlchemy generic types.
    - NO `JSONB` literal.  Use `JSON`.
    - NO `BYTEA` literal.  Use `LargeBinary`.
    - NO `on_conflict_do_update` / `on_conflict_do_nothing`.
      Use `session.merge()` or try/except `IntegrityError`.
    - NO SQLite-only `INSERT OR REPLACE` / `INSERT OR IGNORE`.
    - NO bare `TEXT` columns; use `String(N)` with explicit
      length.
    - NO `INTEGER PRIMARY KEY` SQLite shorthand; use
      `Column(Integer, primary_key=True, autoincrement=True)`.
    - NO `TRUNCATE TABLE` in test cleanup; use
      `session.query(Model).delete()` (works on both backends).
    - NO PG-specific indexes (GIN, GiST, partial via WHERE clause).
      Use SQLAlchemy `Index` objects for plain b-tree indexes
      only.
    If you find a v0.1 scenario that genuinely needs a dialect-
    specific feature, STOP and add an entry to .planning/GAPS.md
    rather than violating this contract.

## 12. Non-goals

- Do NOT implement the 6 corpus event tables (T22).
- Do NOT implement api.check() full pipeline (T13).
- Do NOT implement G modules (T11/T12/T29/T30).
- Do NOT implement arbitration (T25/T26/T27).
- Do NOT implement CLI subcommands (T16).
- Do NOT implement scaffold (T14).
- Do NOT add NFS-shared corpus or distributed locking (out of
  scope per D4; v0.2 candidate, GAPS.md).
- Do NOT implement live tests for the test_<provider>_call_live
  assertions; these are smoke tests, not assertion-heavy.

## 13. Report-back format (when done)

Print summary < 50 lines:
- Files created (path + line count, grouped by phase)
- Files modified (path + +/- line count)
- Total test count (baseline 137 + new T10)
- Live test count (skipped without creds)
- Coverage % on src/plan_forge/llm/
- Any SUBSPEC ambiguities encountered and how resolved (with
  `# SUBSPEC interpretation: ...` comment locations)
- Confirmation: phases 0-6 all green / docker compose up worked /
  alembic up/down/up clean / ASCII clean / scope creep gate clean

Do NOT include lengthy diffs.

Begin with Phase 0 verification (Postgres running).  Do NOT
proceed to Phase 1 until Phase 0 verification passes.
