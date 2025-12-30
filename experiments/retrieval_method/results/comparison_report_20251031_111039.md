# Retrieval Methods Performance Comparison Report

**Generated:** 2025-10-31 11:10:39


## Overall Performance

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.2294 | 0.5611 | 
| hit@1 | 0.1667 | 0.4833 | 
| hit@3 | 0.2417 | 0.6417 | 
| hit@5 | 0.3333 | 0.6417 | 
| hit@10 | 0.4167 | 0.6417 | 
| precision@5 | 0.1433 | 0.4361 | 
| recall@5 | 0.3208 | 0.6333 | 

## Performance by Difficulty


### Basic

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.3400 | 0.4952 | 
| hit@3 | 0.3429 | 0.6286 | 
| hit@5 | 0.4000 | 0.6286 | 

### Intermediate

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.2241 | 0.5789 | 
| hit@3 | 0.2368 | 0.6316 | 
| hit@5 | 0.3947 | 0.6316 | 

### Advanced

| Metric | Embedding (File) | Knowledge Graph |
|---|---|---|
| mrr | 0.1513 | 0.5957 | 
| hit@3 | 0.1702 | 0.6596 | 
| hit@5 | 0.2340 | 0.6596 | 

## Key Insights

- **Best Overall (MRR):** Knowledge Graph (0.5611)
- **Best Hit@5:** Knowledge Graph (0.6417)
- **Fastest:** Embedding (File) (0.3124s)