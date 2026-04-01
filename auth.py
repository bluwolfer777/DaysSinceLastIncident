"""LDAP authentication against samt.lan — verifies credentials and group membership."""

import os
import ssl

from ldap3 import ALL, NTLM, SUBTREE, Server, Connection, Tls
from ldap3.core.exceptions import LDAPBindError, LDAPException

LDAP_SERVER       = os.environ.get("LDAP_SERVER",        "samt.lan")
LDAP_DOMAIN       = os.environ.get("LDAP_DOMAIN",        "SAMT")
LDAP_BASE_DN      = os.environ.get("LDAP_BASE_DN",       "dc=samt,dc=lan")
LDAP_REQUIRED_GROUP = os.environ.get("LDAP_REQUIRED_GROUP", "GG_Sistemisti")
LDAP_USE_SSL      = os.environ.get("LDAP_USE_SSL", "false").lower() == "true"


def _make_server() -> Server:
    if LDAP_USE_SSL:
        tls = Tls(validate=ssl.CERT_REQUIRED)
        return Server(LDAP_SERVER, port=636, use_ssl=True, tls=tls, get_info=ALL, connect_timeout=5)
    return Server(LDAP_SERVER, port=389, get_info=ALL, connect_timeout=5)


def ldap_check(username: str, password: str) -> tuple[bool, str]:
    """
    Attempt to:
      1. Bind to the domain controller as DOMAIN\\username with the given password.
      2. Search for the user's memberOf attribute.
      3. Confirm membership in LDAP_REQUIRED_GROUP.

    Returns (True, "OK") on success or (False, reason) on failure.
    """
    if not username or not password:
        return False, "Username and password are required."

    try:
        server = _make_server()
        conn = Connection(
            server,
            user=f"{LDAP_DOMAIN}\\{username}",
            password=password,
            authentication=NTLM,
            auto_bind=True,
            receive_timeout=10,
        )
    except LDAPBindError:
        return False, "Invalid credentials."
    except LDAPException as exc:
        return False, f"LDAP error: {exc}"
    except Exception as exc:
        return False, f"Cannot reach directory server: {exc}"

    try:
        conn.search(
            LDAP_BASE_DN,
            f"(sAMAccountName={username})",
            search_scope=SUBTREE,
            attributes=["cn", "memberOf"],
        )

        if not conn.entries:
            return False, "User not found in directory."

        entry = conn.entries[0]
        member_of: list[str] = (
            entry.memberOf.values if hasattr(entry, "memberOf") and entry.memberOf else []
        )

        for group_dn in member_of:
            # Group DN looks like: CN=GG_Sistemisti,OU=Groups,DC=samt,DC=lan
            cn_part = group_dn.split(",")[0]
            if "=" in cn_part:
                group_name = cn_part.split("=", 1)[1]
                if group_name.lower() == LDAP_REQUIRED_GROUP.lower():
                    return True, "OK"

        return False, f"Not a member of {LDAP_REQUIRED_GROUP}."

    finally:
        try:
            conn.unbind()
        except Exception:
            pass
