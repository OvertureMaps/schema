#!/usr/bin/env bash

set -eo pipefail
shopt -s lastpipe extglob

self="$(basename "$0")"
title="$self: Verify Overture schema"
declare -A modes
declare -a patterns

function usage() {
  >&2 <<EOF cat
usage: $self [OPTIONS] [PATTERNS]
  (or: $self --help)
EOF
}

function help() {
  >&2 <<EOF cat
$title

OPTIONS:
  -m, --mode=MODE validation mode - schema|examples|counterexamples
                   this argument maybe specified more than once, e.g.
                   \`-m schema -m examples\`. if this argument is omitted,
                   all validation modes are run.

EXAMPLES:
  $self --help
  $self
  $self -m schema
  $self -m examples -m counterexamples "transportation/.*\.json$"
EOF
}

function emit() {
  >&2 printf '%s: %s\n' "$self" "$*"
}

function bad_usage() {
  emit "$*"
  usage
  exit 64
}

function parse_args() {
  while (($#)); do
    local arg="$1"
    shift

    case "$arg" in
      -m|--mode)
        add_mode "$1"
        shift
        ;;
      --mode=*)
        add_mode "${arg/#*=/}"
        ;;
      -h|--help)
        usage
        echo
        help
        exit 0
        ;;
      *)
        patterns=("$arg" "$@")
        break
        ;;
    esac
  done

  if [ "${#modes[@]}" -eq 0 ]; then
    modes=([schema]=yes [examples]=yes [counterexamples]=yes)
  fi
}

function add_mode() {
  mode="$1"
  case "$mode" in
    s|sc|sch|sche|schem|schema)
      mode=schema
      ;;
    e|ex|exa|exam|examp|exampl|example|examples)
      mode=examples
      ;;
    c|co|cou|coun|count|counte|counter|countere|counterex|counterexa|counterexam|counterexamp|counterexampl|counterexample|counterexamples)
      mode=counterexamples
      ;;
    *)
      bad_usage "invalid mode: '$mode'. valid modes are: schema|examples|counterexamples"
      ;;
  esac
  modes["$mode"]=yes
}

schema_file=schema/schema.yaml

function match() {
  if [ "${#patterns}" == 0 ]; then
    return 0
  else
    candidate="$1"
    for pattern in "${patterns[@]}"; do
      if [[ "$candidate" =~ $pattern ]]; then
        return 0
      fi
    done
    return 1
  fi
}

function verify() {
  local mode="$1"
  local instance_file="${2:-}"

  local -a jv_args=(--assert-format --assert-content "$schema_file")
  if [ -n "$instance_file" ]; then
    jv_args+=("$instance_file")
  fi

  case "$mode" in
  quiet)
    jv "${jv_args[@]}" >/dev/null 2>/dev/null
    ;;
  simple)
    jv --output alt "${jv_args[@]}"
    ;;
  *)
    jv --output "$mode" "${jv_args[@]}"
    ;;
  esac
}

function expected_errors() {
  local instance_file="$1"
  local type
  type=$(yq -r '.properties | type' "$instance_file")
  if [[ "$type" != "object" && "$type" != "!!map" ]]; then
    return 1
  fi
  yq -r '(.properties.ext_expected_errors // []) | .[]' "$instance_file"
}

function contains() {
  local haystack="$1"
  local needle="$2"
  grep -qF "$needle" <<<"$haystack"
}

function schema() {
  echo "---- VERIFYING schema ----"
  printf "%s..." "$schema_file"
  if verify quiet; then
    echo OK
  else
      echo FAILED
      printf "\nthe schema itself is invalid.\n"
      verify detailed
  fi
}

function examples() {
  echo "---- VERIFYING examples ----"
  find examples -type f | sort | while read -r instance_file; do
    if ! [[ "$instance_file" == *.yaml ]] && ! [[ "$instance_file" == *.json ]]; then
      printf "%s...FAILED\nexample instance '%s' is EXPECTED to be a .yaml or .json file but ACTUALLY it is not.\n" "$instance_file" "$instance_file"
      return 1
    elif ! match "$instance_file"; then
      continue
    fi
    printf "%s..." "$instance_file"
    if verify quiet "$instance_file"; then
      echo OK
    else
      echo FAILED
      printf "\nexample instance '%s' is EXPECTED to pass validation but ACTUALLY it failed.\n" "$instance_file"
      verify detailed "$instance_file"
    fi
  done
}

function counterexamples() {
  echo "---- VERIFYING counterexamples ----"
  yq_installed=
  if command -v yq >/dev/null; then
    yq_installed=true
  else
    >&2 printf "WARNING: yq is not installed. Install yq for higher-fidelity counterexample testing.\n"
  fi
  find counterexamples -type f | sort | while read -r instance_file; do
    if ! match "$instance_file"; then
      continue
    fi
    printf "%s..." "$instance_file"
    declare -a expected_errors
    if verify quiet "$instance_file"; then
      echo FAILED
      printf "\ncounterexample instance '%s' is EXPECTED to fail validation but ACTUALLY it passed.\n" "$instance_file"
      exit 1
    elif [ -z "$yq_installed" ] || ! expected_errors "$instance_file" | mapfile -t expected_errors || [ ${#expected_errors} == 0 ]; then
      echo OK
    else
      declare -a actual_errors
      (verify simple "$instance_file" || true) 2>&1 | mapfile -t actual_errors
      for expected_error in "${expected_errors[@]}"; do
        for actual_error in "${actual_errors[@]}"; do
          if contains "$actual_error" "$expected_error"; then
            continue 2
          fi
        done
        echo FAILED
        printf "\ncounterexample instance '%s' is EXPECTED to trigger the following validation error but ACTUALLY it did not.\n\n" "$instance_file"
        printf "%s\n" "------------------------ MISSED EXPECTED ERROR -----------------------"
        printf "%s\n\n" "$expected_error"
        printf "%s\n" "---------------------- ACTUAL VALIDATION OUTPUT ----------------------"
        printf "%s\n" "${actual_errors[@]}"
        exit 1
      done
      echo OK
    fi
  done
}

parse_args "$@"

need_newline=

function optional_newline() {
  if [ "$need_newline" == yes ]; then
    echo
    need_newline=no
  fi
}

if [ "${modes[schema]}" == yes ]; then
  schema
  need_newline=yes
fi

if [ "${modes[examples]}" == yes ]; then
  optional_newline
  examples
  need_newline=yes
fi

if [ "${modes[counterexamples]}" == yes ]; then
  optional_newline
  counterexamples
  need_newline=yes
fi
