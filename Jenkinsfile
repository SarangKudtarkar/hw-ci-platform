pipeline {
    agent any

    parameters {
        string(
            name: 'INPUT_REPO_URL',
            defaultValue: 'https://github.com/SarangKudtarkar/RTL2GDS-Asynchronous-FIFO.git',
            description: 'Git URL of the IP repository to verify'
        )
        string(
            name: 'DESIGN_ARGS',
            defaultValue: '--top async_fifo --rtl src/async_fifo.v --tb async_fifo_tb.v --sta require',
            description: 'Options for flow/pipeline.py. Leave empty to use hwci.toml or auto-discovery in the IP repository.'
        )
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
                    INPUT_DIR="../input-$(basename "$INPUT_REPO_URL" .git)"

                    if [ ! -d "$INPUT_DIR/.git" ]; then
                        git clone "$INPUT_REPO_URL" "$INPUT_DIR"
                    fi

                    echo "=== Input Repository ==="
                    git -C "$INPUT_DIR" status --short
                    git -C "$INPUT_DIR" log -1 --oneline
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
                    # Override PDK_ROOT in the node environment if the PDK lives elsewhere.
                    export PDK_ROOT="${PDK_ROOT:-/home/sarang/.volare}"

                    INPUT_DIR="../input-$(basename "$INPUT_REPO_URL" .git)"

                    # DESIGN_ARGS is intentionally unquoted so it splits into options.
                    python3 flow/pipeline.py "$INPUT_DIR" $DESIGN_ARGS
                '''
            }
        }
    }

    post {
        always {
            echo "Hardware CI pipeline completed."
        }

        success {
            echo "BUILD SUCCESS: all CI stages passed."
        }

        failure {
            echo "BUILD FAILURE: Check the Jenkins console output."
        }
    }
}
