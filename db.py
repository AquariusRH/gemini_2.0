import streamlit as st
import psycopg2
from psycopg2 import pool
import pandas as pd
import json

# 建立連線池 (Connection Pool)，避免 Streamlit 重整導致連線數耗盡
@st.cache_resource
def get_pool():
    return psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host=st.secrets["postgres"]["host"],
        database=st.secrets["postgres"]["dbname"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        port=st.secrets["postgres"]["port"]
    )

# 測試連線
def test_connection():
    db_pool = get_pool()
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT NOW();")
            result = cur.fetchone()
            return result
    finally:
        db_pool.putconn(conn)

# 寫入賠率快照
def save_snapshot(race_id, snapshot_time, data):
    db_pool = get_pool()
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO odds_snapshots 
                (race_id, snapshot_time, win_odds, recent_fund_flow, total_fund_flow, qin_odds, bet_changes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                race_id,
                snapshot_time,
                json.dumps(data.get('win_odds', {})),
                json.dumps(data.get('recent_fund_flow', {})),
                json.dumps(data.get('total_fund_flow', {})),
                json.dumps(data.get('qin_odds', {})),
                json.dumps(data.get('bet_changes', {}))
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"寫入快照失敗: {str(e)}")
    finally:
        db_pool.putconn(conn)

# 讀取歷史數據成 DataFrame
def get_snapshots_df(race_id):
    db_pool = get_pool()
    conn = db_pool.getconn()
    try:
        query = "SELECT * FROM odds_snapshots WHERE race_id = %s ORDER BY snapshot_time ASC"
        df = pd.read_sql_query(query, conn, params=(race_id,))
        return df
    finally:
        db_pool.putconn(conn)
