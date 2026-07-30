import os
import yaml


GROUP_VAR_FILE = "/opt/pg_sa/pg_an/group_vars/postgres.yml"


def generate_group_vars(postgres_version):

    os.makedirs(
        os.path.dirname(GROUP_VAR_FILE),
        exist_ok=True
    )

    postgres_vars = {

        "postgres_version": int(postgres_version),

        "postgres_port": 5432,

        "postgres_data_directory":
            f"/var/lib/postgresql/{postgres_version}/main"

    }

    with open(GROUP_VAR_FILE, "w") as file:

        yaml.dump(

            postgres_vars,

            file,

            default_flow_style=False,

            sort_keys=False

        )
