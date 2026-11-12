"""Модуль резервного копирования базы данных и конфигурации."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


# Пути по умолчанию
DEFAULT_DB_PATH = Path('instance/book_catalog.db')
DEFAULT_BACKUP_DIR = Path('data/backups')


def _sha256(filepath: Path) -> str:
    """Вычисляет SHA-256 хеш файла."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def create_backup(db_path: Path, backup_dir: Path) -> Path:
    """
    Создаёт резервную копию БД с манифестом SHA-256.
    
    Алгоритм:
    1. Вычислить SHA-256 для БД.
    2. Сформировать манифест.
    3. Записать во временный ZIP-файл.
    4. Атомарно переименовать в целевое имя.
    """
    if not db_path.exists():
        raise FileNotFoundError(f'База данных не найдена: {db_path}')

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{timestamp}.zip'
    backup_path = backup_dir / backup_name

    # Формирование манифеста
    db_hash = _sha256(db_path)
    manifest = {db_path.name: db_hash}

    # Запись во временный файл (атомарность)
    with tempfile.NamedTemporaryFile(suffix='.zip', dir=backup_dir, delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))
            zf.write(db_path, db_path.name)
        os.replace(tmp_path, backup_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return backup_path


def list_backups(backup_dir: Path) -> list:
    """Возвращает список резервных копий, отсортированный по дате."""
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob('backup_*.zip'))


def restore_backup(archive_path: Path, db_path: Path) -> Path:
    """
    Восстанавливает БД из резервной копии.
    
    Проверки:
    - наличие манифеста
    - совпадение SHA-256
    - безопасность имён файлов (защита от path traversal)
    
    При успехе: прежняя БД сохраняется как .bak (страховая копия).
    При ошибке: откат к прежнему состоянию.
    """
    if not archive_path.exists():
        raise FileNotFoundError(f'Архив не найден: {archive_path}')

    # Проверка архива перед распаковкой
    with zipfile.ZipFile(archive_path, 'r') as zf:
        names = zf.namelist()

        if 'manifest.json' not in names:
            raise ValueError('В архиве отсутствует манифест')

        # Защита от path traversal
        for name in names:
            if name.startswith('/') or '..' in name:
                raise ValueError(f'Небезопасное имя файла в архиве: {name}')

    # Распаковка во временный каталог
    restore_dir = Path(tempfile.mkdtemp(prefix='restore_'))

    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(restore_dir)

        # Проверка манифеста и хешей
        manifest_path = restore_dir / 'manifest.json'
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        for name, expected_hash in manifest.items():
            file_path = restore_dir / name
            if not file_path.exists():
                raise ValueError(f'Файл из манифеста отсутствует: {name}')
            actual_hash = _sha256(file_path)
            if actual_hash != expected_hash:
                raise ValueError(f'Несовпадение хеша для {name}')

        # Страховая копия текущей БД
        if db_path.exists():
            backup_old = db_path.parent / f'{db_path.name}.bak.{int(datetime.now().timestamp())}'
            shutil.copy2(db_path, backup_old)
            print(f'Страховая копия сохранена: {backup_old}')

        # Восстановление
        src_name = list(manifest.keys())[0]
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(restore_dir / src_name, db_path)
        print(f'База данных восстановлена: {db_path}')

        return archive_path

    except Exception:
        raise
    finally:
        shutil.rmtree(restore_dir, ignore_errors=True)


def main():
    """CLI-интерфейс для резервного копирования."""
    parser = argparse.ArgumentParser(
        description='Резервное копирование базы данных'
    )
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('create', help='Создать резервную копию')
    subparsers.add_parser('list', help='Список резервных копий')

    restore_parser = subparsers.add_parser('restore', help='Восстановить из копии')
    restore_parser.add_argument('--archive', help='Путь к конкретному архиву')

    args = parser.parse_args()

    if args.command == 'create':
        try:
            path = create_backup(DEFAULT_DB_PATH, DEFAULT_BACKUP_DIR)
            print(f'Резервная копия создана: {path}')
        except (FileNotFoundError, OSError) as e:
            print(f'Ошибка: {e}', file=sys.stderr)
            sys.exit(1)

    elif args.command == 'list':
        backups = list_backups(DEFAULT_BACKUP_DIR)
        if not backups:
            print('Резервные копии отсутствуют')
        else:
            print('Список резервных копий:')
            for i, p in enumerate(backups, start=1):
                size_kb = p.stat().st_size / 1024
                print(f'  {i}. {p.name} ({size_kb:.1f} КБ)')

    elif args.command == 'restore':
        archive = Path(args.archive) if args.archive else None
        if archive is None:
            backups = list_backups(DEFAULT_BACKUP_DIR)
            if backups:
                archive = backups[-1]
        try:
            path = restore_backup(archive, DEFAULT_DB_PATH)
            print(f'Восстановление выполнено из: {path}')
        except (FileNotFoundError, ValueError, OSError) as e:
            print(f'Ошибка восстановления: {e}', file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()