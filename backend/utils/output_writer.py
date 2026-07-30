import os
from datetime import datetime


OUTPUT_FILE = "/opt/pg_sa/backend/output/deployment.txt"


def write_deployment_output(
    server_ip,
    ssh_user,
    postgres_version
):

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    with open(OUTPUT_FILE, "w") as file:

        file.write("=" * 70 + "\n")
        file.write("PostgreSQL Deployment Request\n")
        file.write("=" * 70 + "\n\n")

        file.write(
            f"Request Time       : {datetime.now()}\n"
        )

        file.write(
            f"Server IP          : {server_ip}\n"
        )

        file.write(
            f"SSH User           : {ssh_user}\n"
        )

        file.write(
            f"PostgreSQL Version : {postgres_version}\n"
        )

        file.write(
            "\nStatus             : Request Received\n"
        )

        file.write("=" * 70 + "\n")
