"""
Escrita atômica de arquivos de estado (JSON e flags).

Motivação (spec 003 / issue DATA-02): motor e UI trocam estado por arquivos sem
lock. A escrita direta (open 'w' + json.dump) deixa uma janela em que o arquivo
fica pela metade; se a UI ler nesse instante, pega conteúdo truncado.

Solução: escreve num arquivo temporário no MESMO diretório do destino e faz
os.replace() — um rename atômico (POSIX e Windows) no mesmo volume. Qualquer
leitor observa sempre a versão antiga OU a nova completa, nunca um estado parcial.

Módulo intencionalmente SEM dependências externas, para ser testável isolado.
"""

import json
import os
import tempfile


def atomic_write_text(path, text, encoding="utf-8"):
    """Escreve `text` em `path` de forma atômica (write-temp + os.replace)."""
    target_dir = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, prefix=".tmp_", suffix=".swap")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as tmp_file:
            tmp_file.write(text)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Nunca deixa o temporário órfão nem corrompe o destino pré-existente.
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path, data, encoding="utf-8", **json_kwargs):
    """Serializa `data` e grava de forma atômica. Repassa kwargs para json.dumps."""
    atomic_write_text(path, json.dumps(data, **json_kwargs), encoding=encoding)
