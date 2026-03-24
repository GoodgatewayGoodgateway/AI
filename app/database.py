import logging
from typing import Optional
import mysql.connector

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "charset": "utf8mb4",
}

DB_NAME = "roomitai"


def get_connection():
    return mysql.connector.connect(database=DB_NAME, **DB_CONFIG)


def init_db():
    """DB 및 테이블 초기화"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.execute(f"USE `{DB_NAME}`")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(255),
            address     VARCHAR(500),
            area        FLOAT,
            deposit     INT,
            monthly     INT,
            price       INT,
            lat         DOUBLE,
            lng         DOUBLE,
            type        VARCHAR(50),
            distance_km FLOAT,
            source      VARCHAR(50),
            city        VARCHAR(100),
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("[DB] roomitai 초기화 완료")


def save_listings(listings: list, city: str = None) -> list:
    """매물 리스트를 DB에 저장하고, DB auto-increment id가 포함된 리스트 반환"""
    if not listings:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    result = []
    for l in listings:
        cursor.execute(
            """
            INSERT INTO listings
                (name, address, area, deposit, monthly, price,
                 lat, lng, type, distance_km, source, city)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                l.get("name"), l.get("address"), l.get("area"),
                l.get("deposit"), l.get("monthly"), l.get("price"),
                l.get("lat"), l.get("lng"), l.get("type"),
                l.get("distance_km"), l.get("source"), city,
            ),
        )
        result.append({"id": cursor.lastrowid, **{k: v for k, v in l.items() if k != "id"}})
    conn.commit()
    cursor.close()
    conn.close()
    return result


def get_listing_by_id_db(listing_id: int) -> Optional[dict]:
    """DB에서 id로 매물 단건 조회"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row
