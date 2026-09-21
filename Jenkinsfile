pipeline {
    agent any

    environment {
        PDK_ROOT = '/home/sarang/.volare'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Fetch Input Repository') {
            steps {
                sh '''
                    if [ ! -d ../input-repo/.git ]; then
                        git clone https://github.com/SarangKudtarkar/RTL2GDS-Asynchronous-FIFO.git ../input-repo
                    fi

                    echo "=== Input Repository ==="
                    git -C ../input-repo status --short
                    git -C ../input-repo log -1 --oneline
                '''
            }
        }

        stage('Environment Check') {
            steps {
                sh '''
                    echo "=== Hardware CI Environment ==="
                    python3 --version
                    docker --version
                    yosys -V
                    verilator --version
                    iverilog -V
                '''
            }
        }

        stage('RTL CI Pipeline') {
            steps {
                sh '''
                    python3 flow/pipeline.py \
                        ../input-repo/src/async_fifo.v \
                        ../input-repo/async_fifo_tb.v \
                        async_fifo \
                        ../input-repo
                '''
            }
        }
    }

    post {
        always {
            echo "Hardware CI pipeline completed."
        }

        success {
            echo "BUILD SUCCESS: RTL checks and MMMC timing passed."
        }

        failure {
            echo "BUILD FAILURE: Check the Jenkins console output."
        }
    }
}
