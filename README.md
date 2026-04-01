# Days Since Last Incident

Mostra su un TV quanti giorni sono passati dall'ultimo incidente.  
Chi ha accesso admin (autenticato via Active Directory) può aggiungere e cancellare record. Quando viene aggiunto un record, il TV si aggiorna automaticamente.

---

## Installazione rapida

### Requisiti

- Un PC/server Linux con **Docker** installato
- Raggiungibilità del domain controller Active Directory dalla macchina che ospita l'app

---

### Passo 1 — Scarica il progetto

```bash
git clone https://github.com/bluwolfer777/DaysSinceLastIncident.git
cd DaysSinceLastIncident
```

---

### Passo 2 — Configura i dati LDAP

Apri il file `docker-compose.yml` con un editor di testo e modifica le quattro righe sotto `environment`:

```yaml
environment:
  LDAP_SERVER: "dc01.tuodominio.local"      # hostname o IP del domain controller
  LDAP_DOMAIN: "TUODOMINIO"                 # nome NetBIOS del dominio (tutto maiuscolo)
  LDAP_BASE_DN: "dc=tuodominio,dc=local"    # base DN del tuo AD
  LDAP_REQUIRED_GROUP: "GG_Sistemisti"      # gruppo AD che può fare login
```

> **Esempio reale:**  
> Se il tuo dominio è `azienda.lan` e il DC si chiama `dc01.azienda.lan`:
> ```yaml
> LDAP_SERVER: "dc01.azienda.lan"
> LDAP_DOMAIN: "AZIENDA"
> LDAP_BASE_DN: "dc=azienda,dc=lan"
> LDAP_REQUIRED_GROUP: "GG_Sistemisti"
> ```

---

### Passo 3 — Avvia l'applicazione

```bash
docker-compose up -d
```

L'app è pronta. Apri il browser su `http://localhost:5000`.

> Se vuoi usare un'altra porta (es. 8080), cambia `"5000:5000"` in `"8080:5000"` nel `docker-compose.yml`.

---

### Passo 4 — Punta il TV sulla dashboard

Sul TV (o su qualsiasi browser) apri:

```
http://<IP-del-server>:5000
```

La pagina si aggiorna da sola ogni volta che viene registrato un nuovo incidente.

---

### Passo 5 — Accedi al pannello admin

Dal tuo PC (non dal TV), apri:

```
http://<IP-del-server>:5000/admin/login
```

Inserisci le tue credenziali di dominio (username senza `DOMINIO\`, solo il nome utente).  
Devi essere membro del gruppo AD configurato al Passo 2.

---

## Comandi utili

| Operazione | Comando |
|---|---|
| Avviare l'app | `docker-compose up -d` |
| Fermare l'app | `docker-compose down` |
| Vedere i log in tempo reale | `docker logs -f days-since-last-incident` |
| Riavviare dopo una modifica alla config | `docker-compose down && docker-compose up -d` |
| Aggiornare all'ultima versione | `git pull && docker-compose up -d --build` |

---

## Usare l'immagine già pronta (senza clonare il repo)

Se non vuoi clonare il repo, puoi usare l'immagine già compilata da GitHub Container Registry.

Crea un file `docker-compose.yml` con questo contenuto:

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
      LDAP_SERVER: "dc01.tuodominio.local"
      LDAP_DOMAIN: "TUODOMINIO"
      LDAP_BASE_DN: "dc=tuodominio,dc=local"
      LDAP_REQUIRED_GROUP: "GG_Sistemisti"

volumes:
  dsli_data:
```

Poi:

```bash
docker-compose up -d
```

Docker scarica l'immagine automaticamente e l'app parte.

---

## Dove vengono salvati i dati

Il database SQLite è salvato in un volume Docker chiamato `dsli_data`.  
I dati **non vanno persi** se fermi o aggiorni il container.

Per fare un backup manuale del database:

```bash
docker cp days-since-last-incident:/app/instance/incidents.db ./backup_incidents.db
```

---

## Opzioni avanzate

| Variabile d'ambiente | Descrizione | Default |
|---|---|---|
| `LDAP_SERVER` | Hostname o IP del domain controller | `ldap.example.com` |
| `LDAP_DOMAIN` | Nome NetBIOS del dominio | `EXAMPLE` |
| `LDAP_BASE_DN` | Base DN per la ricerca utenti in AD | `dc=example,dc=com` |
| `LDAP_REQUIRED_GROUP` | Gruppo AD richiesto per l'accesso admin | `IT_Administrators` |
| `LDAP_USE_SSL` | `true` per usare LDAPS (porta 636) | `false` |

> **Nota su `LDAP_USE_SSL`:** se il DC usa un certificato self-signed o di una CA interna, installa il certificato nel sistema prima di abilitare SSL. Su reti interne senza SSL, le credenziali viaggiano in chiaro — accettabile solo su LAN trusted.

---

## Struttura del progetto

```
app.py              # applicazione Flask
auth.py             # autenticazione LDAP
requirements.txt    # dipendenze Python
Dockerfile
docker-compose.yml
templates/
  dashboard.html    # schermata pubblica per il TV
  login.html        # pagina di login admin
  admin.html        # pannello di gestione incidenti
instance/           # generato automaticamente — contiene DB e chiave di sessione
```
