# Retrieval Evaluation Scripts Summary

## Created Files

This directory now contains comprehensive evaluation scripts for testing different retrieval methods. Below is a summary of each script and its purpose.

---

## 1. `evaluate_embedding_retriever.py`
**Purpose**: Evaluate embedding-based retrieval performance

**Features**:
- Tests **file-level embedding retrieval by default** (searches all files for precise matching)
- Optionally tests case-level (README only) embedding retrieval
- Evaluates against 120 validation queries
- Calculates Hit@K, MRR, Precision@K, and Recall@K metrics
- Analyzes performance by difficulty level (basic/intermediate/advanced)
- Analyzes performance by category (20 query types)
- Saves detailed results to JSON files

**Usage**:
```bash
# Default: Evaluate file-level retrieval (all files)
python experiments/evaluate_embedding_retriever.py
```

**Prerequisites**:
- FAISS indexes must be built first using `build_embedding_index.py` with `embedding_level='file'`
- Requires BLASTFOAM_TUTORIALS path in .env
- Requires embedding API credentials

**Output**: 
- `results/embedding_retrieval_file_YYYYMMDD_HHMMSS.json` (default)
- `results/embedding_retrieval_case_YYYYMMDD_HHMMSS.json` (if optional case-level eval is run)

---

## 2. `evaluate_knowledge_graph_retriever.py`
**Purpose**: Evaluate knowledge graph-based retrieval performance

**Features**:
- Tests case content knowledge graph retrieval
- Uses LLM-generated search strategies
- Evaluates same metrics as embedding retrieval for fair comparison
- Extracts file paths from structured knowledge graph results
- Handles both exact and partial path matching

**Usage**:
```bash
python experiments/evaluate_knowledge_graph_retriever.py
```

**Prerequisites**:
- Knowledge graph data in `data/knowledge_graph/case_content_knowledge_graph/`
- Requires LLM API credentials for search strategy generation

**Output**: 
- `results/knowledge_graph_retrieval_YYYYMMDD_HHMMSS.json`

---

## 3. `compare_retrievers.py`
**Purpose**: Compare performance across all retrieval methods

**Features**:
- Loads and compares results from all retrieval methods
- Generates comprehensive comparison tables
- Creates visualization plots (Hit@K, MRR, Precision/Recall)
- Analyzes performance by difficulty and category
- Generates markdown comparison reports
- Identifies best-performing methods for different scenarios

**Usage**:
```bash
python experiments/compare_retrievers.py
```

**Prerequisites**:
- Evaluation results must exist from other scripts
- Optional: matplotlib for visualizations

**Output**: 
- Console comparison tables
- `results/comparison_plot_YYYYMMDD_HHMMSS.png` (if matplotlib available)
- `results/comparison_report_YYYYMMDD_HHMMSS.md`

---

## 4. `quick_test.py`
**Purpose**: Quick sanity check for retrieval systems

**Features**:
- Tests both retrieval methods with 5 sample queries
- Verifies setup and configuration
- Displays sample results for manual inspection
- Helps identify setup issues before running full evaluations
- Interactive testing (can skip methods)

**Usage**:
```bash
python experiments/quick_test.py
```

**Use Case**: 
- First-time setup verification
- After making changes to retrieval systems
- Before running time-consuming full evaluations

**Output**: Console output with test results

---

## 5. `analyze_failures.py`
**Purpose**: Analyze failed queries to identify improvement opportunities

**Features**:
- Identifies queries where retrieval failed (Hit@5 = 0)
- Analyzes failure patterns by category and difficulty
- Shows detailed failure examples with retrieved vs target files
- Compares failures across different retrieval methods
- Generates actionable improvement suggestions
- Identifies "hard" queries that fail for all methods

**Usage**:
```bash
python experiments/analyze_failures.py
```

**Interactive Features**:
- Select which evaluation results to analyze
- Optionally compare with another method
- View detailed examples of failures

**Output**: 
- Console analysis with patterns and suggestions
- Can help prioritize development efforts

---

## Workflow

### Recommended Evaluation Workflow:

1. **Initial Setup & Testing**
   ```bash
   # Verify setup with quick test
   python experiments/quick_test.py
   ```

2. **Run Full Evaluations**
   ```bash
   # Evaluate embedding retrieval
   python experiments/evaluate_embedding_retriever.py
   
   # Evaluate knowledge graph retrieval
   python experiments/evaluate_knowledge_graph_retriever.py
   ```

3. **Compare Results**
   ```bash
   # Generate comparison report and visualizations
   python experiments/compare_retrievers.py
   ```

4. **Analyze Failures**
   ```bash
   # Deep dive into failures for improvement
   python experiments/analyze_failures.py
   ```

---

## Results Directory Structure

After running evaluations, the `results/` directory will contain:

```
experiments/results/
├── embedding_retrieval_case_20250128_143022.json
├── embedding_retrieval_file_20250128_144533.json
├── knowledge_graph_retrieval_20250128_150215.json
├── comparison_plot_20250128_151030.png
└── comparison_report_20250128_151030.md
```

---

## Key Metrics Explained

### Hit@K
- **Definition**: Percentage of queries where at least one target file appears in top-K results
- **Range**: 0.0 to 1.0 (0% to 100%)
- **Goal**: Maximize

### MRR (Mean Reciprocal Rank)
- **Definition**: Average of 1/rank for first correct result
- **Example**: If first correct result is at rank 3, contributes 1/3 = 0.333
- **Range**: 0.0 to 1.0
- **Goal**: Maximize

### Precision@K
- **Definition**: Proportion of retrieved items (in top-K) that are relevant
- **Formula**: (# relevant in top-K) / K
- **Measures**: Accuracy of retrieval
- **Goal**: Maximize

### Recall@K
- **Definition**: Proportion of relevant items found in top-K
- **Formula**: (# relevant found in top-K) / (total # relevant)
- **Measures**: Completeness of retrieval
- **Goal**: Maximize

---

## Customization Examples

### Evaluate Only Specific Categories
```python
# In evaluate_*.py, modify the dataset loading
filtered_dataset = [q for q in self.dataset if q['category'] in ['turbulence_model', 'time_control']]
```

### Change K Values
```python
# In any evaluation script
metrics = evaluator.evaluate_all(k_values=[1, 2, 3, 5, 10, 20])
```

### Add Custom Metrics
```python
# In evaluator class
def _calculate_f1_score(self, retrieved, target, k):
    precision = self._calculate_precision_at_k(retrieved, target, k)
    recall = self._calculate_recall_at_k(retrieved, target, k)
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)
```

---

## Troubleshooting

### "No index found"
- **Solution**: Run `python principia_ai/tools/build_embedding_index.py` first

### "Knowledge graph not found"
- **Solution**: Ensure knowledge graph data exists in `data/knowledge_graph/case_content_knowledge_graph/`

### "No results found for comparison"
- **Solution**: Run individual evaluation scripts before running comparison

### API timeouts or errors
- **Solution**: Check API credentials in .env file
- **Solution**: Reduce batch size or add retry logic

### Matplotlib errors
- **Solution**: Install with `pip install matplotlib`
- **Solution**: Script will skip plots if matplotlib unavailable

---

## Performance Benchmarks

Based on the BlastFOAM validation dataset (120 queries):

| Method | Expected Hit@5 | Expected MRR | Avg Time/Query | Status |
|--------|---------------|--------------|----------------|---------|
| Embedding (File) | 0.70-0.85 | 0.55-0.70 | 0.2-0.5s | **Default** |
| Knowledge Graph | 0.75-0.90 | 0.60-0.75 | 0.5-1.5s | Recommended |
| Embedding (Case) | 0.60-0.75 | 0.45-0.60 | 0.1-0.3s | Optional |

**Note**: Actual performance depends on:
- Quality of embeddings/knowledge graph
- API response times
- Complexity of query distribution
- Hardware specifications

**Recommendation**: Use file-level embedding for comprehensive coverage, or knowledge graph for best accuracy.

---

## Future Enhancements

Potential additions to the evaluation framework:

1. **Hybrid Retrieval Evaluation**: Test combination of embedding + knowledge graph
2. **Cross-Validation**: K-fold evaluation for robust metrics
3. **User Study Integration**: Incorporate human relevance judgments
4. **Temporal Analysis**: Track performance improvements over time
5. **Error Analysis Dashboard**: Interactive web-based failure exploration
6. **A/B Testing Framework**: Compare retrieval algorithm variants
7. **Query Difficulty Prediction**: Predict which queries will be hard
8. **Automatic Parameter Tuning**: Grid search for optimal K, thresholds, etc.

---

## References

- Validation Dataset Documentation: `dataset/retrieval/RETRIEVAL_VALIDATION_DATASET_README.md`
- Embedding Retriever Implementation: `principia_ai/tools/embedding_retriever.py`
- Knowledge Graph Retriever Implementation: `principia_ai/tools/case_content_knowledge_graph_tool.py`
- FAISS Index Builder: `principia_ai/tools/build_embedding_index.py`

---

## Contributing

To add new evaluation scripts or metrics:

1. Follow the existing pattern in evaluation scripts
2. Ensure consistent metric calculation across methods
3. Update this summary document
4. Add tests if applicable
5. Update the main README.md with high-level changes

## Questions or Issues?

- Check the main README.md for detailed documentation
- Review the validation dataset README for query structure
- Examine existing evaluation results for expected format
- Test with quick_test.py to isolate issues
