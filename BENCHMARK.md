# Benchmark

Проект содержит deterministic benchmark без `LLM-as-judge`.

## Что проверяется

- `exact_match`: нормализованное точное совпадение, если в кейсе задан `exact_answer`
- `required_terms`: все обязательные термины должны присутствовать в ответе
- `required_any`: в ответе должен присутствовать хотя бы один термин из каждой группы
- `forbidden_terms`: запрещенные термины не должны появляться
- `citations`: обязательные `dev.rutoken.ru` URL должны присутствовать в citations
- `refusal`: если `expected_refusal=true`, ответ должен быть отказом; если `false`, отказ не должен происходить

## Dataset

Файл по умолчанию: [benchmark/dataset.jsonl](/c:/repos/rutoken-RAG-2/benchmark/dataset.jsonl)

Формат одной строки:

```json
{
  "id": "access-levels",
  "question": "Какие уровни доступа к объектам в памяти Рутокен?",
  "tags": ["product_matrix", "access"],
  "required_terms": ["гость", "пользователь", "администратор"],
  "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=2228237"]
}
```

Поддерживаемые поля:

- `id`
- `question`
- `tags`
- `exact_answer`
- `required_terms`
- `required_any`
- `forbidden_terms`
- `required_sources`
- `expected_refusal`
- `notes`

## CLI

```bash
python scripts/run_benchmark.py
```

Результат сохраняется в [data/benchmark_results.json](/c:/repos/rutoken-RAG-2/data/benchmark_results.json).

## Web UI

После запуска API:

- `GET /benchmark` показывает HTML-панель benchmark
- `GET /benchmark/cases` возвращает dataset preview
- `GET /benchmark/results` возвращает последний прогон
- `POST /benchmark/run` запускает benchmark и сохраняет новый результат

## Реализация

- backend benchmark: [app/services/benchmarking.py](/c:/repos/rutoken-RAG-2/app/services/benchmarking.py)
- shared pipeline runner: [app/services/pipeline.py](/c:/repos/rutoken-RAG-2/app/services/pipeline.py)
- FastAPI routes: [app/main.py](/c:/repos/rutoken-RAG-2/app/main.py)
- web viewer: [app/web/benchmark.html](/c:/repos/rutoken-RAG-2/app/web/benchmark.html)
