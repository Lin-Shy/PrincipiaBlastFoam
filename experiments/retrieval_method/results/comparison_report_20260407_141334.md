# Retrieval Methods Performance Comparison Report

**Generated:** 2026-04-07 14:13:34


## Overall Performance

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.0349 | 0.6963 | 
| hit@1 | 0.0000 | 0.6476 | 
| hit@3 | 0.0381 | 0.7429 | 
| hit@5 | 0.0524 | 0.7524 | 
| hit@10 | 0.0905 | 0.7667 | 
| precision@5 | 0.0105 | 0.1638 | 
| recall@5 | 0.0429 | 0.7405 | 

## Performance by Difficulty


### Basic

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.0133 | 0.8319 | 
| hit@3 | 0.0130 | 0.8961 | 
| hit@5 | 0.0130 | 0.8961 | 

### Intermediate

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.0557 | 0.4222 | 
| hit@3 | 0.0667 | 0.5333 | 
| hit@5 | 0.1333 | 0.5333 | 

### Advanced

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.0464 | 0.6427 | 
| hit@3 | 0.0508 | 0.6695 | 
| hit@5 | 0.0678 | 0.6864 | 

## Key Insights

- **Best Overall (MRR):** Knowledge Graph (0.6963)
- **Best Hit@5:** Knowledge Graph (0.7524)
- **Fastest:** Embedding (File) (0.4024s)