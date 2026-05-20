import os

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

# Allow env var override of corpus DB URL before fileConfig reads alembic.ini.
# If not set, resolve XDG default for SQLite.
_corpus_url = os.environ.get("PLAN_FORGE_CORPUS_URL")
if not _corpus_url:
    _xdg = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    _db_dir = os.path.join(_xdg, "plan-forge")
    os.makedirs(_db_dir, exist_ok=True)
    _corpus_url = "sqlite:///" + os.path.join(_db_dir, "corpus.db")
config.set_main_option("sqlalchemy.url", _corpus_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from plan_forge.corpus.models import Base  # noqa: E402
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
