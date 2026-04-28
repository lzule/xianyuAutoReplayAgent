# cases

这里放可复用的案例材料。

建议整理：

- 典型项目类型
- 交付结果
- 你擅长解决的问题
- 客户常见诉求

## RAG 样本文件

- `rag_cases.jsonl`：脱敏后的案例样本，供 `app/rag_engine` 检索和重排使用。
- 构建方式：
  - `python scripts/build_rag_cases.py --input-dir ../chat --output knowledge/cases/rag_cases.jsonl`
