import os


INVENTORY_FILE = "/opt/pg_sa/pg_an/inventory/inventory.ini"


def generate_inventory(server_ip, ssh_user, ssh_password):

    os.makedirs(
        os.path.dirname(INVENTORY_FILE),
        exist_ok=True
    )

    inventory = f"""[postgres]
{server_ip}

[all:vars]
ansible_user={ssh_user}
ansible_password={ssh_password}
ansible_python_interpreter=/usr/bin/python3
"""

    with open(INVENTORY_FILE, "w") as file:

        file.write(inventory)
