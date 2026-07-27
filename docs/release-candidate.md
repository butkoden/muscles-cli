# CLI RC checklist

Before tagging an RC, verify the public command surface and a clean generated
project:

```bash
PYTHONPATH=../muscles/src:src python -m pytest --import-mode=importlib -q
python -m build --wheel --sdist
muscles new demo --runtime cli
```

The canonical commands are `new`, `inspect`, `routes`, `schemas`, `rules`,
`action`, `doctor` and `test`. Existing non-empty directories must remain
protected unless `--force` is explicit.
