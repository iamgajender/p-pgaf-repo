pipeline {

    agent any

    environment {

        DOCKER_USER = "gajender07070707"

        BACKEND_IMAGE = "${DOCKER_USER}/pg-sa-backend"
        FRONTEND_IMAGE = "${DOCKER_USER}/pg-sa-frontend"

        IMAGE_TAG = "${BUILD_NUMBER}"

        DEPLOY_HOST = "10.1.1.178"
        DEPLOY_PATH = "/opt/pg_sa"
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
                echo "===== HOSTNAME ====="
                hostname

                echo "===== USER ====="
                whoami

                echo "===== CURRENT DIRECTORY ====="
                pwd

                echo "===== WORKSPACE CONTENT ====="
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

        stage('Deploy To Server') {

            steps {

                sh """
                ssh root@${DEPLOY_HOST} '

                cd ${DEPLOY_PATH}

                echo "IMAGE_TAG=${IMAGE_TAG}" > .env

                docker compose pull

                docker compose up -d

                docker ps

                '
                """
            }
        }
    }

    post {

        success {

            echo "=================================="
            echo "CI/CD PIPELINE COMPLETED"
            echo "Build Number : ${BUILD_NUMBER}"
            echo "Image Tag    : ${IMAGE_TAG}"
            echo "=================================="

            sh '''
            docker image ls | grep pg-sa || true
            '''
        }

        failure {

            echo "=================================="
            echo "CI/CD PIPELINE FAILED"
            echo "=================================="
        }

        always {

            sh '''
            docker image prune -f || true
            '''
        }
    }
}
