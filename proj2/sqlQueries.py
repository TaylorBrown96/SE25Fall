import sqlite3


def create_connection(db_file: str):
    """
    Create and return a connection to the specified SQLite database.
    Args:
        db_file (str): Path to the SQLite database file.
    Returns:
        sqlite3.Connection | None: Connection object if successful, None otherwise.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn


def close_connection(conn):
    """
    Close an existing SQLite database connection.
    Args:
        conn (sqlite3.Connection): Connection object to close.
    Returns:
        None
    """
    if conn:
        conn.close()


def execute_query(conn, query: str, params=()):
    """
    Execute a single SQL query with optional parameters.
    Args:
        conn (sqlite3.Connection): Active database connection.
        query (str): SQL query string to execute.
        params (tuple, optional): Parameters to safely substitute into the query.
    Returns:
        sqlite3.Cursor | None: Cursor object if successful, None if an error occurred.
    """
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur
    except sqlite3.Error as e:
        print(e)
        return None


def fetch_all(conn, query: str, params=()):
    """
    Execute a query and return all fetched rows.
    Args:
        conn (sqlite3.Connection): Active database connection.
        query (str): SQL query string to execute.
        params (tuple, optional): Parameters to safely substitute into the query.
    Returns:
        list: A list of result rows (each as a tuple). Empty list if no results or on failure.
    """
    cur = execute_query(conn, query, params)
    if cur:
        return cur.fetchall()
    return []


def fetch_one(conn, query: str, params=()):
    """
    Execute a query and return the first result row.
    Args:
        conn (sqlite3.Connection): Active database connection.
        query (str): SQL query string to execute.
        params (tuple, optional): Parameters to safely substitute into the query.
    Returns:
        tuple | None: The first row as a tuple, or None if no result or on failure.
    """
    cur = execute_query(conn, query, params)
    if cur:
        return cur.fetchone()
    return None
