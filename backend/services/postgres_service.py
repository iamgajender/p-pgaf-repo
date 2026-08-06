import psycopg
from psycopg import sql
from psycopg import errors


# Table-level privileges exposed by the UI. Privilege names get spliced
# directly into GRANT/REVOKE statements (they can't be query parameters —
# Postgres doesn't allow that), so anything not in this allow-list is
# rejected before it ever reaches a query.
ALLOWED_PRIVILEGES = {"SELECT", "INSERT", "UPDATE", "DELETE", "ALL"}


class PostgresService:

    def __init__(self):
        pass

    ##############################################################

    def _connect(self, data):

        return psycopg.connect(

            host=data["server_ip"],

            port=data["server_port"],

            dbname=data["database"],

            user=data["username"],

            password=data["password"],

            connect_timeout=10

        )

    ##############################################################

    @staticmethod
    def _require_username(raw_username):
        username = str(raw_username or "").strip()
        if not username:
            raise ValueError("Username is required.")
        return username

    ##############################################################

    def test_connection(self, data):

        conn = None

        cursor = None

        try:

            conn = self._connect(data)

            cursor = conn.cursor()

            ##################################################

            cursor.execute("SELECT version();")
            postgres_version = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SELECT current_database();")
            current_database = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SELECT current_user;")
            current_user = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SELECT inet_server_addr();")
            server_ip = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SELECT inet_server_port();")
            server_port = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SHOW server_version;")
            server_version = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SELECT pg_is_in_recovery();")
            recovery = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SHOW data_directory;")
            data_directory = cursor.fetchone()[0]

            ##################################################

            cursor.execute("SHOW config_file;")
            config_file = cursor.fetchone()[0]

            ##################################################

            return {

                "status": "success",

                "message": "Connection Successful.",

                "postgres_version": postgres_version,

                "server_version": server_version,

                "current_database": current_database,

                "current_user": current_user,

                "server_ip": str(server_ip),

                "server_port": server_port,

                "recovery_mode": recovery,

                "data_directory": data_directory,

                "config_file": config_file

            }

        except Exception as e:

            return {

                "status": "error",

                "message": str(e)

            }

        finally:

            if cursor:
                cursor.close()

            if conn:
                conn.close()

    ##############################################################

    def list_users(self, data):

        conn = None

        cursor = None

        try:

            conn = self._connect(data)

            cursor = conn.cursor()

            cursor.execute(r"""

                SELECT rolname

                FROM pg_roles

                WHERE rolname NOT LIKE 'pg\_%'

                ORDER BY rolname

            """)

            users = []

            for row in cursor.fetchall():

                users.append(row[0])

            return {

                "status": "success",

                "users": users

            }

        except Exception as e:

            return {

                "status": "error",

                "message": str(e)

            }

        finally:

            if cursor:
                cursor.close()

            if conn:
                conn.close()

    ##############################################################

    def create_user(self, data):

        conn = None
        cursor = None

        try:

            username = self._require_username(data.get("new_username"))
            password = data.get("new_password") or ""

            if not password:
                return {
                    "status": "error",
                    "message": "Password is required."
                }

            can_login = bool(data.get("can_login", True))
            superuser = bool(data.get("superuser", False))
            createdb = bool(data.get("createdb", False))

            conn = self._connect(data)
            cursor = conn.cursor()

            # sql.Identifier safely quotes the role name (handles case,
            # special characters, reserved words). The password is passed
            # as a query parameter (%s) rather than spliced into the
            # string, so psycopg escapes it the same way it would for any
            # other value.
            # NOTE: the PASSWORD clause in CREATE ROLE / ALTER ROLE is part
            # of Postgres's utility-statement grammar and does NOT accept
            # a bind parameter ($1/%s) — that's what threw the "syntax
            # error at or near $1" you hit. sql.Literal() still escapes
            # the value safely, it just embeds it as a quoted literal in
            # the statement text instead of a separate parameter.
            query = sql.SQL("CREATE ROLE {} WITH {} {} {} PASSWORD {}").format(
                sql.Identifier(username),
                sql.SQL("LOGIN" if can_login else "NOLOGIN"),
                sql.SQL("SUPERUSER" if superuser else "NOSUPERUSER"),
                sql.SQL("CREATEDB" if createdb else "NOCREATEDB"),
                sql.Literal(password),
            )

            cursor.execute(query)
            conn.commit()

            return {
                "status": "success",
                "message": f'User "{username}" created successfully.'
            }

        except errors.DuplicateObject:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": f'A role named "{data.get("new_username")}" already exists.'
            }

        except Exception as e:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": str(e)
            }

        finally:

            if cursor:
                cursor.close()

            if conn:
                conn.close()

    ##############################################################

    def get_user_details(self, data):

        conn = None
        cursor = None

        try:

            username = self._require_username(data.get("target_username"))

            conn = self._connect(data)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                       rolreplication, rolconnlimit, rolvaliduntil
                FROM pg_roles
                WHERE rolname = %s
                """,
                (username,)
            )
            row = cursor.fetchone()

            if row is None:
                return {
                    "status": "error",
                    "message": f'No role named "{username}" was found.'
                }

            can_login, superuser, createdb, createrole, replication, conn_limit, valid_until = row

            return {
                "status": "success",
                "attributes": {
                    "can_login": can_login,
                    "superuser": superuser,
                    "createdb": createdb,
                    "createrole": createrole,
                    "replication": replication,
                    "connection_limit": conn_limit,
                    "valid_until": valid_until.isoformat() if valid_until else None
                }
            }

        except Exception as e:

            return {
                "status": "error",
                "message": str(e)
            }

        finally:

            if cursor:
                cursor.close()

            if conn:
                conn.close()

    ##############################################################

    def modify_user(self, data):

        conn = None
        cursor = None

        try:

            username = self._require_username(data.get("target_username"))
            password = data.get("new_password") or None

            conn = self._connect(data)
            cursor = conn.cursor()

            # Current attributes come straight from the database — the
            # source of truth — not from whatever the client last
            # rendered. This is what lets us build an ALTER ROLE with
            # only the clauses that actually changed, instead of always
            # resending every attribute (which is what was triggering
            # "permission denied ... SUPERUSER" on requests that never
            # meant to touch SUPERUSER at all).
            cursor.execute(
                """
                SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                       rolreplication, rolconnlimit
                FROM pg_roles
                WHERE rolname = %s
                """,
                (username,)
            )
            row = cursor.fetchone()

            if row is None:
                return {
                    "status": "error",
                    "message": f'No role named "{username}" was found.'
                }

            current = {
                "can_login": row[0],
                "superuser": row[1],
                "createdb": row[2],
                "createrole": row[3],
                "replication": row[4],
                "connection_limit": row[5],
            }

            boolean_attrs = {
                "can_login": "LOGIN",
                "superuser": "SUPERUSER",
                "createdb": "CREATEDB",
                "createrole": "CREATEROLE",
                "replication": "REPLICATION",
            }

            clauses = []
            changed = []

            for key, keyword in boolean_attrs.items():
                if key in data and data[key] is not None:
                    requested = bool(data[key])
                    if requested != current[key]:
                        clauses.append(sql.SQL(keyword if requested else f"NO{keyword}"))
                        changed.append(key)

            if data.get("connection_limit") not in (None, ""):
                requested_limit = int(data["connection_limit"])
                if requested_limit != current["connection_limit"]:
                    clauses.append(
                        sql.SQL("CONNECTION LIMIT {}").format(sql.Literal(requested_limit))
                    )
                    changed.append("connection_limit")

            valid_until_clause = None
            if data.get("valid_until"):
                valid_until_clause = sql.SQL("VALID UNTIL {}").format(
                    sql.Literal(data["valid_until"])
                )
                changed.append("valid_until")

            if not clauses and not valid_until_clause and not password:
                return {
                    "status": "success",
                    "message": f'No changes were needed — "{username}" already matches the requested settings.'
                }

            if clauses or valid_until_clause:
                all_clauses = clauses + ([valid_until_clause] if valid_until_clause else [])
                query = sql.SQL("ALTER ROLE {} WITH {}").format(
                    sql.Identifier(username),
                    sql.SQL(" ").join(all_clauses)
                )
                cursor.execute(query)

            if password:
                pw_query = sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(username), sql.Literal(password)
                )
                cursor.execute(pw_query)
                changed.append("password")

            conn.commit()

            return {
                "status": "success",
                "message": f'Updated {", ".join(changed)} for "{username}".'
            }

        except errors.UndefinedObject:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": f'No role named "{data.get("target_username")}" was found.'
            }

        except Exception as e:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": str(e)
            }

        finally:

            if cursor:
                cursor.close()

            if conn:
                conn.close()

    ##############################################################

    def update_privileges(self, data):

        conn = None
        cursor = None

        try:

            username = self._require_username(data.get("target_username"))
            action = str(data.get("action", "grant")).strip().lower()

            if action not in ("grant", "revoke"):
                return {
                    "status": "error",
                    "message": 'Action must be "grant" or "revoke".'
                }

            requested = data.get("privileges") or []
            privileges = [p.strip().upper() for p in requested if p]

            if not privileges:
                return {
                    "status": "error",
                    "message": "Select at least one privilege."
                }

            invalid = [p for p in privileges if p not in ALLOWED_PRIVILEGES]
            if invalid:
                return {
                    "status": "error",
                    "message": f"Unsupported privilege(s): {', '.join(invalid)}"
                }

            # "ALL" supersedes anything else selected alongside it.
            if "ALL" in privileges:
                privileges = ["ALL"]

            # Privileges are per-database — connect to the database the
            # privileges should apply to, not necessarily the database the
            # superuser originally connected to.
            connect_data = dict(data)
            connect_data["database"] = data.get("target_database") or data["database"]

            conn = self._connect(connect_data)
            cursor = conn.cursor()

            privilege_clause = sql.SQL(", ").join(
                sql.SQL(p) for p in privileges
            )

            if action == "grant":
                query = sql.SQL(
                    "GRANT {} ON ALL TABLES IN SCHEMA public TO {}"
                ).format(privilege_clause, sql.Identifier(username))
            else:
                query = sql.SQL(
                    "REVOKE {} ON ALL TABLES IN SCHEMA public FROM {}"
                ).format(privilege_clause, sql.Identifier(username))

            cursor.execute(query)
            conn.commit()

            return {
                "status": "success",
                "message": (
                    f'{"Granted" if action == "grant" else "Revoked"} '
                    f'{", ".join(privileges)} on "{connect_data["database"]}" '
                    f'{"to" if action == "grant" else "from"} "{username}".'
                )
            }

        except errors.UndefinedObject:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": f'No role named "{data.get("target_username")}" was found.'
            }

        except Exception as e:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": str(e)
            }

        finally:

            if cursor:
                cursor.close()

            if conn:
                conn.close()
