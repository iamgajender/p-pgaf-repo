import psycopg
from psycopg import sql
from psycopg import errors


# Table-level privileges exposed by the UI. Privilege names get spliced
# directly into GRANT/REVOKE statements (they can't be query parameters —
# Postgres doesn't allow that), so anything not in this allow-list is
# rejected before it ever reaches a query.
ALLOWED_PRIVILEGES = {
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "TRUNCATE", "REFERENCES", "TRIGGER", "ALL"
}

# Privileges valid at the DATABASE and SCHEMA grant levels — distinct
# from table privileges above, since Postgres scopes these differently
# (e.g. CONNECT only makes sense on a database, USAGE only on a schema).
ALLOWED_DATABASE_PRIVILEGES = {"CONNECT", "CREATE", "TEMP"}
ALLOWED_SCHEMA_PRIVILEGES = {"USAGE", "CREATE"}


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

            access_model = str(data.get("access_model") or "custom").strip().lower()
            is_rbac = access_model == "rbac"

            conn = self._connect(data)
            cursor = conn.cursor()

            if is_rbac:
                # RBAC flow:
                # 1. CREATE ROLE <user> LOGIN PASSWORD <pw>
                # 2. GRANT <role> TO <user>
                # 3. (optional) ALTER ROLE <user> SET ROLE <role>
                assign_role = self._require_username(data.get("assign_role"))

                cursor.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(username), sql.Literal(password)
                    )
                )
                cursor.execute(
                    sql.SQL("GRANT {} TO {}").format(
                        sql.Identifier(assign_role), sql.Identifier(username)
                    )
                )
                if bool(data.get("set_default_role", True)):
                    cursor.execute(
                        sql.SQL("ALTER ROLE {} SET ROLE {}").format(
                            sql.Identifier(username), sql.Identifier(assign_role)
                        )
                    )
                conn.commit()
                return {
                    "status": "success",
                    "message": (
                        f'User "{username}" created and assigned to role '
                        f'"{assign_role}" successfully.'
                    )
                }

            else:
                # Custom flow — direct attributes, no role assignment
                can_login = bool(data.get("can_login", True))
                superuser = bool(data.get("superuser", False))
                createdb = bool(data.get("createdb", False))

                # NOTE: the PASSWORD clause in CREATE ROLE / ALTER ROLE is
                # part of Postgres's utility-statement grammar and does NOT
                # accept a bind parameter ($1/%s). sql.Literal() still
                # escapes the value safely — it embeds it as a quoted
                # literal in the statement text instead of a parameter.
                cursor.execute(
                    sql.SQL("CREATE ROLE {} WITH {} {} {} PASSWORD {}").format(
                        sql.Identifier(username),
                        sql.SQL("LOGIN" if can_login else "NOLOGIN"),
                        sql.SQL("SUPERUSER" if superuser else "NOSUPERUSER"),
                        sql.SQL("CREATEDB" if createdb else "NOCREATEDB"),
                        sql.Literal(password),
                    )
                )
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

            # Roles currently granted to this user — excludes pg_* built-in
            # predefined roles, same filter as list_users(), so this
            # reflects actual RBAC role assignments, not implicit ones.
            cursor.execute(
                r"""
                SELECT r.rolname
                FROM pg_auth_members m
                JOIN pg_roles r ON r.oid = m.roleid
                JOIN pg_roles u ON u.oid = m.member
                WHERE u.rolname = %s
                  AND r.rolname NOT LIKE 'pg\_%%'
                ORDER BY r.rolname
                """,
                (username,)
            )
            assigned_roles = [row[0] for row in cursor.fetchall()]

            return {
                "status": "success",
                "attributes": {
                    "can_login": can_login,
                    "superuser": superuser,
                    "createdb": createdb,
                    "createrole": createrole,
                    "replication": replication,
                    "connection_limit": conn_limit,
                    "valid_until": valid_until.isoformat() if valid_until else None,
                    "assigned_roles": assigned_roles
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

            assign_role = data.get("assign_role") or None
            set_default_role = bool(data.get("set_default_role", False))

            if not clauses and not valid_until_clause and not password and not assign_role:
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

            if assign_role:
                # Find the user's current role memberships (excluding
                # pg_* built-ins) so we can revoke the old one(s) before
                # granting the new one — a user is meant to hold one
                # business role at a time in this design, not accumulate
                # them across every reassignment.
                cursor.execute(
                    r"""
                    SELECT r.rolname
                    FROM pg_auth_members m
                    JOIN pg_roles r ON r.oid = m.roleid
                    JOIN pg_roles u ON u.oid = m.member
                    WHERE u.rolname = %s
                      AND r.rolname NOT LIKE 'pg\_%%'
                    """,
                    (username,)
                )
                current_roles = [row[0] for row in cursor.fetchall()]

                for old_role in current_roles:
                    if old_role != assign_role:
                        cursor.execute(
                            sql.SQL("REVOKE {} FROM {}").format(
                                sql.Identifier(old_role), sql.Identifier(username)
                            )
                        )

                if assign_role not in current_roles:
                    cursor.execute(
                        sql.SQL("GRANT {} TO {}").format(
                            sql.Identifier(assign_role), sql.Identifier(username)
                        )
                    )

                if set_default_role:
                    cursor.execute(
                        sql.SQL("ALTER ROLE {} SET ROLE {}").format(
                            sql.Identifier(username), sql.Identifier(assign_role)
                        )
                    )

                changed.append(f'assigned role ({assign_role})')

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
                "message": f'No role named "{data.get("target_username")}" or "{data.get("assign_role")}" was found.'
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

    def list_databases(self, data):

        conn = None
        cursor = None

        try:

            conn = self._connect(data)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT datname
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
            """)

            databases = [row[0] for row in cursor.fetchall()]

            return {
                "status": "success",
                "databases": databases
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

    def list_schemas(self, data):

        conn = None
        cursor = None

        try:

            target_database = data.get("target_database")

            if not target_database:
                return {
                    "status": "error",
                    "message": "target_database is required."
                }

            # Schemas live inside a specific database — connect to the
            # one being asked about, not the one from the original
            # superuser connection.
            connect_data = dict(data)
            connect_data["database"] = target_database

            conn = self._connect(connect_data)
            cursor = conn.cursor()

            cursor.execute(r"""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                  AND schema_name NOT LIKE 'pg\_toast%'
                  AND schema_name NOT LIKE 'pg\_temp\_%'
                ORDER BY schema_name
            """)

            schemas = [row[0] for row in cursor.fetchall()]

            return {
                "status": "success",
                "schemas": schemas
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

    def list_tables(self, data):

        conn = None
        cursor = None

        try:

            target_database = data.get("target_database")
            schema = data.get("schema")

            if not target_database or not schema:
                return {
                    "status": "error",
                    "message": "target_database and schema are required."
                }

            connect_data = dict(data)
            connect_data["database"] = target_database

            conn = self._connect(connect_data)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (schema,)
            )

            tables = [row[0] for row in cursor.fetchall()]

            return {
                "status": "success",
                "tables": tables
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

    def update_privileges(self, data):

        conn = None
        cursor = None

        try:

            username = self._require_username(data.get("target_username"))
            action = str(data.get("action", "grant")).strip().lower()
            schema = str(data.get("schema") or "public").strip()

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

            # "ALL" (the privilege, e.g. ALL PRIVILEGES) supersedes
            # anything else selected alongside it.
            if "ALL" in privileges:
                privileges = ["ALL"]

            # tables is a list of specific table names, or empty/absent
            # to mean "every table in the schema" (the old behavior).
            # This is the fix for the real gap flagged in review: GRANT
            # ON ALL TABLES IN SCHEMA has no way to target just
            # "customers" — now it only does that when nothing specific
            # was selected.
            requested_tables = [t.strip() for t in (data.get("tables") or []) if t and t.strip()]

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

            verb = sql.SQL("GRANT") if action == "grant" else sql.SQL("REVOKE")
            preposition = sql.SQL("TO") if action == "grant" else sql.SQL("FROM")

            if requested_tables:
                target_clause = sql.SQL("TABLE {}").format(
                    sql.SQL(", ").join(sql.Identifier(schema, t) for t in requested_tables)
                )
                target_description = f'table(s) {", ".join(requested_tables)}'
            else:
                target_clause = sql.SQL("ALL TABLES IN SCHEMA {}").format(sql.Identifier(schema))
                target_description = f'all tables in schema "{schema}"'

            if action == "grant":
                query = sql.SQL("GRANT {} ON {} TO {}").format(
                    privilege_clause, target_clause, sql.Identifier(username)
                )
            else:
                query = sql.SQL("REVOKE {} ON {} FROM {}").format(
                    privilege_clause, target_clause, sql.Identifier(username)
                )

            cursor.execute(query)
            conn.commit()

            return {
                "status": "success",
                "message": (
                    f'{"Granted" if action == "grant" else "Revoked"} '
                    f'{", ".join(privileges)} on {target_description} in '
                    f'"{connect_data["database"]}" '
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

    ##############################################################

    def create_role(self, data):

        conn = None
        cursor = None

        try:

            role_name = self._require_username(data.get("role_name"))
            can_login = bool(data.get("can_login", False))

            target_database = data.get("target_database")
            schema = str(data.get("schema") or "public").strip()

            db_privileges = [p.strip().upper() for p in (data.get("database_privileges") or []) if p]
            schema_privileges = [p.strip().upper() for p in (data.get("schema_privileges") or []) if p]
            table_privileges = [p.strip().upper() for p in (data.get("table_privileges") or []) if p]

            invalid_db = [p for p in db_privileges if p not in ALLOWED_DATABASE_PRIVILEGES]
            if invalid_db:
                return {
                    "status": "error",
                    "message": f"Unsupported database privilege(s): {', '.join(invalid_db)}"
                }

            invalid_schema = [p for p in schema_privileges if p not in ALLOWED_SCHEMA_PRIVILEGES]
            if invalid_schema:
                return {
                    "status": "error",
                    "message": f"Unsupported schema privilege(s): {', '.join(invalid_schema)}"
                }

            invalid_table = [p for p in table_privileges if p not in ALLOWED_PRIVILEGES]
            if invalid_table:
                return {
                    "status": "error",
                    "message": f"Unsupported table privilege(s): {', '.join(invalid_table)}"
                }

            if "ALL" in table_privileges:
                table_privileges = ["ALL"]

            apply_existing = bool(data.get("apply_existing", True))
            apply_future = bool(data.get("apply_future", True))

            # Step 1: CREATE ROLE. Roles are cluster-wide (not tied to a
            # database), so this uses the original connection info as-is.
            conn = self._connect(data)
            cursor = conn.cursor()

            query = sql.SQL("CREATE ROLE {} {}").format(
                sql.Identifier(role_name),
                sql.SQL("LOGIN" if can_login else "NOLOGIN")
            )
            cursor.execute(query)
            conn.commit()

            cursor.close()
            conn.close()
            conn = None
            cursor = None

            granted = []

            # Step 2: everything below is per-database, so it needs its
            # own connection to target_database — same reason
            # update_privileges() reconnects for schema/table grants.
            if target_database and (db_privileges or schema_privileges or table_privileges):

                connect_data = dict(data)
                connect_data["database"] = target_database

                conn = self._connect(connect_data)
                cursor = conn.cursor()

                if db_privileges:
                    priv_clause = sql.SQL(", ").join(sql.SQL(p) for p in db_privileges)
                    cursor.execute(
                        sql.SQL("GRANT {} ON DATABASE {} TO {}").format(
                            priv_clause, sql.Identifier(target_database), sql.Identifier(role_name)
                        )
                    )
                    granted.append(f'database privileges ({", ".join(db_privileges)})')

                if schema_privileges:
                    priv_clause = sql.SQL(", ").join(sql.SQL(p) for p in schema_privileges)
                    cursor.execute(
                        sql.SQL("GRANT {} ON SCHEMA {} TO {}").format(
                            priv_clause, sql.Identifier(schema), sql.Identifier(role_name)
                        )
                    )
                    granted.append(f'schema privileges ({", ".join(schema_privileges)})')

                if table_privileges:
                    priv_clause = sql.SQL(", ").join(sql.SQL(p) for p in table_privileges)

                    if apply_existing:
                        cursor.execute(
                            sql.SQL("GRANT {} ON ALL TABLES IN SCHEMA {} TO {}").format(
                                priv_clause, sql.Identifier(schema), sql.Identifier(role_name)
                            )
                        )
                        granted.append("existing tables")

                    if apply_future:
                        # This is the piece that keeps new tables from
                        # needing a manual GRANT every time — it only
                        # applies to tables created BY role_name itself
                        # going forward, which matches the "owner role
                        # creates objects, members inherit access"
                        # pattern this whole design is built around.
                        cursor.execute(
                            sql.SQL(
                                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA {} "
                                "GRANT {} ON TABLES TO {}"
                            ).format(
                                sql.Identifier(role_name), sql.Identifier(schema),
                                priv_clause, sql.Identifier(role_name)
                            )
                        )
                        granted.append("future tables (default privileges)")

                conn.commit()

            summary = f' with {", ".join(granted)}' if granted else ""

            return {
                "status": "success",
                "message": f'Role "{role_name}" created successfully{summary}.'
            }

        except errors.DuplicateObject:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": f'A role named "{data.get("role_name")}" already exists.'
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

    def delete_user(self, data):

        conn = None
        cursor = None

        try:

            username = self._require_username(data.get("target_username"))

            conn = self._connect(data)
            cursor = conn.cursor()

            cursor.execute(
                sql.SQL("DROP ROLE {}").format(sql.Identifier(username))
            )
            conn.commit()

            return {
                "status": "success",
                "message": f'User "{username}" deleted successfully.'
            }

        except errors.UndefinedObject:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": f'No role named "{data.get("target_username")}" was found.'
            }

        except errors.DependentObjectsStillExist as e:

            if conn:
                conn.rollback()

            return {
                "status": "error",
                "message": (
                    f'Cannot delete "{data.get("target_username")}" — it still owns '
                    f'objects or has active grants. Reassign or drop those first. '
                    f'({str(e).strip()})'
                )
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

    def modify_role(self, data):

        conn = None
        cursor = None

        try:

            role_name = self._require_username(data.get("target_role"))

            conn = self._connect(data)
            cursor = conn.cursor()

            # Confirm the role actually exists before doing anything else
            # — gives a clean error instead of failing partway through a
            # multi-statement grant sequence.
            cursor.execute(
                "SELECT rolcanlogin FROM pg_roles WHERE rolname = %s",
                (role_name,)
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "status": "error",
                    "message": f'No role named "{role_name}" was found.'
                }

            changed = []

            # Optional LOGIN/NOLOGIN change
            requested_login = data.get("can_login")
            if requested_login is not None and bool(requested_login) != row[0]:
                cursor.execute(
                    sql.SQL("ALTER ROLE {} WITH {}").format(
                        sql.Identifier(role_name),
                        sql.SQL("LOGIN" if requested_login else "NOLOGIN")
                    )
                )
                changed.append("login attribute")

            target_database = data.get("target_database")
            schema = str(data.get("schema") or "public").strip()

            db_privileges = [p.strip().upper() for p in (data.get("database_privileges") or []) if p]
            schema_privileges = [p.strip().upper() for p in (data.get("schema_privileges") or []) if p]
            table_privileges = [p.strip().upper() for p in (data.get("table_privileges") or []) if p]

            invalid_db = [p for p in db_privileges if p not in ALLOWED_DATABASE_PRIVILEGES]
            invalid_schema = [p for p in schema_privileges if p not in ALLOWED_SCHEMA_PRIVILEGES]
            invalid_table = [p for p in table_privileges if p not in ALLOWED_PRIVILEGES]
            if invalid_db or invalid_schema or invalid_table:
                return {
                    "status": "error",
                    "message": f"Unsupported privilege(s): {', '.join(invalid_db + invalid_schema + invalid_table)}"
                }

            if "ALL" in table_privileges:
                table_privileges = ["ALL"]

            apply_existing = bool(data.get("apply_existing", True))
            apply_future = bool(data.get("apply_future", True))

            conn.commit()  # commit the LOGIN change before switching connections
            cursor.close()
            conn.close()
            conn = None
            cursor = None

            if target_database and (db_privileges or schema_privileges or table_privileges):

                connect_data = dict(data)
                connect_data["database"] = target_database

                conn = self._connect(connect_data)
                cursor = conn.cursor()

                if db_privileges:
                    priv_clause = sql.SQL(", ").join(sql.SQL(p) for p in db_privileges)
                    cursor.execute(
                        sql.SQL("GRANT {} ON DATABASE {} TO {}").format(
                            priv_clause, sql.Identifier(target_database), sql.Identifier(role_name)
                        )
                    )
                    changed.append(f'database privileges ({", ".join(db_privileges)})')

                if schema_privileges:
                    priv_clause = sql.SQL(", ").join(sql.SQL(p) for p in schema_privileges)
                    cursor.execute(
                        sql.SQL("GRANT {} ON SCHEMA {} TO {}").format(
                            priv_clause, sql.Identifier(schema), sql.Identifier(role_name)
                        )
                    )
                    changed.append(f'schema privileges ({", ".join(schema_privileges)})')

                if table_privileges:
                    priv_clause = sql.SQL(", ").join(sql.SQL(p) for p in table_privileges)

                    if apply_existing:
                        cursor.execute(
                            sql.SQL("GRANT {} ON ALL TABLES IN SCHEMA {} TO {}").format(
                                priv_clause, sql.Identifier(schema), sql.Identifier(role_name)
                            )
                        )
                        changed.append("existing tables")

                    if apply_future:
                        cursor.execute(
                            sql.SQL(
                                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA {} "
                                "GRANT {} ON TABLES TO {}"
                            ).format(
                                sql.Identifier(role_name), sql.Identifier(schema),
                                priv_clause, sql.Identifier(role_name)
                            )
                        )
                        changed.append("future tables (default privileges)")

                conn.commit()

            if not changed:
                return {
                    "status": "success",
                    "message": f'No changes were needed for "{role_name}".'
                }

            return {
                "status": "success",
                "message": f'Updated {", ".join(changed)} for "{role_name}".'
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

    def get_role_members(self, data):

        conn = None
        cursor = None

        try:

            role_name = self._require_username(data.get("target_role"))

            conn = self._connect(data)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT m.rolname
                FROM pg_auth_members am
                JOIN pg_roles r ON am.roleid = r.oid
                JOIN pg_roles m ON am.member = m.oid
                WHERE r.rolname = %s
                ORDER BY m.rolname
                """,
                (role_name,)
            )
            members = [row[0] for row in cursor.fetchall()]

            return {
                "status": "success",
                "members": members
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
