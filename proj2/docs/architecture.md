# Architecture

- Flask (Jinja views + /api blueprint)
- SQLite via `sqlQueries.py`
- Session-based auth
- Admin-only DB viewer (whitelisted tables)
- Local Swagger UI at `/apidocs` + exported `openapi.json`

## Data Model (current)
- User(usr_id, first_name, last_name, email, phone, password_HS, wallet, preferences)
- Restaurant(rtr_id, name, ...)
- MenuItem(itm_id, rtr_id, ...)
- Review(...), Order(...)

## Flow
1. Login sets session (Fname/Lname/Email/etc.)
2. Index/Profile read from session
3. `/api` exposes health + `/me` for FE use
