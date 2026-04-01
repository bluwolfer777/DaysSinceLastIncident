# Days Since Last Incident

Displays on a TV how many days have passed since the last incident.  
Admins authenticated via Active Directory can add and delete records. When a record is added, the TV updates automatically.

---

## Quick install

### Requirements

- A Linux PC/server with **Docker** installed
- Network access to your Active Directory domain controller from the machine running the app

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/bluwolfer777/DaysSinceLastIncident.git
cd DaysSinceLastIncident
```

---

### Step 2 — Configure LDAP

Open `docker-compose.yml` with a text editor and fill in the four lines under `environment`:

```yaml
environment:
  LDAP_SERVER: "dc01.yourdomain.local"    # hostname or IP of the domain controller
  LDAP_DOMAIN: "YOURDOMAIN"              # NetBIOS domain name (uppercase)
  LDAP_BASE_DN: "dc=yourdomain,dc=local" # base DN of your AD
  LDAP_REQUIRED_GROUP: "IT_Admins"       # AD group allowed to log in
```

> **Real-world example:**  
> If your domain is `company.lan` and the DC is `dc01.company.lan`:
> ```yaml
> LDAP_SERVER: "dc01.company.lan"
> LDAP_DOMAIN: "COMPANY"
> LDAP_BASE_DN: "dc=company,dc=lan"
> LDAP_REQUIRED_GROUP: "IT_Admins"
> ```

---

### Step 3 — Start the application

```bash
docker-compose up -d
```

The app is ready. Open your browser at `http://localhost:5000`.

> To use a different port (e.g. 8080), change `"5000:5000"` to `"8080:5000"` in `docker-compose.yml`.

---

### Step 4 — Point the TV at the dashboard

On the TV (or any browser) open:

```
http://<server-ip>:5000
```

The page reloads automatically every time a new incident is recorded.

---

### Step 5 — Access the admin panel

From your PC (not the TV), open:

```
http://<server-ip>:5000/admin/login
```

Enter your domain credentials (username only — no `DOMAIN\` prefix).  
You must be a member of the AD group configured in Step 2.

---

## Useful commands

| Action | Command |
|---|---|
| Start the app | `docker-compose up -d` |
| Stop the app | `docker-compose down` |
| View live logs | `docker logs -f days-since-last-incident` |
| Restart after a config change | `docker-compose down && docker-compose up -d` |
| Update to the latest version | `git pull && docker-compose up -d --build` |

---

## Using the pre-built image (no need to clone the repo)

If you don't want to clone the repository, you can use the image published on GitHub Container Registry.

Create a `docker-compose.yml` file with the following content:

```yaml
services:
  dsli:
    image: ghcr.io/bluwolfer777/dayssincelastincident:latest
    container_name: days-since-last-incident
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - dsli_data:/app/instance
    environment:
      LDAP_SERVER: "dc01.yourdomain.local"
      LDAP_DOMAIN: "YOURDOMAIN"
      LDAP_BASE_DN: "dc=yourdomain,dc=local"
      LDAP_REQUIRED_GROUP: "IT_Admins"

volumes:
  dsli_data:
```

Then run:

```bash
docker-compose up -d
```

Docker will pull the image automatically and the app will start.

---

## Where data is stored

The SQLite database is stored in a Docker volume called `dsli_data`.  
Data is **not lost** when you stop or update the container.

To manually back up the database:

```bash
docker cp days-since-last-incident:/app/instance/incidents.db ./backup_incidents.db
```

---

## Advanced options

| Environment variable | Description | Default |
|---|---|---|
| `LDAP_SERVER` | Hostname or IP of the domain controller | `ldap.example.com` |
| `LDAP_DOMAIN` | NetBIOS domain name | `EXAMPLE` |
| `LDAP_BASE_DN` | Base DN for user searches in AD | `dc=example,dc=com` |
| `LDAP_REQUIRED_GROUP` | AD group required for admin access | `IT_Administrators` |
| `LDAP_USE_SSL` | Set to `true` to use LDAPS (port 636) | `false` |

> **Note on `LDAP_USE_SSL`:** if the DC uses a self-signed or internal CA certificate, install the certificate in the system trust store before enabling SSL. Without SSL on a trusted internal LAN, credentials are sent in plaintext — acceptable only on private networks.

---

## Project structure

```
app.py              # Flask application
auth.py             # LDAP authentication
requirements.txt    # Python dependencies
Dockerfile
docker-compose.yml
templates/
  dashboard.html    # public TV display
  login.html        # admin login page
  admin.html        # incident management panel
instance/           # auto-created at runtime — contains the DB and session key
```
