# HW-CI Health & Stream Analytics Platform

A lightweight, open-source CI/CD and analytics platform for multi-IP ASIC/SoC hardware repositories.

This project demonstrates how a hardware repository can be treated like a software CI system: every commit can be checked through a repeatable RTL quality pipeline, with build history stored in SQLite and visualized through a Streamlit dashboard.

The current MVP uses the `RTL2GDS-Asynchronous-FIFO` repository as the testbed.

---

## 1. Project Overview

### Problem

Hardware repositories often contain multiple RTL/IP blocks, testbenches, constraints, generated reports, and physical-design artifacts. It can become difficult to answer:

- Is the latest RTL healthy?
- Did a recent commit break the design?
- Which CI stage failed?
- How long are builds taking?
- Is the repository ready for release?
- How has build health changed over time?

### Solution

This project provides a Python-driven hardware CI pipeline that currently performs:

```text
Git Repository
      |
      v
   RTL Source
      |
      v
+-------------+
|    Lint     |  Verilator
+-------------+
      |
      v
+-------------+
| Synthesis   |  Yosys
+-------------+
      |
      v
+-------------+
| Simulation  |  Icarus Verilog
+-------------+
      |
      v
 SQLite Build Database
      |
      v
 Streamlit Dashboard

The pipeline stops when a quality gate fails and records the result in the database.

## 2. Current Features
Git repository metadata ingestion
Commit and branch tracking
Verilator RTL linting
Yosys synthesis/hierarchy checking
Icarus Verilog simulation
Automatic stage-by-stage pipeline execution
Early pipeline failure handling
Runtime measurement for every stage
SQLite build history
Build pass/fail analytics
Streamlit health dashboard
Runtime trend visualization
Build history table
Demonstration of failed and recovered builds

## 3. Technology Stack
Component	Tool
Language	Python 3
Version control	Git
Lint	Verilator
Synthesis	Yosys
Simulation	Icarus Verilog
Database	SQLite
Analytics	pandas
Dashboard	Streamlit
Hardware testbed	Asynchronous FIFO RTL
Environment	Python virtual environment

## 4. Repository Structure
hw-ci-platform/
├── analysis/
│   └── analytics.py
│
├── config/
│
├── dashboard/
│   └── app.py
│
├── db/
│   ├── database.py
│   ├── build.db
│   └── schema.sql
│
├── farm/
│
├── flow/
│   ├── lint.py
│   ├── synth.py
│   ├── simulate.py
│   └── pipeline.py
│
├── logs/
├── results/
│
├── vcs/
│   └── hooks/
│
├── .venv/
│
└── README.md

The hardware repository is kept separately as the CI input/testbed:

hw-ci-health/
├── hw-ci-platform/
└── input-repo/

## 5. Prerequisites

The following tools should be installed:

Git
Python 3
Verilator
Yosys
Icarus Verilog

Check the installations:

git --version
python3 --version
verilator --version
yosys --version
iverilog -V

Example environment used during development:

Python       3.12.3
Verilator    5.050
Yosys        0.33
Icarus       12.0

Exact versions may differ.

## 6. Clone the Project

Create a workspace:

mkdir -p ~/projects/hw-ci-health
cd ~/projects/hw-ci-health

Clone the hardware test repository:

git clone https://github.com/SarangKudtarkar/RTL2GDS-Asynchronous-FIFO.git input-repo

Clone or place this CI platform repository beside it:

~/projects/hw-ci-health/
├── input-repo/
└── hw-ci-platform/

Enter the platform:

cd ~/projects/hw-ci-health/hw-ci-platform

## 7. Create the Python Environment

Linux distributions may prevent packages from being installed into the system Python environment.

Create a virtual environment:

python3 -m venv .venv

Activate it:

source .venv/bin/activate

You should see something similar to:

(.venv) user@machine:~/projects/hw-ci-health/hw-ci-platform$

Install the Python dependencies:

python -m pip install streamlit pandas

Verify Streamlit:

python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"

## 8. Initialize the Database

The project uses SQLite to store build and stage results.

Initialize the schema:

sqlite3 db/build.db < db/schema.sql

Check that the tables exist:

sqlite3 db/build.db ".tables"

Expected tables:

builds
stage_results

The database contains two main concepts:

builds

Stores one record for each pipeline execution.

Important fields include:

Build ID
Git commit
Git branch
Timestamp
Overall status
Total runtime
stage_results

Stores individual pipeline stage results.

For example:

build 1 | lint       | PASS | 0.687 sec
build 1 | synthesis  | PASS | 0.254 sec
build 1 | simulation | PASS | 0.257 sec

## 9. Verify the Hardware Repository

Enter the test repository:

cd ../input-repo

Check Git status:

git status

The repository should ideally be clean before running a normal CI build.

Verify the original simulation:

iverilog -o async_fifo_tb async_fifo.v async_fifo_tb.v
vvp async_fifo_tb

The testbench should complete successfully and show FIFO write/read activity.

Return to the CI platform:

cd ../hw-ci-platform

## 10. Run Individual CI Stages

The platform can execute individual stages independently.

10.1 Lint

Run:

python flow/lint.py ../input-repo/async_fifo.v
What it does

Runs Verilator in lint-only mode.

Conceptually:

RTL
 |
 v
Verilator
 |
 +-- PASS
 +-- FAIL

Lint catches issues such as invalid syntax, structural problems, and many RTL coding problems before more expensive stages run.

10.2 Synthesis

Run:

python flow/synth.py ../input-repo/async_fifo.v async_fifo
What it does

Runs Yosys against the RTL.

The current synthesis flow performs:

read_verilog
      |
hierarchy -top
      |
proc
      |
opt
      |
check
      |
stat

This validates that Yosys can understand and process the RTL hierarchy.

10.3 Simulation

Run:

python flow/simulate.py ../input-repo/async_fifo.v ../input-repo/async_fifo_tb.v
What it does
Compiles the RTL and testbench with Icarus Verilog.
Executes the generated simulation.
Reports PASS/FAIL.
Measures runtime.

## 11. Run the Complete Pipeline

From:

~/projects/hw-ci-health/hw-ci-platform

run:

python flow/pipeline.py \
  ../input-repo/async_fifo.v \
  ../input-repo/async_fifo_tb.v \
  async_fifo \
  ../input-repo

The arguments are:

<RTL file>
<testbench file>
<top module>
<Git repository path>

Example:

RTL file:       ../input-repo/async_fifo.v
Testbench:      ../input-repo/async_fifo_tb.v
Top module:     async_fifo
Git repository: ../input-repo

The pipeline performs:

[1/3] Lint
   |
   | PASS
   v
[2/3] Synthesis
   |
   | PASS
   v
[3/3] Simulation
   |
   | PASS
   v
Build recorded in SQLite

If lint fails:

[1/3] Lint
   |
   | FAIL
   v
Pipeline stopped

Synthesis and simulation are not executed.

## 12. Git Metadata

The pipeline automatically extracts:

git branch --show-current

and:

git rev-parse HEAD

This allows every build to be associated with a specific Git state.

For example:

Branch: main
Commit: 70a3164b512b2d15110ff1d84495748ad8f5677d

This is important because hardware CI results should be traceable back to the exact RTL revision that produced them.

## 13. Build Analytics

Run:

python analysis/analytics.py

The analytics script reports:

CI BUILD SUMMARY
========================================
Total builds:       3
Passed builds:      2
Pass rate:          66.67%
Average runtime:    0.528 sec

The values will change as more builds are executed.

The current analytics layer demonstrates:

Total build count
Number of successful builds
Pass rate
Average pipeline runtime

## 14. Start the Dashboard

Make sure the virtual environment is active:

source .venv/bin/activate

Start Streamlit:

streamlit run dashboard/app.py

Streamlit will provide a local browser URL, normally similar to:

http://localhost:8501

The dashboard currently displays:

Total Builds
Passed Builds
Failed Builds
Pass Rate
Overall Pipeline Health
Build Runtime Trend
Build History
Average Pipeline Runtime
