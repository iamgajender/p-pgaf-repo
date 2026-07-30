async function installPostgres(){

    const deployment = {

        server_ip : document.getElementById("server_ip").value,

        ssh_user : document.getElementById("ssh_user").value,

        ssh_password : document.getElementById("ssh_password").value,

        postgres_version : document.getElementById("postgres_version").value

    };

    console.log(deployment);

    document.getElementById("status").innerHTML = "Sending Deployment Request...";

    try{

        const response = await fetch("/install",{

            method:"POST",

            headers:{

                "Content-Type":"application/json"

            },

            body:JSON.stringify(deployment)

        });

        const result = await response.json();

        document.getElementById("status").innerHTML = result.message;

        console.log(result);

    }

    catch(error){

        console.error(error);

        document.getElementById("status").innerHTML="Unable to reach Backend Server.";

    }

}
