pipeline {
    agent any

    stages {
        stage('Install Docker') {
            steps {
                echo 'Installing Docker (if not already installed)...'
                sh '''
                    if ! command -v docker &> /dev/null; then
                        sudo apt update -y
                        sudo apt install -y docker.io
                        sudo systemctl start docker
                    fi
                '''
            }
        }

        stage('Install AWS CLI') {
            steps {
                echo 'Installing AWS CLI (if not already installed)...'
                sh '''
                    if ! command -v aws &> /dev/null; then
                        sudo apt update -y
                        sudo apt install -y unzip
                        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                        unzip -o awscliv2.zip
                        sudo ./aws/install
                    fi
                '''
            }
        }

        stage('Git Checkout') {
            steps {
                // Create directory and move into it in the same shell
                sh '''
                    sudo mkdir -p /docker
                    cd /docker
                '''
                checkout([$class: 'GitSCM',
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[url: 'https://github.com/harshkhalkar/student-registration-flask-application.git']]
                ])
                // These will run in the workspace, not /docker
                sh 'rm -rf LICENSE README.md kubernetes docker-compose.yml init.sql Jenkinsfile'
                sh 'ls -l'
            }
        }

        stage('Build and Run Docker Container') {
            steps {
                sh '''
                    sudo docker build -t demo/purpose:v2 .
                    sudo docker run -d -p 5000:5000 --name pyapp demo/purpose:v2
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Running tests inside container...'
                sh '''
                    sudo docker ps
                    curl -s localhost:5000 || echo "Flask app not reachable"
                    sudo docker exec pyapp ls -l
                    sudo docker exec pyapp ls -l tests
                    sudo docker exec pyapp python3 -m unittest discover -s tests -t .
                '''
            }
        }

        stage('Push to ECR') {
            steps {
                sh '''
                    aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 873579225118.dkr.ecr.us-east-1.amazonaws.com
                    sudo docker tag demo/purpose:v2 873579225118.dkr.ecr.us-east-1.amazonaws.com/demo/purpose:v2
                    sudo docker push 873579225118.dkr.ecr.us-east-1.amazonaws.com/demo/purpose:v2
                '''
            }
        }
    }

    post {
        always {
            echo 'Cleaning up Docker resources...'
            sh '''
                sudo docker stop pyapp || true
                sudo docker rm pyapp || true
                sudo docker rmi demo/purpose:v2 || true
                sudo docker rmi $(sudo docker images -q) || true
            '''
        }
    }
}
