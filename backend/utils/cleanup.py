import os

FILES = [
    "/opt/pg_sa/backend/logs/ansible.log",
    "/opt/pg_sa/backend/output/deployment.txt",
    "/opt/pg_sa/backend/output/postgres_summary.json"
]

def cleanup_previous_deployment():

    for file_path in FILES:

        if os.path.exists(file_path):

            open(file_path, "w").close()
