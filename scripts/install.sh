#!/bin/bash

set -euo pipefail

FILE_NAME="cartographer.py"
PACKAGE_NAME="jomik-cartographer"
SCAFFOLDING="from cartographer.klipper_integration import *"

function display_help() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  -k, --klipper     Set the Klipper directory (default: $HOME/klipper)"
  echo "  -e, --klippy-env  Set the Klippy virtual environment directory (default: $HOME/klippy-env)"
  echo "  --help             Show this help message and exit"
  exit 0
}

function parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
    -k | --klipper)
      klipper_dir="$2"
      shift 2
      ;;
    -e | --klippy-env)
      klippy_env="$2"
      shift 2
      ;;
    --help)
      display_help
      ;;
    *)
      echo "Unknown option: $1"
      display_help
      ;;
    esac
  done
}

function check_directory_exists() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    echo "Error: Directory '$dir' does not exist."
    exit 1
  fi
}

function check_virtualenv_exists() {
  if [ ! -d "$klippy_env" ]; then
    echo "Error: Virtual environment directory '$klippy_env' does not exist."
    exit 1
  fi
}

function install_dependencies() {
  echo "Installing or upgrading '$PACKAGE_NAME' into '$klippy_env'..."
  "$klippy_env/bin/pip" install --upgrade "$PACKAGE_NAME"
  echo "'$PACKAGE_NAME' has been successfully installed or upgraded into '$klippy_env'."
}

function create_scaffolding() {
  local file_path="$1"

  echo "$SCAFFOLDING" >"$file_path"
  echo "File '$FILE_NAME' has been created in $file_path."
}

function exclude_from_git() {
  local file_path="$1"
  local klipper_dir="$2"

  if [ -d "$klipper_dir/.git" ] && ! grep -qF "$file_path" "$klipper_dir/.git/info/exclude" >/dev/null 2>&1; then
    echo "$file_path" >>"$klipper_dir/.git/info/exclude" >/dev/null 2>&1
  fi
}

function main() {
  klipper_dir="$HOME/klipper"
  klippy_env="$HOME/klippy-env"

  parse_args "$@"

  check_directory_exists "$klipper_dir"

  check_virtualenv_exists

  install_dependencies

  extras_dir="$klipper_dir/klippy/extras"
  check_directory_exists "$extras_dir"

  file_path="$extras_dir/$FILE_NAME"

  create_scaffolding "$file_path"

  exclude_from_git "$file_path" "$klipper_dir"
}

main "$@"
