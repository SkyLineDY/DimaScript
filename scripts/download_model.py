"""Download the pinned model into the cache layout used by the worker."""
from pathlib import Path
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent.parent
REVISION = '536b0662742c02347bc0e980a01041f333bce120'
snapshot = Path(snapshot_download(
    repo_id='Systran/faster-whisper-small', revision=REVISION,
    cache_dir=str(ROOT / 'models'),
    allow_patterns=['config.json', 'model.bin', 'tokenizer.json', 'vocabulary.*'],
))
# WhisperModel('small') resolves the default main ref in offline mode.
refs = snapshot.parent.parent / 'refs'
refs.mkdir(parents=True, exist_ok=True)
(refs / 'main').write_text(REVISION, encoding='utf-8')
for required in ('config.json', 'model.bin', 'tokenizer.json'):
    if not (snapshot / required).is_file():
        raise RuntimeError(f'Model download is incomplete: {required}')
print(f'Model ready: {snapshot}')

