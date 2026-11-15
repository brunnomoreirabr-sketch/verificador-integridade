from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile


def hash_file(path):
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, 'rb') as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise OSError('não é um arquivo regular')
        digest = hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
        after = os.fstat(source.fileno())
        current = path.lstat()
        if ((before.st_size, before.st_mtime_ns, before.st_ino) !=
                (after.st_size, after.st_mtime_ns, after.st_ino) or
                (after.st_ino, after.st_mtime_ns) != (current.st_ino, current.st_mtime_ns) or
                not stat.S_ISREG(current.st_mode)):
            raise OSError('arquivo mudou durante a leitura; repita a verificação')
        return {'sha256': digest.hexdigest(), 'bytes': after.st_size}


def scan(directory):
    root = Path(directory).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('O caminho precisa ser uma pasta.')
    files, errors, ignored = {}, {}, []

    def unreadable(error):
        try:
            key = Path(error.filename).relative_to(root).as_posix()
        except (ValueError, TypeError):
            key = '.'
        errors[key] = str(error)

    for base, directories, names in os.walk(root, topdown=True, followlinks=False, onerror=unreadable):
        for name in list(directories):
            path = Path(base) / name
            if path.is_symlink():
                ignored.append(path.relative_to(root).as_posix())
                directories.remove(name)
        for name in sorted(names):
            path = Path(base) / name
            key = path.relative_to(root).as_posix()
            if path.is_symlink():
                ignored.append(key)
                continue
            try:
                if not stat.S_ISREG(path.lstat().st_mode):
                    ignored.append(key)
                    continue
                files[key] = hash_file(path)
            except OSError as error:
                errors[key] = str(error)
    return files, errors, sorted(ignored)


def create_manifest(directory):
    files, errors, ignored = scan(directory)
    if errors:
        raise ValueError('Inventário não criado: arquivos ou pastas não puderam ser lidos: ' + ', '.join(sorted(errors)))
    return {'versao': 1, 'algoritmo': 'sha256', 'criado_em': datetime.now(timezone.utc).isoformat(),
            'arquivos': files, 'ignorados': ignored}


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get('versao') != 1 or manifest.get('algoritmo') != 'sha256':
        raise ValueError('Versão ou algoritmo do inventário não suportado.')
    files = manifest.get('arquivos')
    if not isinstance(files, dict):
        raise ValueError('O inventário precisa conter o objeto arquivos.')
    for name, info in files.items():
        path = PurePosixPath(name)
        if (not name or name == '.' or path.is_absolute() or '..' in path.parts or
                '\\' in name or not isinstance(info, dict) or
                not isinstance(info.get('sha256'), str) or not re.fullmatch(r'[a-f0-9]{64}', info['sha256']) or
                type(info.get('bytes')) is not int or info['bytes'] < 0):
            raise ValueError(f'Entrada inválida no inventário: {name!r}')
    return files


def verify(directory, manifest):
    expected = validate_manifest(manifest)
    actual, errors, ignored = scan(directory)

    def inaccessible(name):
        return any(prefix == '.' or name == prefix or name.startswith(prefix + '/') for prefix in errors)

    unknown = {name for name in expected if inaccessible(name)}
    removed = set(expected) - set(actual) - unknown
    shared = set(expected) & set(actual)
    changed = {name for name in shared if expected[name] != actual[name]}
    report = {'adicionados': sorted(set(actual) - set(expected)), 'alterados': sorted(changed),
              'removidos': sorted(removed), 'sem_alteracao': sorted(shared - changed),
              'nao_verificados': sorted(unknown), 'erros': errors, 'ignorados': ignored}
    report['resultado'] = 'incompleto' if errors else ('alterado' if any(report[k] for k in ('adicionados', 'alterados', 'removidos')) else 'integro')
    return report


def outside_root(path, root):
    path = Path(path).resolve()
    if path.is_relative_to(Path(root).resolve()):
        raise ValueError('Salve o inventário e o relatório fora da pasta verificada.')
    return path


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
