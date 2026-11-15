import argparse
import json
from pathlib import Path
import sys
from .core import create_manifest, outside_root, verify, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description='Cria e compara inventários de arquivos com SHA-256.')
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('criar')
    create.add_argument('pasta', type=Path)
    create.add_argument('--saida', type=Path, required=True)
    check = commands.add_parser('verificar')
    check.add_argument('pasta', type=Path)
    check.add_argument('--inventario', type=Path, required=True)
    check.add_argument('--saida', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'criar':
            target = outside_root(args.saida, args.pasta)
            if target.exists():
                raise ValueError('O inventário já existe. Escolha outro nome para preservar a referência.')
            result = create_manifest(args.pasta)
            write_json(target, result)
            print(f'Inventário criado: {target} ({len(result["arquivos"])} arquivos).')
            return 0
        if args.saida:
            target = outside_root(args.saida, args.pasta)
            if target == args.inventario.resolve():
                raise ValueError('O relatório não pode sobrescrever o inventário.')
        result = verify(args.pasta, json.loads(args.inventario.read_text(encoding='utf-8')))
        if args.saida:
            write_json(target, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return {'integro': 0, 'alterado': 1, 'incompleto': 2}[result['resultado']]
    except (OSError, ValueError, UnicodeError) as error:
        print(f'Erro: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
