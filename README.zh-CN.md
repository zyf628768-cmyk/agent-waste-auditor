# AgentWaste

**Find the Hidden Cost of AI Work. — 找出 AI 工作的隐性成本。**

AgentWaste 是本地优先的开源 AI Agent 任务经济性审计 CLI 与 Skill。覆盖模型、工具、失败、返工、等待和质量处理成本；仅分析用户指定的文件。Python 3.11+，MIT，无运行时第三方依赖，无付费 API，无遥测上传。

## 快速开始

```sh
python -m pip install .
agentwaste import examples/success.jsonl --tasks examples/success.tasks.json -o events.json
agentwaste analyze events.json --pricing examples/pricing.json -o audit.json
agentwaste report audit.json --format html -o audit.html
agentwaste pricing examples/pricing.json
agentwaste doctor --input examples/success.jsonl --pricing examples/pricing.json
python scripts/demo.py
```

六个命令 `import/analyze/compare/report/pricing/doctor` 均支持 `--help`；也可在源码目录执行 `python -m agentwaste`。报告支持 JSON、Markdown、离线 HTML 和费用明细 CSV。导入支持通用 JSONL/CSV、实验性 Codex/Claude Code 本地格式、完整 OpenAI Responses/Chat Completions 对象；不需要联网。CLI 会拒绝输出覆盖本次命令指定的输入文件，但可能覆盖已有报告文件。

发布前复核进一步增加了严格嵌套 Schema、重复 JSON 键与畸形 CSV 拒绝、原子报告写入、可配置检测窗口和安装后验证。金额计算固定在局部 128 位 Decimal 上下文中，不受调用方精度设置影响；极端数值会明确拒绝。

## 核算原则

- 所有金额用 Decimal，保存为字符串；按原币种、真实记录 actual、已知价格估算 estimated、用户手工 manual 分账。actual 仅表示来源声称实际收费，不代表已对账。
- 无法获取的价格、用量和收费工具费用列入未知，不能当成零。总额只是已观测小计，不保证含未记录的费用。
- 输入 Token 包含缓存读与写；缓存费用单独计算，模型价格有版本、来源和有效日期。示例模型及价格为 SYNTHETIC，不能当成商业模型现价。
- 失败调用仍计费；失败成本归因与成本分类是两个视图，不能再次相加。人工分钟不含返工分钟，按可选时薪单独计算；等待时间不会自动换算工资。
- ROI 缺少人工基准、明确验收、人工投入或完整成本时降级为“无法核算”。估算价格或未经核实基准产生“情景估计”。`verified_basis` 仅表示用户确认基准及来源数据，并非独立财务认证。
- 每条浪费结论均为有证据的嫌疑，不是确定判断，也不自动计算可追回金额。明确的正常重试、用户要求重复、幂等检查与已确认进展可以豁免普通重复规则。

## 演示与比较

所有演示均明确标注 SYNTHETIC，执行 `python scripts/demo.py` 后可打开：

| 演示 | 报告 | 实际演示结果 |
| --- | --- | --- |
| 普通成功任务 | [success.html](examples/reports/success.html) | USD 0.30 模型估算 + 0.02 工具记录 + 6.00 人工 = 6.32；零嫌疑 |
| 高浪费失败任务 | [waste.html](examples/reports/waste.html) | USD 30.0454；9 条嫌疑、8 类规则；ROI 无法核算 |
| 同验收 Agent 比较 | [comparison.html](examples/reports/comparison.html) | 6.32 与 12.65；均为 1/1 成功，人工 10 与 20 分钟 |

这些不是 Codex/Claude 的真实基准评测。比较必须有相同任务键、难度、验收 ID，并按费用覆盖范围分组；缺失元数据排除，全局不排名。`compare --by` 支持 agent、model、prompt_strategy、workflow。

比较现在进一步按真实/估算费用来源、人工投入完整度、未知原因和币种分组，展示每次尝试及每个成功任务成本、已知/未知结果数量和耗时中位数，避免尝试次数不同导致总额误导。比较 CSV 也包含这些指标。`analyze --rules examples/rules.json` 可配置重复次数、时间窗口、上下文 Token 和按原币种设置的高费用阈值；默认窗口一小时，仅默认设置 USD 1 高费用复核线，已确认进展会中断重复候选序列。

## 与现有产品的关系

[Langfuse](https://langfuse.com/docs/observability/features/token-and-cost-tracking) 已支持用量、真实与推断费用、模型配置及评估实验；[LangSmith](https://www.langchain.com/langsmith/observability) 已支持追踪、费用、延迟和评估；[Helicone](https://www.helicone.ai/) 提供网关、费用监控、缓存与路由；[OpenLIT](https://www.openlit.io/) 提供 OpenTelemetry 可观测性、Agent 评估、费用与 GPU 监控。调研日期为 2026-10-19，来源及详细对照见 [英文 README](README.md)。

AgentWaste 不宣称原创 Token 看板或完整任务成本概念。其重点是无需服务端的指定日志离线审计，将失败、返工、人工介入与带假设的经济价值放在同一报告中；不取代这些产品的线上监控和评估平台。

## 隐私、限制与验证

不扫描私人目录、环境变量和聊天记录；不保存提示词正文、完整命令、文件内容或工具输出，不执行日志命令。保存必要摘要、计数及脱敏后的结构化字段和摘要哈希。哈希可能被猜测，正则脱敏不是通用个人信息识别器，请勿将隐私正文放进标识字段，公开报告前仍需审阅。

原生适配器为实验性结构配置，仅以合成样本验证；不保证某大版本全部变种兼容。暂不支持流式 API、组织用量聚合、订阅账单分摊、汇率换算、自动缓存 TTL 推断、原生日志工具退出码可靠提取或自动人工投入识别。未能确定的数据保留为未知。可选 Web Dashboard 暂未实现；离线 HTML 已提供。

```sh
python -m pip install '.[test]' build
python -m unittest discover -s tests -v
python scripts/demo.py
python -m build
```

[验证记录](docs/validation.md) 区分已运行的 Windows 本地测试与尚待 GitHub 执行的跨平台矩阵。[格式说明](docs/formats.md)、[审计方法](docs/methodology.md)、[安全政策](SECURITY.md)、[发布步骤](docs/release.md)、[Skill](SKILL.md) 提供使用边界和维护说明。
