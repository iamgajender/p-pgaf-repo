pipeline {

    agent any

    environment {

        DOCKER_USER = "gajender07070707"

        BACKEND_IMAGE = "${DOCKER_USER}/pg-sa-backend"
        FRONTEND_IMAGE = "${DOCKER_USER}/pg-sa-frontend"

        IMAGE_TAG = "${BUILD_NUMBER}"

        DEPLOY_PATH = "/home/jenkins/deployment/pg_sa/"
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
                hostname
                whoami
                pwd
                ls -lah
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

        stage('Deploy Locally') {
            steps {

                sh """
                cd ${DEPLOY_PATH}

                echo "IMAGE_TAG=${IMAGE_TAG}" > .env

                docker compose pull

                docker compose up -d

                docker ps
                """
            }
        }

        stage('Health Check') {
            steps {

                sh '''
                sleep 20

                curl -f http://localhost || exit 1
                '''
            }
        }
    }

    post {

        success {

            echo "=================================="
            echo "DEPLOYMENT SUCCESSFUL"
            echo "Build Number : ${BUILD_NUMBER}"
            echo "Image Tag    : ${IMAGE_TAG}"
            echo "=================================="
        }

        failure {

            echo "=================================="
            echo "DEPLOYMENT FAILED"
            echo "=================================="
        }

        always {

            sh '''
            docker image prune -f || true
            '''
        }
    }
}
