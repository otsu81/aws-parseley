# AWS Parseley 3.0

Parseley is a parsing- and iteration tool intended to operate over a large number of AWS accounts, using an AWS Organization as source of truth.

This is a hodge-podge of functions meant to quickly return results based on the parameters in the respective functions in the `main.py` file.


## Requirements
* Access privileges to an AWS organization and a standardized role in each child account
* AWS CLI with profiles configured
* Python 3.6 or later

## Installation

1. `pip3 install -r requirements.txt`
2. Copy `.env.example` to `.env` and modify accordingly
3. Change which `.env` file you want to use in `settings.py`

## Running

Modify the `main.py` file to execute API calls as necessary