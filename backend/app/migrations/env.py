from alembic import context

import app.models  # noqa: F401  (enregistre les tables)
from app.db import Base, get_engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with get_engine().connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Le mode hors ligne n'est pas géré.")
run_migrations_online()
