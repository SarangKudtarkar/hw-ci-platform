pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
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
                    python3 flow/pipeline.py ../input-repo/src/async_fifo.v ../input-repo/async_fifo_tb.v async_fifo ../input-repo
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
