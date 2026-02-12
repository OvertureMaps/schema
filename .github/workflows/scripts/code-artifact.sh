#!/usr/bin/env bash

set -euo pipefail

readonly subcommand="$1"

function token() {
  local -r aws_account_id="$1"
  local -r aws_region="$2"
  local -r domain="$3"

  aws codeartifact get-authorization-token \
    --region "$aws_region" \
    --domain "$domain" \
    --domain-owner "$aws_account_id" \
    --query authorizationToken \
    --output text
}

function repo_url() {
  local -r token="$1"
  local -r credentials="${token:+aws:$token@}"
  local -r aws_account_id="$2"
  local -r aws_region="$3"
  local -r domain="$4"
  local -r repository="$5"
  local -r suffix="$6"

  printf "https://%s%s-%s.d.codeartifact.%s.amazonaws.com/pypi/%s/%s\n" \
    "$credentials" "$domain" "$aws_account_id" "$aws_region" "$repository" "$suffix"
}

case "$subcommand" in
  token)
    if [ $# -ne 4 ]; then
      >&2 echo "Usage: $0 token <aws_account_id> <aws_region> <domain>"
      exit 1
    fi
    token "$2" "$3" "$4"
    ;;

  index-url|publish-url)
    if [ $# -ne 5 ]; then
      >&2 echo "Usage: $0 $subcommand <aws_account_id> <aws_region> <domain> <repository>"
      exit 1
    fi

    if [ "$subcommand" = "index-url" ]; then
      repo_url "" "$2" "$3" "$4" "$5" "simple/"
    else
      repo_url $(token) "$2" "$3" "$4" "$5" ""
    fi
    ;;

  *)
    >&2 echo "Unknown subcommand: ${subcommand:-<missing>}"
    >&2 echo "Valid subcommands: token | index-url | publish-url"
    exit 1
    ;;
esac
