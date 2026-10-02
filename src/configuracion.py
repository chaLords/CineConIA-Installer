"""Versioned policy and per-installation state; no global Python dependencies."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def cargar(nombre):
    with (ROOT / 'config' / (nombre + '.json')).open(encoding='utf-8-sig') as f:
        return json.load(f)


def nodos():
    data = cargar('recommended_nodes')
    for key, node in data.items():
        # null follows the default branch (our own Cine con IA nodes).
        if node['version'] is not None and not re.fullmatch(r'[0-9a-f]{40}', node['version']):
            raise ValueError(f'NODE_REVISION_INVALID: {key}')
        if not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+\.git', node['repo']):
            raise ValueError(f'NODE_SOURCE_INVALID: {key}')
        if any(not re.fullmatch(r'[\w.-]+', name) or name in ('.', '..') for name in node['carpetas']):
            raise ValueError(f'NODE_PATH_INVALID: {key}')
    return data


def recomendado():
    return os.environ.get('CINECONIA_MODE') == 'recommended'


def perfil_vram(gb):
    if gb is None:
        return None
    # Hardware reports a slightly smaller usable capacity than the label.
    return next(p for p in reversed(cargar('hardware_profiles')) if float(gb) + 0.5 >= p['min_vram_gb'])


def leer_estado(destino):
    try:
        return json.loads((Path(destino)/'_cineconia/install-state.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def guardar_estado(destino, **cambios):
    data = leer_estado(destino)
    data.update(cambios, updated_utc=datetime.now(timezone.utc).isoformat())
    directory = Path(destino)/'_cineconia'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/'install-state.json'
    fd, temporary = tempfile.mkstemp(dir=directory, prefix='state-', suffix='.part')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)
    return path


def validar_entorno(destino, inf):
    """Only a new pinned portable must match the archive's runtime contract."""
    key = os.environ.get('CIA_PROFILE') or leer_estado(destino).get('profile')
    if not key or os.environ.get('CIA_OPERATION') == 'maintenance':
        return
    policy = cargar('compatibility_matrix')['profiles'][key]
    expected = policy.get('python_minor')
    if expected and not inf['python'].startswith(expected + '.'):
        raise RuntimeError(f"PYTHON_MATRIX_MISMATCH: {inf['python']} / {expected}")
    expected = policy.get('cuda_runtime')
    if expected and inf.get('cuda') != expected:
        raise RuntimeError(f"CUDA_MATRIX_MISMATCH: {inf.get('cuda')} / {expected}")
    expected = policy.get('torch_version')
    if expected and inf['torch'].get('torch') != expected:
        raise RuntimeError(f"TORCH_MATRIX_MISMATCH: {inf['torch'].get('torch')} / {expected}")
    if inf.get('gpu_inutilizable') or not inf['torch'].get('torch'):
        raise RuntimeError('GPU_RUNTIME_UNAVAILABLE')


def preparar_git(destino):
    """MinGit lives inside this portable and changes PATH only for this process."""
    import preflight
    import pasos
    found = preflight.git_exe()
    if found:
        os.environ['PATH'] = str(Path(found).parent) + os.pathsep + os.environ.get('PATH', '')
        return found
    spec = cargar('compatibility_matrix')['tools']['mingit']
    directory = Path(destino)/'_cineconia/tools'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory/'git'
    executable = target/'cmd/git.exe'
    if executable.is_file():
        r = subprocess.run([str(executable), '--version'], capture_output=True, timeout=30)
        if r.returncode == 0:
            os.environ['PATH'] = str(executable.parent) + os.pathsep + os.environ.get('PATH', '')
            return str(executable)
    archive = directory/'mingit.zip'
    partial = archive.with_suffix('.part')
    # Keep downloads visible using the same progress renderer as the bootstrap.
    ok, detail = pasos.correr(['curl.exe', '--fail', '--location', '--retry', '3',
                              '--output', str(partial), spec['url']], 'MinGit', timeout=600)
    if not ok:
        raise RuntimeError('GIT_DOWNLOAD_FAILED: ' + '; '.join(detail))
    # Chunked: hashlib.file_digest needs Python 3.11 and older portables exist.
    digest = hashlib.sha256()
    with partial.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != spec['sha256']:
        raise RuntimeError('GIT_HASH_MISMATCH')
    os.replace(partial, archive)
    stage = Path(tempfile.mkdtemp(prefix='git-', dir=directory))
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            output = (stage/member.filename).resolve()
            if not output.is_relative_to(stage.resolve()):
                raise RuntimeError('GIT_ARCHIVE_UNSAFE')
        z.extractall(stage)
    if not (stage/'cmd/git.exe').is_file():
        raise RuntimeError('GIT_ARCHIVE_INVALID')
    if target.exists():
        target.rename(directory/('git-backup-' + datetime.now().strftime('%Y%m%d%H%M%S%f')))
    stage.rename(target)
    os.environ['PATH'] = str(executable.parent) + os.pathsep + os.environ.get('PATH', '')
    if subprocess.run([str(executable), '--version'], capture_output=True, timeout=30).returncode:
        raise RuntimeError('GIT_START_FAILED')
    return str(executable)


def autorizar(destino, input_fn=input):
    """Direct invocation cannot silently configure an existing installation."""
    normalize = lambda p: os.path.normcase(os.path.realpath(p))
    supplied = os.environ.get('CIA_AUTHORIZED_DESTINATION')
    if supplied and normalize(supplied) == normalize(destino):
        return True
    import i18n
    print(i18n.t('setup.maintenance_confirm') + '\n' + destino)
    return input_fn(i18n.t('setup.confirm') + ': ').strip() == i18n.t('setup.confirm_word')


def mensaje_error(error):
    """Translated text for coded errors (CODE or CODE: detail); the code stays visible."""
    import i18n
    texto = str(error)
    m = re.fullmatch(r'([A-Z0-9_]+)(?::\s*(.*))?', texto, flags=re.DOTALL)
    if m:
        clave = 'setup.error.' + m.group(1)
        traducido = i18n.t(clave)
        if traducido != clave:
            return (traducido.replace('{detail}', m.group(2) or '')
                    + f"\n      ({i18n.t('setup.error_code')} {texto})")
    return texto
