# Project Manifest

## Directory Structure

```text
001 Agent Factory/
├── README.md
├── .gitignore
├── .env.example
├── 00-project/                 # Brief, scope, requirements, roadmap, decisions
├── 01-research/                # Research and user feedback
├── 03-src/
│   ├── agent_factory/          # Active v0.7 package
│   ├── data/                   # Active runtime data and versioned data snapshots
│   ├── tools/                  # Local maintenance utilities
│   └── versions/               # Historical source/config snapshots v0.1-v0.7
├── 05-tests/
│   ├── tests/                  # Active test suite
│   └── version-history/        # Tests from historical releases
├── 06-reports/
│   ├── evals/                  # Project and release evaluation reports
│   └── reports/                # Findings and versioned report snapshots
├── 07-docs/
│   └── specifications/        # Business plans and versioned specifications
└── 99-archive/                 # Original ZIPs and preserved conflicting exports
```
