#!/bin/bash

set -euo pipefail

FILE_NAME="cartographer.py"
PACKAGE_NAME="jomik-cartographer"

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

function uninstall_dependencies() {
  echo "Uninstalling '$PACKAGE_NAME' from '$klippy_env'..."
  "$klippy_env/bin/pip" uninstall -y "$PACKAGE_NAME"
  echo "'$PACKAGE_NAME' has been successfully uninstalled from '$klippy_env'."
}

function remove_scaffolding() {
  local file_path="$1"
  if [ -f "$file_path" ]; then
    rm "$file_path"
    echo "File '$FILE_NAME' has been removed from $file_path."
  else
    echo "File '$FILE_NAME' does not exist in $file_path."
  fi
}

function remove_from_git_exclude() {
  local file_path="$1"
  local klipper_dir="$2"
  if [ -d "$klipper_dir/.git" ] && grep -qF "$file_path" "$klipper_dir/.git/info/exclude"; then
    sed -i "/$file_path/d" "$klipper_dir/.git/info/exclude"
    echo "File '$FILE_NAME' has been removed from .git/info/exclude."
  else
    echo "File '$FILE_NAME' is not listed in .git/info/exclude."
  fi
}

function main() {
  klipper_dir="$HOME/klipper"
  klippy_env="$HOME/klippy-env"

  parse_args "$@"

  check_directory_exists "$klipper_dir"

  check_virtualenv_exists

  uninstall_dependencies

  extras_dir="$klipper_dir/klippy/extras"
  check_directory_exists "$extras_dir"

  file_path="$extras_dir/$FILE_NAME"

  remove_scaffolding "$file_path"

  remove_from_git_exclude "$file_path" "$klipper_dir"

  echo "klipper_dir is set to: $klipper_dir"
  echo "klippy_env is set to: $klippy_env"
}

main "$@"
