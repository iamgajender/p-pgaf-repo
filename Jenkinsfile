pipeline {
    agent any

    stages {

        stage('Check Agent') {
            steps {
                sh '''
                echo "===== HOSTNAME ====="
                hostname

                echo "===== USER ====="
                whoami

                echo "===== IP ADDRESS ====="
                ip a

                echo "===== CURRENT DIRECTORY ====="
                pwd

                echo "===== WORKSPACE ====="
                echo $WORKSPACE
                '''
            }

        }

    }
}
