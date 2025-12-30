# Retrieval Methods Performance Comparison Report

**Generated:** 2025-10-28 14:40:31


## Overall Performance

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.2294 | 0.5292 | 
| hit@1 | 0.1667 | 0.4500 | 
| hit@3 | 0.2417 | 0.6083 | 
| hit@5 | 0.3333 | 0.6083 | 
| hit@10 | 0.4167 | 0.6083 | 
| precision@5 | 0.1433 | 0.4583 | 
| recall@5 | 0.3208 | 0.5958 | 

## Performance by Difficulty


### Basic

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.3400 | 0.6429 | 
| hit@3 | 0.3429 | 0.6571 | 
| hit@5 | 0.4000 | 0.6571 | 

### Intermediate

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.2241 | 0.4605 | 
| hit@3 | 0.2368 | 0.5526 | 
| hit@5 | 0.3947 | 0.5526 | 

### Advanced

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.1513 | 0.5000 | 
| hit@3 | 0.1702 | 0.6170 | 
| hit@5 | 0.2340 | 0.6170 | 

## Key Insights

- **Best Overall (MRR):** Knowledge Graph (0.5292)
- **Best Hit@5:** Knowledge Graph (0.6083)
- **Fastest:** Embedding (File) (0.2875s)