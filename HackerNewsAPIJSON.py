from datetime import datetime
import sqlite3
import requests

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json?print=pretty"

def convert_to_iso_format(unix_timestamp):
    """
    Convert UNIX timestamp to ISO format.
    """
    date = datetime.utcfromtimestamp(unix_timestamp)
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_latest_news_ids():
    """
    Fetch the latest Hacker News story IDs.
    """
    response = requests.get(TOP_STORIES_URL, timeout=500)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_and_store_news_data(news_ids, database_name):
    """
    Fetch and store Hacker News data in an SQLite database.
    """
    # Create or connect to the SQLite database
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS News (
            id INTEGER PRIMARY KEY,
            title STRING,
            url STRING,
            by STRING,
            score INTEGER,
            time DATETIME
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Likes_Dislikes (
            id INTEGER PRIMARY KEY,
            news_id INTEGER,
            likes BOOLEAN,
            FOREIGN KEY (news_id) REFERENCES news (id)
        )
    ''')

    # Fetch and store each news item
    for item_id in news_ids:
        response = requests.get(ITEM_URL.format(item_id), timeout=500)
        if response.status_code == 200:
            news_data = response.json()
            time_iso = convert_to_iso_format(news_data['time'])
            cursor.execute('''
                INSERT OR IGNORE INTO news (id, title, url, by, score, time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (news_data['id'], news_data.get('title', ''),
                news_data.get('url', ''), news_data['by'], news_data['score'], time_iso))

    # Commit changes and close the database connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    news_ids = get_latest_news_ids()
    DATABASE_NAME = "site.db"

    fetch_and_store_news_data(news_ids, DATABASE_NAME)
