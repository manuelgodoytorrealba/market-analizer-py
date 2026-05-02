from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.entities import Base

settings = get_settings()
DATABASE_URL = settings.database_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        _migrate_sqlite_schema()
        Base.metadata.create_all(bind=engine)


def _migrate_sqlite_schema() -> None:
    with engine.begin() as conn:
        if not _table_exists(conn, "listings"):
            return

        if not _has_composite_unique_index(conn, "listings", ["source", "external_id"]):
            if _table_exists(conn, "listings_old"):
                conn.exec_driver_sql("DROP TABLE listings_old")
            conn.exec_driver_sql("ALTER TABLE listings RENAME TO listings_old")
            conn.exec_driver_sql(
                """
                CREATE TABLE listings (
                    id INTEGER NOT NULL,
                    source VARCHAR NOT NULL,
                    external_id VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    normalized_name VARCHAR,
                    price FLOAT NOT NULL,
                    currency VARCHAR,
                    url TEXT NOT NULL,
                    image_url TEXT,
                    location VARCHAR,
                    seller_location VARCHAR,
                    shipping_region VARCHAR,
                    search_query VARCHAR,
                    condition VARCHAR,
                    shipping_cost FLOAT,
                    buy_it_now BOOLEAN,
                    is_active BOOLEAN,
                    scraped_at DATETIME,
                    first_seen_at DATETIME,
                    last_seen_at DATETIME,
                    PRIMARY KEY (id)
                )
                """
            )
            conn.exec_driver_sql("CREATE INDEX ix_listings_id ON listings (id)")
            conn.exec_driver_sql(
                "CREATE INDEX ix_listings_source_active ON listings (source, is_active)"
            )
            conn.exec_driver_sql(
                "CREATE INDEX ix_listings_normalized_name ON listings (normalized_name)"
            )
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX uq_listings_source_external_id ON listings (source, external_id)"
            )
            conn.exec_driver_sql(
                """
                INSERT INTO listings (
                    id,
                    source,
                    external_id,
                    title,
                    normalized_name,
                    price,
                    currency,
                    url,
                    image_url,
                    location,
                    seller_location,
                    shipping_region,
                    search_query,
                    condition,
                    shipping_cost,
                    buy_it_now,
                    is_active,
                    first_seen_at,
                    last_seen_at
                )
                SELECT
                    lo.id,
                    lo.source,
                    lo.external_id,
                    lo.title,
                    lo.normalized_name,
                    lo.price,
                    'EUR',
                    lo.url,
                    NULL,
                    lo.location,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    1,
                    COALESCE(lo.is_active, 1),
                    COALESCE(lo.last_seen_at, lo.first_seen_at),
                    lo.first_seen_at,
                    lo.last_seen_at
                FROM listings_old lo
                WHERE lo.rowid = (
                    SELECT lo2.rowid
                    FROM listings_old lo2
                    WHERE lo2.source = lo.source AND lo2.external_id = lo.external_id
                    ORDER BY COALESCE(lo2.last_seen_at, lo2.first_seen_at) DESC, lo2.id DESC
                    LIMIT 1
                )
                """
            )
            conn.exec_driver_sql("DROP TABLE listings_old")

        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_listings_source_active ON listings (source, is_active)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_listings_normalized_name ON listings (normalized_name)"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_listings_source_external_id ON listings (source, external_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_opportunities_score ON opportunities (score)"
        )
        _ensure_column_exists(conn, "listings", "search_query", "VARCHAR")
        _ensure_column_exists(conn, "listings", "currency", "VARCHAR")
        _ensure_column_exists(conn, "listings", "image_url", "TEXT")
        _ensure_column_exists(conn, "listings", "seller_location", "VARCHAR")
        _ensure_column_exists(conn, "listings", "shipping_region", "VARCHAR")
        _ensure_column_exists(conn, "listings", "condition", "VARCHAR")
        _ensure_column_exists(conn, "listings", "shipping_cost", "FLOAT")
        _ensure_column_exists(conn, "listings", "scraped_at", "DATETIME")
        _ensure_column_exists(conn, "listings", "buy_it_now", "BOOLEAN DEFAULT 1")
        _ensure_column_exists(conn, "opportunities", "listing_id", "INTEGER")
        _ensure_column_exists(conn, "opportunities", "source_listing_id", "INTEGER")
        _ensure_column_exists(conn, "opportunities", "normalized_name", "VARCHAR")
        _ensure_column_exists(conn, "opportunities", "search_query", "VARCHAR")
        _ensure_column_exists(conn, "opportunities", "opportunity_type", "VARCHAR")
        _ensure_column_exists(conn, "opportunities", "buy_it_now", "BOOLEAN DEFAULT 1")
        _ensure_column_exists(conn, "opportunities", "estimated_resale_price", "FLOAT")
        _ensure_column_exists(conn, "opportunities", "profit_estimate", "FLOAT")
        _ensure_column_exists(conn, "opportunities", "fees_estimate", "FLOAT")
        _ensure_column_exists(conn, "opportunities", "shipping_estimate", "FLOAT")
        _ensure_column_exists(conn, "opportunities", "liquidity_count", "INTEGER")
        _ensure_column_exists(conn, "opportunities", "manual_decision", "VARCHAR")
        _ensure_column_exists(conn, "opportunities", "discount_pct", "FLOAT")
        _ensure_column_exists(conn, "opportunities", "comparable_count", "INTEGER")
        _ensure_column_exists(conn, "opportunities", "confidence", "VARCHAR")
        _ensure_column_exists(conn, "opportunities", "metric_name", "VARCHAR")
        _ensure_column_exists(conn, "opportunities", "reasoning_summary", "TEXT")
        _ensure_column_exists(conn, "opportunities", "evidence_json", "TEXT")
        _ensure_column_exists(conn, "scrape_runs", "listings_normalized", "INTEGER DEFAULT 0")
        _ensure_column_exists(conn, "scrape_runs", "error_message", "TEXT")
        _ensure_column_exists(conn, "scrape_runs", "summary_json", "TEXT")


def _table_exists(conn, table_name: str) -> bool:
    row = conn.exec_driver_sql(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    ).first()
    return row is not None


def _ensure_column_exists(conn, table_name: str, column_name: str, sql_type: str) -> None:
    columns = {
        row[1]
        for row in conn.exec_driver_sql(f"PRAGMA table_info('{table_name}')").fetchall()
    }
    if column_name in columns:
        return
    conn.exec_driver_sql(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"
    )


def _has_composite_unique_index(conn, table_name: str, expected_columns: list[str]) -> bool:
    for row in conn.exec_driver_sql(f"PRAGMA index_list('{table_name}')").fetchall():
        is_unique = bool(row[2])
        if not is_unique:
            continue

        index_name = row[1]
        columns = [
            index_row[2]
            for index_row in conn.exec_driver_sql(
                f"PRAGMA index_info('{index_name}')"
            ).fetchall()
        ]
        if columns == expected_columns:
            return True

    return False
