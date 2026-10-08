# Comando de diagnóstico READ-ONLY no Coolify

ID: 2bbf6b59c0cb0b5b. Placement: 14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e.

Abra o terminal da aplicação backend e execute a partir da mesma pasta em que funcionou `python scripts/reset_test_user_learning.py ...`. Copie TODO o bloco abaixo.

O bloco contém a cópia comprimida de `backend/scripts/audit_placement_result.py`, verificada por SHA-256. Executa o diagnóstico em memória, usando a configuração existente da API; não exige que o arquivo esteja no container, não grava o script, não faz deploy nem instala dependências. Só exporta JSON para stdout. PostgreSQL usa transação REPEATABLE READ com READ ONLY verificado e timeout de 15 segundos por statement; encerra com rollback. Nenhum seed, migration, complete, next-item ou chamada de IA/TTS é executado.

Se o terminal já tiver o arquivo (por cópia manual autorizada), o comando curto equivalente é:

```bash
python scripts/audit_placement_result.py --test-id 14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e
```

## Comando que funciona sem publicar o arquivo

```bash
python - --test-id 14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e <<'PY'
import base64, hashlib, zlib
from pathlib import Path
payload = (
    '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'
)
source = zlib.decompress(base64.b64decode(payload))
assert hashlib.sha256(source).hexdigest() == '3128b0470169a29da3ea3af623c637fac5909c92b990eeeed348112b81e40286', 'Diagnostic integrity check failed'
assert Path('app/core/database.py').is_file(), 'Execute na pasta backend, a mesma do reset'
filename = str(Path('scripts/audit_placement_result.py').resolve())
exec(compile(source, filename, 'exec'), {'__name__': '__main__', '__file__': filename})
PY
```

Retorne o JSON completo. Ele contém redação/respostas e conteúdo pedagógico desse teste, mas não imprime DATABASE_URL, credenciais, usuários de outras contas ou tokens. Se a saída for truncada, redirecione o stdout para um arquivo temporário do container e copie seu conteúdo; isso só grava o relatório local, sem alterar o banco.

A presença de áudio no item não comprova que ele foi reproduzido. Campos atuais do item/banco não são snapshots históricos. O diagnóstico sinaliza discrepâncias de skill/CEFR e alterações de item posteriores à resposta, para não inventar causalidade.
