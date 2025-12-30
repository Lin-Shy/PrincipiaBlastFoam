# Retrieval Evaluation Workflow Guide

## Quick Start

### For First-Time Users

```bash
# 1. Test your setup (takes ~1 minute)
python experiments/quick_test.py

# 2. Run all evaluations automatically (takes ~30-60 minutes)
python experiments/run_all_evaluations.py
```

### For Experienced Users

```bash
# Run specific evaluations
python experiments/evaluate_embedding_retriever.py         # ~10-20 min
python experiments/evaluate_knowledge_graph_retriever.py   # ~15-30 min
python experiments/compare_retrievers.py                   # ~1 min
python experiments/analyze_failures.py                     # Interactive
```

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        START EVALUATION                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   Quick Test Setup     │
                   │  (quick_test.py)       │
                   │  - Test 5 samples      │
                   │  - Verify config       │
                   └────────┬───────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │  Setup OK?                   │
              └─────┬───────────────────┬───┘
                    │ NO                │ YES
                    ▼                   ▼
            ┌────────────┐     ┌──────────────────────────┐
            │ Fix Issues │     │  Run Full Evaluations     │
            │ - Check    │     │                           │
            │   .env     │     │  ┌─────────────────────┐  │
            │ - Build    │     │  │ Embedding Eval      │  │
            │   indexes  │     │  │ (Case-Level)        │  │
            │ - Verify   │     │  │ - 120 queries       │  │
            │   paths    │     │  │ - Save results      │  │
            └────────────┘     │  └──────────┬──────────┘  │
                               │             │             │
                               │  ┌──────────▼──────────┐  │
                               │  │ Knowledge Graph     │  │
                               │  │ Eval                │  │
                               │  │ - 120 queries       │  │
                               │  │ - Save results      │  │
                               │  └──────────┬──────────┘  │
                               └─────────────┼─────────────┘
                                             ▼
                                ┌────────────────────────┐
                                │  Comparison Analysis   │
                                │  (compare_retrievers)  │
                                │  - Load all results    │
                                │  - Generate tables     │
                                │  - Create plots        │
                                │  - Write report        │
                                └────────┬───────────────┘
                                         │
                                         ▼
                                ┌────────────────────────┐
                                │  Failure Analysis      │
                                │  (analyze_failures.py) │
                                │  - Identify failures   │
                                │  - Find patterns       │
                                │  - Generate insights   │
                                └────────┬───────────────┘
                                         │
                                         ▼
                                ┌────────────────────────┐
                                │  Review & Improve      │
                                │  - Read reports        │
                                │  - Implement fixes     │
                                │  - Re-evaluate         │
                                └────────────────────────┘
```

---

## File Organization

```
experiments/
├── README.md                           # Detailed documentation
├── SCRIPTS_SUMMARY.md                  # Script reference guide
├── WORKFLOW_GUIDE.md                   # This file
│
├── quick_test.py                       # ⚡ Quick setup verification
├── run_all_evaluations.py             # 🚀 Master automation script
│
├── evaluate_embedding_retriever.py     # 📊 Embedding evaluation
├── evaluate_knowledge_graph_retriever.py # 📊 KG evaluation
├── compare_retrievers.py              # 📈 Comparison analysis
├── analyze_failures.py                # 🔍 Failure deep-dive
│
└── results/                           # 📁 Output directory
    ├── embedding_retrieval_case_*.json
    ├── knowledge_graph_retrieval_*.json
    ├── comparison_plot_*.png
    ├── comparison_report_*.md
    └── master_summary_*.md
```

---

## Usage Scenarios

### Scenario 1: First Time Evaluation

**Goal**: Establish baseline performance metrics

```bash
# Step 1: Verify everything works
python experiments/quick_test.py

# Step 2: Run automated evaluation
python experiments/run_all_evaluations.py

# Step 3: Review the master summary
cat experiments/results/master_summary_*.md

# Step 4: Check detailed comparison report
cat experiments/results/comparison_report_*.md
```

**Output**: Baseline metrics for all retrieval methods

---

### Scenario 2: Method Improvement

**Goal**: Improve a specific retrieval method

```bash
# Step 1: Run current evaluation
python experiments/evaluate_embedding_retriever.py

# Step 2: Analyze failures
python experiments/analyze_failures.py
# → Select the results file
# → Review failure patterns
# → Note improvement suggestions

# Step 3: Make code improvements to retriever
# (Edit principia_ai/tools/embedding_retriever.py)

# Step 4: Re-evaluate
python experiments/evaluate_embedding_retriever.py

# Step 5: Compare before/after
python experiments/compare_retrievers.py
```

**Output**: Performance delta showing improvement

---

### Scenario 3: Comparative Study

**Goal**: Compare different retrieval approaches

```bash
# Evaluate all methods
python experiments/evaluate_embedding_retriever.py
python experiments/evaluate_knowledge_graph_retriever.py

# Generate comparison
python experiments/compare_retrievers.py

# Analyze where each method excels
python experiments/analyze_failures.py
# → Compare failures across methods
# → Identify method-specific strengths
```

**Output**: Comparative report with visualizations

---

### Scenario 4: Category-Specific Analysis

**Goal**: Understand performance on specific query types

```bash
# Run full evaluation
python experiments/run_all_evaluations.py

# Check category performance in comparison report
# Look for categories with poor performance

# Analyze failures for specific category
python experiments/analyze_failures.py
# → Filter by category in code or results

# Create category-specific improvements
```

**Output**: Category-specific insights and recommendations

---

## Interpreting Results

### Understanding Metrics

**Hit@K** (Most Important for Users)
- Hit@3 = 0.80 → 80% of users find answer in top 3 results
- Hit@5 = 0.90 → 90% of users find answer in top 5 results
- **Target**: Hit@5 > 0.85 for good user experience

**MRR** (Mean Reciprocal Rank)
- MRR = 0.70 → Average rank of first correct result is ~1.4
- MRR = 0.50 → Average rank is 2.0
- **Target**: MRR > 0.65 for good precision

**Precision@K** (Retrieval Accuracy)
- Precision@5 = 0.60 → 60% of top-5 results are relevant
- **Target**: Precision@5 > 0.50 for acceptable quality

**Recall@K** (Completeness)
- Recall@5 = 0.80 → 80% of target files found in top-5
- **Target**: Recall@5 > 0.70 for comprehensive retrieval

---

### Reading Comparison Tables

Example output from `compare_retrievers.py`:

```
Metric                    | Embedding (File)         | Knowledge Graph          |
--------------------------|--------------------------|--------------------------|
mrr                       |                   0.6234 |                   0.7125 |
hit@5                     |                   0.7583 |                   0.8417 |
```

**Interpretation**:
- Knowledge Graph has better MRR (0.71 vs 0.62) → More precise results
- Knowledge Graph has better Hit@5 (84% vs 76%) → Better user satisfaction
- Knowledge Graph is likely the better choice for this use case
- Embedding (File) searches all files for comprehensive coverage

---

### Analyzing Failure Patterns

When running `analyze_failures.py`, look for:

1. **High-Failure Categories**
   - Categories with >50% failure rate need attention
   - May indicate missing knowledge or poor query understanding

2. **Difficulty Distribution**
   - If "basic" queries fail → Core functionality issues
   - If "advanced" queries fail → Expected, but improvement possible

3. **Common Target Files**
   - Files that frequently appear in failures
   - May need better indexing or metadata

4. **Method Comparison**
   - Queries that fail in one method but succeed in another
   - Opportunities for hybrid approaches

---

## Performance Expectations

### Timing Benchmarks (120 queries)

| Script | Expected Duration | Notes |
|--------|------------------|-------|
| quick_test.py | ~1-2 minutes | 5 sample queries (file-level) |
| evaluate_embedding_retriever.py | ~10-20 minutes | File-level by default, depends on API speed |
| evaluate_knowledge_graph_retriever.py | ~15-30 minutes | LLM calls for search strategies |
| compare_retrievers.py | ~1 minute | Just loads and analyzes |
| analyze_failures.py | Interactive | Manual exploration |
| run_all_evaluations.py | ~30-60 minutes | Includes all steps |

### Disk Space

- Embedding indexes (file-level): ~500 MB - 2 GB (depending on case count and files)
- Embedding indexes (case-level): ~100-500 MB (if using README only)
- Knowledge graph data: ~50-200 MB
- Evaluation results: ~5-10 MB per run
- Plots and reports: ~1-5 MB per run

---

## Troubleshooting Guide

### Issue: Quick test fails on embedding retriever
```
Solution:
1. Build indexes: python principia_ai/tools/build_embedding_index.py
2. Check BLASTFOAM_TUTORIALS path in .env
3. Verify embedding API credentials
```

### Issue: Quick test fails on knowledge graph retriever
```
Solution:
1. Check knowledge graph data exists: data/knowledge_graph/case_content_knowledge_graph/
2. Verify LLM API credentials in .env
3. Test API connection manually
```

### Issue: "No results found for comparison"
```
Solution:
1. Run individual evaluation scripts first
2. Check experiments/results/ directory has JSON files
3. Ensure JSON files are valid (not corrupted)
```

### Issue: Slow evaluation (>1 hour for 120 queries)
```
Possible causes:
1. API rate limiting → Add retry logic or delays
2. Network latency → Check connection
3. Large dataset → Normal for comprehensive evaluation

Solutions:
- Reduce test set size for faster iterations
- Use parallel processing if API allows
- Cache embedding results
```

### Issue: Poor performance metrics
```
Expected ranges (validation dataset):
- Hit@5: 0.60-0.90
- MRR: 0.45-0.75

If below range:
1. Check if indexes are up-to-date
2. Verify knowledge graph completeness
3. Review query-to-file matching logic
4. Run analyze_failures.py for insights
```

---

## Tips for Success

1. **Start Small**: Use `quick_test.py` before full runs
2. **Iterate Quickly**: Test changes on small datasets first
3. **Compare Versions**: Keep old results to track progress
4. **Document Changes**: Note what you changed between runs
5. **Analyze Failures**: Don't just look at aggregate metrics
6. **Use Automation**: `run_all_evaluations.py` for consistent runs
7. **Version Control**: Commit results along with code changes

---

## Next Steps After Evaluation

1. **If results are good (Hit@5 > 0.85)**:
   - Document the configuration
   - Consider deploying to production
   - Set up monitoring for performance tracking

2. **If results are moderate (Hit@5 = 0.70-0.85)**:
   - Analyze top failure categories
   - Implement targeted improvements
   - Consider hybrid approaches

3. **If results are poor (Hit@5 < 0.70)**:
   - Deep dive with `analyze_failures.py`
   - Review fundamental retrieval approach
   - Consider alternative methods or major refactoring

---

## Advanced Usage

### Custom Metrics

Add your own metrics by extending the evaluator classes:

```python
# In evaluate_embedding_retriever.py
def _calculate_custom_metric(self, retrieved, target, k):
    # Your custom logic
    return score
```

### Filtered Evaluation

Test on specific query subsets:

```python
# Filter by category
filtered = [q for q in dataset if q['category'] == 'turbulence_model']

# Filter by difficulty
filtered = [q for q in dataset if q['difficulty'] == 'advanced']
```

### Parallel Evaluation

Speed up with concurrent processing:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(evaluate_single_query, queries))
```

---

## Support

- **Documentation**: See README.md for detailed explanations
- **Examples**: Review SCRIPTS_SUMMARY.md for code examples
- **Dataset Info**: Check dataset/retrieval/RETRIEVAL_VALIDATION_DATASET_README.md
- **Issues**: Analyze with analyze_failures.py

---

**Happy Evaluating! 🚀**
