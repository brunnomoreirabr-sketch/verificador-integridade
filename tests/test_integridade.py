from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from integridade.core import create_manifest, verify, outside_root, validate_manifest
from integridade.cli import main


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / 'files'
        self.root.mkdir()
        (self.root / 'a.txt').write_text('abc')
        (self.root / 'b.txt').write_text('segundo')

    def tearDown(self):
        self.temp.cleanup()

    def test_same_size_change_addition_and_removal(self):
        manifest = create_manifest(self.root)
        (self.root / 'a.txt').write_text('xyz')
        (self.root / 'b.txt').unlink()
        (self.root / 'c.txt').write_text('novo')
        result = verify(self.root, manifest)
        self.assertEqual(result['alterados'], ['a.txt'])
        self.assertEqual(result['removidos'], ['b.txt'])
        self.assertEqual(result['adicionados'], ['c.txt'])
        self.assertEqual(result['resultado'], 'alterado')

    def test_unchanged_files(self):
        result = verify(self.root, create_manifest(self.root))
        self.assertEqual(result['resultado'], 'integro')
        self.assertEqual(len(result['sem_alteracao']), 2)

    def test_unreadable_file_is_not_reported_as_removed(self):
        manifest = create_manifest(self.root)
        from integridade.core import hash_file
        def read(path):
            if path.name == 'a.txt':
                raise PermissionError('sem acesso')
            return hash_file(path)
        with patch('integridade.core.hash_file', side_effect=read):
            result = verify(self.root, manifest)
            self.assertEqual(result['resultado'], 'incompleto')
            self.assertEqual(result['nao_verificados'], ['a.txt'])
            self.assertEqual(result['removidos'], [])
            with self.assertRaises(ValueError):
                create_manifest(self.root)

    def test_symlinks_are_not_followed(self):
        try:
            (self.root / 'link').symlink_to(self.root / 'a.txt')
        except OSError:
            self.skipTest('Sistema sem criação de links simbólicos')
        manifest = create_manifest(self.root)
        self.assertNotIn('link', manifest['arquivos'])
        self.assertIn('link', manifest['ignorados'])

    def test_manifest_and_output_paths_validated(self):
        manifest = create_manifest(self.root)
        manifest['arquivos']['../outside'] = manifest['arquivos']['a.txt']
        with self.assertRaises(ValueError):
            validate_manifest(manifest)
        with self.assertRaises(ValueError):
            outside_root(self.root / 'inventory.json', self.root)

    def test_cli_round_trip_and_exit_codes(self):
        inventory = self.base / 'inventory.json'
        with patch('sys.stdout'), patch('sys.stderr'):
            self.assertEqual(main(['criar', str(self.root), '--saida', str(inventory)]), 0)
            self.assertEqual(main(['criar', str(self.root), '--saida', str(inventory)]), 2)
            self.assertEqual(main(['verificar', str(self.root), '--inventario', str(inventory)]), 0)
            (self.root / 'a.txt').write_text('mudou')
            self.assertEqual(main(['verificar', str(self.root), '--inventario', str(inventory)]), 1)
            self.assertEqual(main(['verificar', str(self.root), '--inventario', str(inventory), '--saida', str(inventory)]), 2)
