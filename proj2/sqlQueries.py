import sqlite3

def create_connection(db_file):
    """
    Create a database connection to the SQLite database specified by db_file

    params:
    - db_file: database file path
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn

def close_connection(conn):
    """
    Close the database connection

    params:
    - conn: Connection object
    """
    if conn:
        conn.close()

def execute_query(conn, query, params=()):
    """
    Execute a single query

    params:
    - conn: Connection object
    - query: a SQL query
    - params: a tuple of parameters to be used with the query
    """
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur
    except sqlite3.Error as e:
        print(e)
        return None
    
def fetch_all(conn, query, params=()):
    """
    Fetch all results from a query

    params:
    - conn: Connection object
    - query: a SQL query
    - params: a tuple of parameters to be used with the query
    """
    cur = execute_query(conn, query, params)
    if cur:
        return cur.fetchall()
    return []

def fetch_one(conn, query, params=()):
    """
    Fetch a single result from a query

    params:
    - conn: Connection object
    - query: a SQL query
    - params: a tuple of parameters to be used with the query
    """
    cur = execute_query(conn, query, params)
    if cur:
        return cur.fetchone()
    return None