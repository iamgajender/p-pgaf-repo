pipeline {

    agent any

    environment {

        DOCKER_USER = "gajender07070707"

        BACKEND_IMAGE = "${DOCKER_USER}/pg-sa-backend"

        FRONTEND_IMAGE = "${DOCKER_USER}/pg-sa-frontend"

        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {

            steps {
                checkout scm
            }
        }

        stage('Verify Workspace') {

            steps {

                sh '''
                pwd
                ls -la
                '''
            }
        }

        stage('Build Backend Image') {

            steps {

                sh """
                docker build \
                -t ${BACKEND_IMAGE}:${IMAGE_TAG} \
                -t ${BACKEND_IMAGE}:latest \
                -f backend/Dockerfile .
                """
            }
        }

        stage('Build Frontend Image') {

            steps {

                sh """
                docker build \
                -t ${FRONTEND_IMAGE}:${IMAGE_TAG} \
                -t ${FRONTEND_IMAGE}:latest \
                -f frontend/Dockerfile .
                """
            }
        }

        stage('DockerHub Login') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    )
                ]) {

                    sh '''
                    echo "$DOCKER_PASSWORD" | docker login \
                    -u "$DOCKER_USERNAME" \
                    --password-stdin
                    '''
                }
            }
        }

        stage('Push Backend Image') {

            steps {

                sh """
                docker push ${BACKEND_IMAGE}:${IMAGE_TAG}
                docker push ${BACKEND_IMAGE}:latest
                """
            }
        }

        stage('Push Frontend Image') {

            steps {

                sh """
                docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                docker push ${FRONTEND_IMAGE}:latest
                """
            }
        }

    }

    post {

        success {

            echo "CI Pipeline Completed Successfully"

            sh '''
            docker image ls | grep pg-sa
            '''
        }

        failure {

            echo "CI Pipeline Failed"
        }
    }
}
