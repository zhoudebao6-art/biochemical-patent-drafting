# 上游v6.37架构的生化批次

本技能保留parallel_batch.py、cli_pool.py、stage_pool_runner.py、cli_evidence.py、incremental_review.py、independent_delivery.py等完整执行链，不另造简化调度器。内容规范已替换为生化。旧软通技能及其冻结批次不受影响。

用户本轮是技能制作/维护时不启动生产。实际办案先递归识别优化书，剔除历史稿/重复版本/锁文件，按内容核定正式完整名称及同案附件。输入、工作、桌面交付目录分开；二进制DOC先在只读intake转换并保留原/转换SHA，primary_source使用DOCX。

selection结构为projects:[{title,source_files:[相对路径],primary_source:相对路径}]，不凭文件名猜标题。正式名称需唯一合法，不能清洗截短或加案号掩盖冲突。

```text
python scripts/parallel_batch.py scan --input 输入目录 --out 扫描.json
python scripts/parallel_batch.py init --input 输入目录 --work-root 工作目录 --selection 选择.json --controller 本批控制器标识
python scripts/cli_pool.py run --manifest 批次manifest.json --workers 真实总容量 --controller 同一控制器标识
```

init冻结本技能/规则/模型/来源；以后命令自动重定向到快照。三池上限16/8/8、目标32、在制最多64；64GB内存建议最多同时开32个CLI任务，实际容量必须核定并显式传workers。draft→review→revise(需要时)→新会话review；同案一个活动attempt。stage_pool_runner的独立准备/收稿通道和发布通道保持原版，完成即流转补位，通过即平铺交付，不等全批。真实CLI身份、模型/强度、会话日志和退出证据由cli_evidence校验，配置不证明执行。

手工collaboration通道用reserve --prepare返回的spawn_arguments及worker_context，真实派发后保存dispatch并bind；收稿按worker-receipt，record后立即deliver。命令参数以脚本--help及cli-workers.md为准，不伪造派发证据。draft高、review/revise极高强度沿batch-policy，不能静默换模型。

六项键保留，source_support包含配方/实验数据及原表，formulas包含化学式/单位上下标，figures覆盖全部终图。生化输出契约在原pass和交付门禁接入，不新增模型轮次；源绑定检查不能被旧软通禁词误阻断。总控仍核实际语义、图和全部当前页。改稿后新SHA、新渲染及独立重验，未做not_run。

一次批次唯一桌面目录为原始输入文件夹完整名称_终稿_冻结batch_id，所有正式名称.docx直接放根部；证据/待处理留工作区。原子发布、防覆盖、幂等恢复及同批目录核验沿原工具；accepted一案即交付一案。完成后释放其专属worker，不结束共享Office/其他项目进程。

恢复先summary、收已有结果，确认旧进程退出后cancel/重派，保留失败日志，不重算源SHA放行。内部工具缺陷按tool-fault-recovery修复验证并接续，冻结身份异常不放行。无CLI时才按真实子代理容量执行；无法独立审查只能交候选状态，不造pass。旧serial兼容代码保留但新生化批次只走当前三池。
