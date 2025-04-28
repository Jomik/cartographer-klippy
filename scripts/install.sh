#!/bin/bash

set -euo pipefail

FILE_NAME="cartographer.py"
PACKAGE_NAME="cartographer3d-plugin"
SCAFFOLDING="from cartographer.klipper.extra import *"

function display_help() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  -k, --klipper       Set the Klipper directory (default: \$HOME/klipper)"
  echo "  -e, --klippy-env    Set the Klippy virtual environment directory (default: \$HOME/klippy-env)"
  echo "  --uninstall         Uninstall the package and remove the scaffolding"
  echo "  --help              Show this help message and exit"
  exit 0
}

function parse_args() {
  uninstall=false
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
    --uninstall)
      uninstall=true
      shift
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

function uninstall_dependencies() {
  echo "Uninstalling '$PACKAGE_NAME' from '$klippy_env'..."
  "$klippy_env/bin/pip" uninstall -y "$PACKAGE_NAME"
  echo "'$PACKAGE_NAME' has been uninstalled from '$klippy_env'."
}

function create_scaffolding() {
  local file_path="$1"
  if [ -L "$file_path" ]; then
    echo "Error: '$file_path' is a symlink - scaffolding cannot be created."
    exit 1
  fi
  echo "$SCAFFOLDING" >"$file_path"
  echo "File '$FILE_NAME' has been created in $file_path."
}

function remove_scaffolding() {
  local file_path="$1"
  if [ -f "$file_path" ]; then
    rm "$file_path"
    echo "Removed file '$file_path'."
  fi
}

function exclude_from_git() {
  local file_path="$1"
  local klipper_dir="$2"
  local exclude_file="$klipper_dir/.git/info/exclude"

  if [ -d "$klipper_dir/.git" ] && ! grep -qF "$file_path" "$exclude_file" >/dev/null 2>&1; then
    echo "$file_path" >>"$exclude_file"
  fi
}

function remove_from_git_exclude() {
  local file_path="$1"
  local klipper_dir="$2"
  local exclude_file="$klipper_dir/.git/info/exclude"

  if [ -f "$exclude_file" ]; then
    sed -i "\|$file_path|d" "$exclude_file"
    echo "Removed '$file_path' from git exclude."
  fi
}

function main() {
  klipper_dir="$HOME/klipper"
  klippy_env="$HOME/klippy-env"

  parse_args "$@"

  check_directory_exists "$klipper_dir"
  check_virtualenv_exists

  extras_dir="$klipper_dir/klippy/extras"
  check_directory_exists "$extras_dir"
  file_path="$extras_dir/$FILE_NAME"

  if [ "$uninstall" = true ]; then
    uninstall_dependencies
    remove_scaffolding "$file_path"
    remove_from_git_exclude "$file_path" "$klipper_dir"
  else
    install_dependencies
    create_scaffolding "$file_path"
    exclude_from_git "$file_path" "$klipper_dir"
  fi
}

main "$@"
