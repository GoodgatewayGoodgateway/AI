import logging
import os
from typing import Optional
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _build_db_config() -> tuple[dict, str]:
    config = {
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", 3306)),
        "user":     os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "charset":  "utf8mb4",
    }
    db_name = os.getenv("DB_NAME", "roomitai")
    return config, db_name


DB_CONFIG, DB_NAME = _build_db_config()


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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     VARCHAR(100) NOT NULL,
            listing_id  INT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_fav (user_id, listing_id)
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


def add_favorite(user_id: str, listing_id: int) -> Optional[dict]:
    """즐겨찾기 추가. 이미 존재하면 None 반환"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO favorites (user_id, listing_id) VALUES (%s, %s)",
            (user_id, listing_id),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "listing_id": listing_id}
    except Exception:
        return None
    finally:
        cursor.close()
        conn.close()


def get_favorites_db(user_id: str) -> list:
    """유저의 즐겨찾기 목록 조회 (listings JOIN)"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT f.id AS favorite_id, l.*
        FROM favorites f
        JOIN listings l ON f.listing_id = l.id
        WHERE f.user_id = %s
        ORDER BY f.created_at DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def delete_favorite(favorite_id: int, user_id: str) -> bool:
    """즐겨찾기 삭제. 삭제된 행이 있으면 True"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM favorites WHERE id = %s AND user_id = %s",
        (favorite_id, user_id),
    )
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    return affected > 0


# 초기화 가능한 테이블 목록 (SQL 인젝션 방지용 화이트리스트)
_RESETTABLE_TABLES = {"listings", "favorites"}


def reset_table_auto_increment(table: str) -> dict:
    """
    테이블 데이터를 삭제하고 AUTO_INCREMENT를 1로 초기화.
    listings 테이블은 favorites에서 참조 중인 행을 보호한다.
    허용된 테이블: listings, favorites
    """
    if table not in _RESETTABLE_TABLES:
        raise ValueError(f"허용되지 않은 테이블입니다: {table}")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
    before = cursor.fetchone()["cnt"]

    if table == "listings":
        # favorites에서 참조 중인 listing_id는 삭제하지 않음
        cursor.execute("""
            DELETE FROM listings
            WHERE id NOT IN (SELECT listing_id FROM favorites)
        """)
        deleted = cursor.rowcount
        # 테이블이 비었을 때만 AUTO_INCREMENT = 1이 실제로 적용됨
        cursor.execute("ALTER TABLE listings AUTO_INCREMENT = 1")
    else:
        cursor.execute(f"TRUNCATE TABLE `{table}`")
        deleted = before

    conn.commit()
    cursor.close()
    conn.close()

    logger.info(f"[DB] {table} 초기화 완료 (삭제 {deleted}건, 보호 {before - deleted}건)")
    return {"table": table, "deleted_count": deleted, "protected_count": before - deleted, "auto_increment": 1}


def get_market_trend_db(area: str, listing_type: Optional[str] = None) -> list:
    """지역·타입별 날짜별 평균 가격 트렌드 조회"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT DATE(created_at) AS date,
               ROUND(AVG(price), 0) AS avg_price,
               COUNT(*) AS count
        FROM listings
        WHERE (city LIKE %s OR address LIKE %s)
    """
    params: list = [f"%{area}%", f"%{area}%"]
    if listing_type:
        query += " AND type = %s"
        params.append(listing_type)
    query += " GROUP BY DATE(created_at) ORDER BY date ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
