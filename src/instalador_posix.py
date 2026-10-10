"""Instalador base de ComfyUI para Linux NVIDIA y macOS Apple Silicon.

No sustituye el instalador Windows: usa el metodo oficial de ComfyUI para
entornos no portables (venv + PyTorch del backend + requirements.txt). La
configuracion de nodos de terceros se incorporara cuando se valide en hardware
real de cada plataforma.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


class InstallerError(RuntimeError):
    pass


def _language():
    value = os.environ.get("CINECONIA_LANG") or os.environ.get("LANG", "")
    return "es" if value.lower().startswith("es") else "en"


TEXT = {
    "es": {
        "title": "Cine con IA · instalación multiplataforma (beta)",
        "unsupported": "Este instalador beta solo admite Linux x86_64 con NVIDIA y macOS Apple Silicon.",
        "missing": "Falta el requisito: {name}",
        "exists": "La carpeta de destino ya contiene archivos: {path}",
        "plan": "Se instalará ComfyUI {revision} con {profile} en {destination}",
        "confirm": "Escribe INSTALAR para continuar (Enter cancela): ",
        "cancelled": "Cancelado. No se modificó nada.",
        "models": "Biblioteca de modelos externa (Enter acepta {path}; - usa la carpeta interna): ",
        "ready": "Listo. Abre ComfyUI con: {launcher}",
        "dry_run": "Simulación terminada. No se modificó nada.",
        "step": "→ {text}",
        "venv": "Creando entorno aislado de Python",
        "clone": "Descargando ComfyUI comprobado",
        "torch": "Instalando PyTorch para el backend detectado",
        "requirements": "Instalando dependencias de ComfyUI",
        "models_ready": "Biblioteca de modelos enlazada: {path}",
    },
    "en": {
        "title": "Cine con IA · cross-platform installation (beta)",
        "unsupported": "This beta installer supports Linux x86_64 with NVIDIA and Apple Silicon macOS only.",
        "missing": "Missing requirement: {name}",
        "exists": "The destination folder already contains files: {path}",
        "plan": "ComfyUI {revision} with {profile} will be installed in {destination}",
        "confirm": "Type INSTALL to continue (Enter cancels): ",
        "cancelled": "Cancelled. Nothing was changed.",
        "models": "External model library (Enter accepts {path}; - uses the internal folder): ",
        "ready": "Ready. Start ComfyUI with: {launcher}",
        "dry_run": "Dry run complete. Nothing was changed.",
        "step": "→ {text}",
        "venv": "Creating an isolated Python environment",
        "clone": "Downloading the pinned ComfyUI revision",
        "torch": "Installing PyTorch for the detected backend",
        "requirements": "Installing ComfyUI dependencies",
        "models_ready": "Model library linked: {path}",
    },
}


def text(key, **values):
    return TEXT[_language()][key].format(**values)


def load_config():
    with (ROOT / "config" / "platform_profiles.json").open(encoding="utf-8") as source:
        return json.load(source)


def platform_key(system=None, machine=None):
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    return system, machine


def select_profile(system=None, machine=None, config=None):
    system, machine = platform_key(system, machine)
    config = config or load_config()
    for name, profile in config["profiles"].items():
        if profile["platform"] == system and machine in profile["architectures"]:
            return name, profile
    raise InstallerError(text("unsupported"))


def free_destination(base):
    base = Path(base).expanduser().resolve()
    for number in range(1, 100):
        candidate = base / ("ComfyUI" if number == 1 else f"ComfyUI-{number}")
        if not candidate.exists():
            return candidate
    raise InstallerError("No free ComfyUI destination was found.")


def validate_destination(destination):
    destination = Path(destination).expanduser().resolve()
    if destination == Path(destination.anchor):
        raise InstallerError(text("exists", path=destination))
    if destination.exists() and any(destination.iterdir()):
        raise InstallerError(text("exists", path=destination))
    return destination


def run(command, label):
    print(text("step", text=label))
    subprocess.run(command, check=True)


def launcher_text():
    return '''#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
PORT="${CINECONIA_PORT:-8188}"
exec "$ROOT/.venv/bin/python" "$ROOT/ComfyUI/main.py" --port "$PORT" "$@"
'''


def write_launcher(destination, system):
    name = "Abrir-ComfyUI.command" if system == "darwin" else "Iniciar-ComfyUI.sh"
    launcher = destination / name
    launcher.write_text(launcher_text(), encoding="utf-8", newline="\n")
    launcher.chmod(launcher.stat().st_mode | 0o111)
    return launcher


def configure_models(destination, models):
    if models is None:
        return None
    import modelos_enlace
    models = modelos_enlace.validar_biblioteca(str(models), str(destination / "ComfyUI"))
    modelos_enlace.crear_estructura(models)
    modelos_enlace.registrar_biblioteca(models)
    modelos_enlace.actualizar_yaml(str(destination / "ComfyUI"), models,
                                   modelos_enlace.mapa_categorias(models))
    return models


def install(destination, profile, config, models=None, dry_run=False):
    destination = validate_destination(destination)
    print(text("plan", revision=config["comfyui"]["revision"],
               profile=profile["label"], destination=destination))
    if dry_run:
        print(text("dry_run"))
        return None
    for command in profile["required_commands"]:
        if not shutil.which(command):
            raise InstallerError(text("missing", name=command))
    destination.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    run([python, "-m", "venv", str(destination / ".venv")], text("venv"))
    pip = destination / ".venv" / "bin" / "pip"
    env_python = destination / ".venv" / "bin" / "python"
    run([str(pip), "install", "--upgrade", "pip"], "pip")
    run(["git", "clone", "--depth", "1", "--branch", config["comfyui"]["revision"],
         config["comfyui"]["repository"], str(destination / "ComfyUI")], text("clone"))
    run([str(pip), "install", *profile["torch_arguments"]], text("torch"))
    run([str(pip), "install", "-r", str(destination / "ComfyUI" / "requirements.txt")], text("requirements"))
    library = configure_models(destination, models)
    if library:
        print(text("models_ready", path=library))
    return write_launcher(destination, profile["platform"])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Cine con IA cross-platform installer")
    parser.add_argument("--destination", help="Installation folder")
    parser.add_argument("--models-library", help="External model library; - uses ComfyUI/models")
    parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Validate the plan without writing")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print("\n   " + text("title"))
    config = load_config()
    try:
        _, profile = select_profile(config=config)
        destination = validate_destination(args.destination or free_destination(Path.home()))
        print(text("plan", revision=config["comfyui"]["revision"],
                   profile=profile["label"], destination=destination))
        if not args.yes and not args.dry_run:
            word = "INSTALAR" if _language() == "es" else "INSTALL"
            if input(text("confirm")).strip() != word:
                print(text("cancelled"))
                return 2
        default_models = Path.home() / "ComfyUI-models"
        if args.models_library is None and not args.dry_run:
            answer = input(text("models", path=default_models)).strip()
            models = None if answer == "-" else Path(answer).expanduser() if answer else default_models
        else:
            models = None if args.models_library == "-" else Path(args.models_library).expanduser() if args.models_library else None
        launcher = install(destination, profile, config, models=models, dry_run=args.dry_run)
        if launcher:
            print(text("ready", launcher=launcher))
        return 0
    except (InstallerError, OSError, subprocess.CalledProcessError, ValueError) as error:
        print("\n   [X] " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
