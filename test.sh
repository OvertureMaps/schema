#!/usr/bin/env bash

set -eo pipefail
shopt -s lastpipe extglob

schema_file=schema/schema.yaml

function verify() {
  local mode="$1"
  local instance_file="${2:-}"

  local -a jv_args=(-assertformat -assertcontent "$schema_file")
  if [ -n "$instance_file" ]; then
    jv_args+=("$instance_file")
  fi

  case "$mode" in
  quiet)
    jv "${jv_args[@]}" 2>/dev/null
    ;;
  simple)
    jv "${jv_args[@]}"
    ;;
  *)
    jv -output "$mode" "${jv_args[@]}"
    ;;
  esac
}

function expected_errors() {
  local instance_file="$1"
  local type
  type=$(yq -r '.properties | type' "$instance_file")
  if [ "$type" != "object" ]; then
    return 1
  fi
  yq -r '(.properties.extExpectedErrors // []) | .[]' "$instance_file"
}

echo "---- VERIFYING schema ----"
printf "%s..." "$schema_file"
if verify quiet; then
  echo OK
else
    echo FAILED
    printf "\nthe schema itself is invalid.\n"
    verify detailed
fi

echo

echo "---- VERIFYING examples ----"
find examples -type f | sort | while read -r instance_file; do
  printf "%s..." "$instance_file"
  if verify quiet "$instance_file"; then
    echo OK
  else
    echo FAILED
    printf "\nexample instance '%s' is EXPECTED to pass validation but ACTUALLY it failed.\n" "$instance_file"
    verify detailed "$instance_file"
  fi
done

echo

echo "---- VERIFYING counterexamples ----"
yq_installed=
if command -v yq >/dev/null; then
  yq_installed=true
else
  >&2 printf "WARNING: yq is not installed. Install yq for higher-fidelity counterexample testing."
fi
find counterexamples -type f | sort | while read -r instance_file; do
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
        if [[ "$actual_error" == *"$expected_error"* ]]; then
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
  fi
done
