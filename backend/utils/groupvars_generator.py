import os
import yaml

GROUP_VAR_FILE = "/opt/pg_sa/pg_an/group_vars/postgres.yml"


def generate_group_vars(postgres_version, postgres_password):

    os.makedirs(
        os.path.dirname(GROUP_VAR_FILE),
        exist_ok=True
    )

    postgres_vars = {
        "postgres_version": int(postgres_version),
        "postgres_port": 5432,
        "postgres_data_directory":
            f"/var/lib/postgresql/{postgres_version}/main",
        # Consumed by the second play in standalone.yml to set the
        # postgres role's password after install. Plain-text in this
        # file for now per the earlier discussion — move to
        # ansible-vault before this touches a real production server.
        "postgres_superuser_password": postgres_password
    }

    with open(GROUP_VAR_FILE, "w") as file:
        yaml.dump(
            postgres_vars,
            file,
            default_flow_style=False,
            sort_keys=False
        )
