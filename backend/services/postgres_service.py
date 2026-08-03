import psycopg


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

            cursor.execute("""

                SELECT rolname

                FROM pg_roles

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

        return {

            "status": "success",

            "message": "Create User API not implemented yet."

        }

    ##############################################################

    def modify_user(self, data):

        return {

            "status": "success",

            "message": "Modify User API not implemented yet."

        }

    ##############################################################

    def update_privileges(self, data):

        return {

            "status": "success",

            "message": "Privileges API not implemented yet."

        }
