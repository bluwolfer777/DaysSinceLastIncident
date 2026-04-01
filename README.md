# Days Since Last Incident

A Flask web application that tracks and displays the number of days since the last incident.

- **Public dashboard** — intended to run on a TV or shared display; shows the counter and the full incident log.
- **Admin panel** — restricted to domain users on `samt.lan` who are members of the `GG_Sistemisti` group.
- **Live reload** — when an admin adds or deletes a record, every connected dashboard client reloads automatically via Socket.IO.

---

## Project structure

```
.
├── app.py                  # Flask application — routes, Socket.IO, DB helpers
├── auth.py                 # LDAP authentication and group-membership check
├── requirements.txt        # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── templates/
│   ├── dashboard.html      # Public TV display
│   ├── login.html          # Admin login form
│   └── admin.html          # Add / delete incidents
└── instance/               # Created at runtime — git-ignored
    ├── incidents.db        # SQLite database (WAL mode)
    └── secret.key          # Flask session key, generated once on first run
```

---

## Running locally

### Prerequisites

- Python 3.11+
- Access to the `samt.lan` domain controller from the machine running the app

### Install and start

```bash
pip install -r requirements.txt
python app.py
```

The app listens on `http://0.0.0.0:5000`.

- Dashboard: `http://<host>:5000/`
- Admin login: `http://<host>:5000/admin/login`

On first run, `instance/` is created automatically along with the SQLite database and the session secret key.

---

## Running with Docker

### Build and start

```bash
docker compose up -d
```

### Stop

```bash
docker compose down
```

The SQLite database and secret key are stored in the `dsli_data` named volume, so they survive container restarts and rebuilds.

To see logs:

```bash
docker compose logs -f
```

---

## LDAP / Active Directory configuration

Authentication is handled in `auth.py`. The following environment variables control its behaviour — they can be set directly in `docker-compose.yml` or exported in the shell before running locally.

| Variable | Default | Description |
|---|---|---|
| `LDAP_SERVER` | `samt.lan` | Hostname or IP of the domain controller |
| `LDAP_DOMAIN` | `SAMT` | NetBIOS domain name used for NTLM bind (`DOMAIN\username`) |
| `LDAP_BASE_DN` | `dc=samt,dc=lan` | Base DN for user searches |
| `LDAP_REQUIRED_GROUP` | `GG_Sistemisti` | CN of the group that grants admin access |
| `LDAP_USE_SSL` | `false` | Set to `true` to connect on port 636 with LDAPS |

### How authentication works

1. The user submits their domain username and password on `/admin/login`.
2. `auth.py` opens an NTLM connection to the domain controller as `SAMT\<username>` using the submitted password. A failed bind means wrong credentials.
3. After a successful bind, the user's `memberOf` attribute is retrieved.
4. The CN of each group is compared (case-insensitive) against `LDAP_REQUIRED_GROUP`. Access is granted only if a match is found.
5. On success, `session["admin"] = True` is set; all subsequent admin requests verify this flag.

> **Note on nested groups:** the check uses direct `memberOf` membership only. If `GG_Sistemisti` is a member of another group and users are added to the parent group, they will not pass the check. Add them directly to `GG_Sistemisti` or open an issue to add recursive resolution.

> **Note on TLS:** if the domain controller uses a self-signed or internal CA certificate, either install the CA cert in the system/container trust store, or switch to port 389 (`LDAP_USE_SSL=false`). Using port 389 transmits credentials in cleartext — acceptable only on a trusted internal network.

---

## Database schema

One table, created automatically on first run:

```sql
CREATE TABLE incidents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_on  DATE     NOT NULL,       -- date the incident actually happened
    perpetrator  TEXT     NOT NULL,       -- name or team responsible
    note         TEXT     NOT NULL,       -- short description
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

The days counter is calculated as `today − MAX(occurred_on)`.

---

## Live reload mechanism

The dashboard page connects to the Flask-SocketIO server on load. When an admin adds or deletes an incident, the server emits an `incident_update` event on the default namespace. All connected dashboard clients show a brief banner and reload the page after 1.5 seconds.

As a fallback for environments where WebSocket connections are blocked (e.g. by a corporate proxy), the dashboard also has a hard `<meta http-equiv="refresh" content="300">` that forces a reload every 5 minutes.

---

## Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | Public | Dashboard |
| GET | `/admin/login` | Public | Login form |
| POST | `/admin/login` | Public | Submit credentials |
| GET | `/admin/logout` | Admin | Clear session and redirect to login |
| GET | `/admin` | Admin | List incidents and add-incident form |
| POST | `/admin` | Admin | Insert a new incident |
| POST | `/admin/delete/<id>` | Admin | Delete an incident by ID |

---

## Dependencies

| Package | Purpose |
|---|---|
| `flask` | Web framework |
| `flask-socketio` | WebSocket support for live dashboard reload |
| `ldap3` | LDAP/Active Directory authentication |
| `eventlet` | Async worker required by Flask-SocketIO (single worker) |

> Flask-SocketIO requires exactly **one gunicorn worker** (`--workers 1`). Using multiple workers breaks the in-process Socket.IO event bus. If you need horizontal scaling, add a Redis message queue and configure `SocketIO(message_queue=...)`.
