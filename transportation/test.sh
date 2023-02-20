#!/bin/env bash

set -eo pipefail
shopt -s lastpipe extglob

schema_file=schema/schema.yaml

function verify() {
  local mode="$1"
  local instance_file="${2:-}"

  local -a jv_args=("$schema_file")
  if [ -n "$instance_file" ]; then
    jv_args+=("$instance_file")
  fi

  case "$mode" in
  quiet)
    jv "${jv_args[@]}" 2>/dev/null
    ;;
  *)
    jv --output "$mode" "${jv_args[@]}"
    ;;
  esac
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

# TODO: A major shortcoming of the counterexamples is that there is no
#       way to specify HOW they fail. Consequently if a counterexample
#       becomes totally obsolete because we ripped out that part of the
#       schema, we don't get any notice that the counterexample is now
#       irrelevant. Pointless cruft will build up over time until this
#       is fixed.

echo "---- VERIFYING counterexamples ----"
find counterexamples -type f | sort | while read -r instance_file; do
  printf "%s..." "$instance_file"
  if ! verify quiet "$instance_file"; then
    echo OK
  else
    echo FAILED
    printf "\ncounterexample instance '%s' is EXPECTED to fail validation but ACTUALLY it passed.\n" "$instance_file"
    exit 1
  fi
done
