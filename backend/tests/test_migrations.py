from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db import Base, get_engine


def test_migration_matches_models(client):
    """La migration crée exactement les tables décrites par les modèles."""
    engine = get_engine()
    assert {"game", "tag", "game_tag", "note_entry"} <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
