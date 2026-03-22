# Benchmark

Benchmark-подсистема проекта теперь использует PostgreSQL как основное хранилище.

## Что хранится в БД

- наборы вопросов (`question sets`)
- вопросы внутри каждого набора
- история всех benchmark run по каждому набору
- case-level результаты каждого run

Стартовые seed-наборы теперь задаются Python-модулем [benchmark_seed_data.py](/c:/repos/rutoken-RAG-2/app/services/benchmark_seed_data.py) и добавляются в PostgreSQL по фиксированным `set_id`, если их еще нет в БД.

## Основные endpoints

- `GET /benchmark` — web UI
- `GET /benchmark/sets` — список наборов вопросов
- `POST /benchmark/sets` — создать набор
- `GET /benchmark/sets/{set_id}` — получить набор с вопросами
- `PUT /benchmark/sets/{set_id}` — обновить набор и вопросы
- `POST /benchmark/sets/{set_id}/run` — запустить benchmark по набору
- `GET /benchmark/runs?set_id=...` — история запусков
- `GET /benchmark/runs/{run_id}` — детали конкретного запуска
- `GET /benchmark/results?set_id=...` — shortcut на последний run

## CLI

```bash
python scripts/run_benchmark.py
python scripts/run_benchmark.py --set-id <question-set-id>
python scripts/seed_benchmark_sets.py
```

Если `--set-id` не указан, будет использован первый доступный набор.

## Docker

Для benchmark теперь нужен PostgreSQL контейнер:

```bash
docker compose up -d postgres qdrant api
```

## Реализация

- PostgreSQL repository: [app/services/benchmark_repository.py](/c:/repos/rutoken-RAG-2/app/services/benchmark_repository.py)
- deterministic evaluation: [app/services/benchmarking.py](/c:/repos/rutoken-RAG-2/app/services/benchmarking.py)
- общие benchmark routes: [app/main.py](/c:/repos/rutoken-RAG-2/app/main.py)
- web UI: [app/web/benchmark.html](/c:/repos/rutoken-RAG-2/app/web/benchmark.html)
