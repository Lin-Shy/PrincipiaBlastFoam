# Retrieval Methods Evaluation

This directory contains evaluation scripts for testing and comparing different retrieval methods used in the PrincipiaBlastFoam project.

## Overview

The evaluation framework tests two main retrieval approaches:
1. **Embedding-Based Retrieval**: Uses vector embeddings and FAISS for semantic search
   - **File-level (Default)**: Searches all individual files within cases for precise matching
   - Case-level (Optional): Searches README files of OpenFOAM tutorial cases for case-level overview
2. **Knowledge Graph-Based Retrieval**: Uses a structured knowledge graph of case content with LLM-generated search strategies

**Note**: The default embedding evaluation uses **file-level** retrieval for better precision and coverage.

## Files

- `evaluate_embedding_retriever.py` - Evaluates embedding-based retrieval methods
- `evaluate_knowledge_graph_retriever.py` - Evaluates knowledge graph-based retrieval
- `compare_retrievers.py` - Compares performance across all methods
- `results/` - Directory where evaluation results are saved

## Prerequisites

1. **Environment Setup**: Ensure your `.env` file contains:
   ```
   BLASTFOAM_TUTORIALS=/path/to/openfoam/tutorials
   EMBEDDING_API_KEY=your_api_key
   EMBEDDING_API_BASE_URL=your_api_base_url
   EMBEDDING_MODEL=text-embedding-v3
   LLM_API_KEY=your_llm_api_key
   LLM_API_BASE_URL=your_llm_base_url
   ```

2. **Validation Dataset**: The evaluation uses the BlastFOAM retrieval validation dataset located at:
   ```
   dataset/retrieval/blastfoam_retrieval_validation_dataset.json
   ```

3. **For Embedding-Based Retrieval**: Build the FAISS indexes first:
   ```bash
   python principia_ai/tools/build_embedding_index.py
   ```

4. **For Knowledge Graph Retrieval**: Ensure the knowledge graph data exists at:
   ```
   data/knowledge_graph/case_content_knowledge_graph/
   ```

## Usage

### 1. Evaluate Embedding-Based Retrieval

```bash
# Evaluate file-level embedding retrieval (default - searches all files)
python experiments/evaluate_embedding_retriever.py
```

This script will:
- Load the validation dataset (120 test queries)
- Initialize the **file-level** embedding retriever (searches all files for precise matching)
- Evaluate each query and calculate metrics
- Save detailed results to `experiments/results/`
- Optionally evaluate case-level retrieval (README only)

**Metrics Calculated:**
- Hit@K: Whether target file appears in top-K results
- MRR (Mean Reciprocal Rank): Average of 1/rank for first correct result
- Precision@K: Proportion of relevant files in top-K
- Recall@K: Proportion of target files found in top-K
- Performance by difficulty (basic/intermediate/advanced)
- Performance by category (20 query categories)

### 2. Evaluate Knowledge Graph Retrieval

```bash
# Evaluate knowledge graph-based retrieval
python experiments/evaluate_knowledge_graph_retriever.py
```

This script will:
- Load the validation dataset
- Initialize the knowledge graph retriever
- Evaluate using LLM-generated search strategies
- Calculate the same metrics as embedding retrieval
- Save results to `experiments/results/`

### 3. Compare All Methods

```bash
# Compare performance across all methods
python experiments/compare_retrievers.py
```

This script will:
- Load the most recent evaluation results for each method
- Generate comparison tables showing:
  - Overall performance metrics
  - Performance by difficulty level
  - Performance by query category
- Create visualization plots (if matplotlib is available):
  - Hit@K comparison chart
  - MRR by difficulty level
  - Precision/Recall comparison
  - Category performance heatmap
- Generate a markdown comparison report

## Evaluation Metrics

### Hit@K
Measures whether at least one target file appears in the top-K retrieved results.
- **Range**: 0 to 1 (0% to 100%)
- **Interpretation**: Higher is better. Hit@5 = 0.85 means 85% of queries found the target in top-5 results.

### Mean Reciprocal Rank (MRR)
Average of 1/rank for the first correct result across all queries.
- **Range**: 0 to 1
- **Interpretation**: Higher is better. MRR = 0.70 means on average, the first correct result appears at rank ~1.4.

### Precision@K
Proportion of retrieved items (in top-K) that are relevant.
- **Formula**: (# relevant items in top-K) / K
- **Range**: 0 to 1
- **Interpretation**: Higher is better. Measures retrieval accuracy.

### Recall@K
Proportion of relevant items that are retrieved in top-K.
- **Formula**: (# relevant items found in top-K) / (total # relevant items)
- **Range**: 0 to 1
- **Interpretation**: Higher is better. Measures retrieval completeness.

## Output Files

### Individual Evaluation Results
Saved to `experiments/results/`:
- `embedding_retrieval_case_YYYYMMDD_HHMMSS.json` - Case-level embedding results
- `embedding_retrieval_file_YYYYMMDD_HHMMSS.json` - File-level embedding results
- `knowledge_graph_retrieval_YYYYMMDD_HHMMSS.json` - Knowledge graph results

Each JSON file contains:
```json
{
  "metadata": {
    "dataset": "path/to/dataset",
    "timestamp": "...",
    "total_queries": 120
  },
  "aggregate_metrics": {
    "mrr": 0.75,
    "hit@1": 0.60,
    "hit@3": 0.80,
    "hit@5": 0.85,
    "by_difficulty": {...},
    "by_category": {...}
  },
  "detailed_results": [...]
}
```

### Comparison Results
Saved to `experiments/results/`:
- `comparison_report_YYYYMMDD_HHMMSS.md` - Markdown report with tables
- `comparison_plot_YYYYMMDD_HHMMSS.png` - Visualization charts

## Validation Dataset

The BlastFOAM retrieval validation dataset contains:
- **120 test queries** covering realistic user requests
- **20 categories**: turbulence models, time control, mesh, materials, etc.
- **3 difficulty levels**: basic (40), intermediate (40), advanced (40)
- **4 query types**: direct technical, file location, goal-based, complex configuration

Each query includes:
- Natural language query text
- Target file paths that should be retrieved
- Difficulty level and category labels
- Detailed description of the modification needed

## Customization

### Adjust K Values
Modify the `k_values` parameter in the evaluation scripts:
```python
metrics = evaluator.evaluate_all(k_values=[1, 3, 5, 10, 20])
```

### Filter by Category or Difficulty
You can modify the scripts to evaluate only specific subsets:
```python
# In evaluate_*.py, filter the dataset
filtered_dataset = [q for q in self.dataset if q['difficulty'] == 'advanced']
```

### Add Custom Metrics
Extend the evaluator classes with new metric calculation methods:
```python
def _calculate_custom_metric(self, retrieved_paths, target_paths):
    # Your custom metric logic
    return score
```

## Troubleshooting

### Issue: "No index found"
**Solution**: Build the embedding indexes first:
```bash
python principia_ai/tools/build_embedding_index.py
```

### Issue: "Knowledge graph not found"
**Solution**: Ensure the knowledge graph data exists in `data/knowledge_graph/case_content_knowledge_graph/`

### Issue: "No results found for comparison"
**Solution**: Run the individual evaluation scripts first before running the comparison script.

### Issue: "Matplotlib not found"
**Solution**: Install matplotlib for visualization:
```bash
pip install matplotlib
```

## Performance Expectations

Based on the validation dataset:

**Embedding-Based Retrieval (File-level - Default):**
- Best for: Specific file content, detailed parameter searches, precise matching
- Expected Hit@5: 70-85%
- Expected MRR: 0.55-0.70
- **Recommended for most use cases**

**Embedding-Based Retrieval (Case-level - Optional):**
- Best for: General case discovery, README-level information, case overview
- Expected Hit@5: 60-75%
- Expected MRR: 0.45-0.60

**Knowledge Graph Retrieval:**
- Best for: Structured queries, file-specific questions, complex relationships
- Expected Hit@5: 75-90%
- Expected MRR: 0.60-0.75

## Contributing

To add a new retrieval method:
1. Create a new evaluation script following the existing pattern
2. Implement the same metrics for fair comparison
3. Update the comparison script to include the new method
4. Document the new method in this README

## References

- Validation Dataset: `dataset/retrieval/RETRIEVAL_VALIDATION_DATASET_README.md`
- Embedding Retriever: `principia_ai/tools/embedding_retriever.py`
- Knowledge Graph Retriever: `principia_ai/tools/case_content_knowledge_graph_tool.py`
