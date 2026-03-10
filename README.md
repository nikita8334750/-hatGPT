# Супер сжатие файлов

Утилита `super_compress.py` делает сильное сжатие файлов/папок в tar-архив.

По умолчанию используется режим `auto`:
1. `zstd` (если установлен),
2. иначе `xz`,
3. иначе `gzip`.

## Запуск

```bash
./super_compress.py <файл_или_папка> [другие_пути...] -o backup
```

Скрипт сам добавит расширение:
- `.tar.zst` для `zstd`
- `.tar.xz` для `xz`
- `.tar.gz` для `gzip`

## Параметры

- `inputs` — один или несколько файлов/папок.
- `-o, --output` — путь для выходного файла.
- `-m, --method` — `auto | zstd | xz | gzip`.
- `-l, --level` — уровень сжатия:
  - `1..22` для `zstd`
  - `0..9` для `xz/gzip`

## Примеры

```bash
./super_compress.py ./project -o project_backup
./super_compress.py logs app.db -o archive -m zstd -l 22
./super_compress.py ./data -o data_pack -m xz -l 9
```

## Требования

- `python3`
- `tar`
- Для метода `zstd`: бинарник `zstd`
- Для метода `xz`: бинарник `xz`
- Для метода `gzip`: бинарник `gzip`
