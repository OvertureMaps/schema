#!/usr/bin/env bash

set -euo pipefail

if [ $# -ne 4 ]; then
  >&2 echo "Usage: $0 <aws_account_id> <aws_region> <domain> <repository>"
  exit 1
fi

readonly aws_account_id="$1"
readonly aws_region="$2"
readonly domain="$3"
readonly repository="$4"

# Use the `aws-actions/configure-aws-credentials` GitHub action before calling this script to
# ensure the necessary AWS credentials, for an appropriate role, are available in the environment.

auth_token=$( \
    aws codeartifact get-authorization-token \
        --region "$aws_region" \
        --domain "$domain" \
        --domain-owner "$aws_account_id" \
        --query authorizationToken \
        --output text)

printf "https://aws:%s@%s-%s.d.codeartifact.%s.amazonaws.com/\n" \
    "$auth_token" "$domain"  "$aws_account_id" "$aws_region"
