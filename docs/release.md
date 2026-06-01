# Release to PyPI (RU/EN)

## RU

### Цель
Автоматически публиковать `muscles-cli` в PyPI через GitHub Actions без хранения PyPI token в secrets.

### Что используется
- Workflow: `.github/workflows/release.yml`
- Trigger:
  - `release.published`
  - `workflow_dispatch`
- Trusted Publishing (OIDC) через:
  - `pypa/gh-action-pypi-publish@release/v1`
- GitHub Environment: `pypi`

### Как это работает
1. `test` job:
   - checkout `muscles-cli` и `butkoden/muscles`
   - установка зависимостей
   - запуск: `PYTHONPATH=../muscles/src:src python -m pytest -q`
2. `build` job:
   - сборка `sdist` и `wheel` командой `python -m build`
   - upload артефактов `dist/*`
3. `publish` job:
   - download артефактов
   - публикация в PyPI через OIDC

### Настройка PyPI Trusted Publisher
В PyPI для проекта `muscles-cli` нужно создать Trusted Publisher с параметрами:
- owner: `butkoden`
- repository: `muscles-cli`
- workflow: `release.yml`
- environment: `pypi`

### Важно
- Не использовать PyPI API token/password в GitHub Secrets.
- Для publish job нужны permissions:
  - `id-token: write`
  - `contents: read`

---

## EN

### Goal
Publish `muscles-cli` to PyPI via GitHub Actions without storing a PyPI token in GitHub Secrets.

### Stack
- Workflow: `.github/workflows/release.yml`
- Triggers:
  - `release.published`
  - `workflow_dispatch`
- Trusted Publishing (OIDC) via:
  - `pypa/gh-action-pypi-publish@release/v1`
- GitHub Environment: `pypi`

### Flow
1. `test` job:
   - checkout `muscles-cli` and `butkoden/muscles`
   - install dependencies
   - run: `PYTHONPATH=../muscles/src:src python -m pytest -q`
2. `build` job:
   - build `sdist` and `wheel` with `python -m build`
   - upload `dist/*` artifacts
3. `publish` job:
   - download artifacts
   - publish to PyPI via OIDC

### PyPI Trusted Publisher setup
Create a Trusted Publisher in PyPI for `muscles-cli` with:
- owner: `butkoden`
- repository: `muscles-cli`
- workflow: `release.yml`
- environment: `pypi`

### Important
- Do not store PyPI token/password in repository or GitHub Secrets.
- `publish` job must keep permissions:
  - `id-token: write`
  - `contents: read`
