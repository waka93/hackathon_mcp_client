# Table of Content
- [Environment Setup](#environment-setup)
- [Local Testing](#local-testing)

## Environment Setup

### Create virtual environment
```
# Skip if already installed
pip install uv

uv venv --python=3.12
```

### Activate virtual environment
`source .venv/bin/activate`

### Install dependencies
`uv sync`

### Create .env file
```
# Rename .env.template to .env
mv .env.template .env

# Populate the correct environment variables
```

## Local Testing

### Start MCP Server
Start your MCP server (not included in this repo)

Run the client with
`uv run agent.py`
