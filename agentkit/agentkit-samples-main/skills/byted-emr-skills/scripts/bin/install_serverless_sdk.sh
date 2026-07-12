#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ASSETS_DIR="$SCRIPT_DIR/../../assets"
pip install $ASSETS_DIR/libs/python_serverless-1.0.3.4.1-py3-none-any.whl