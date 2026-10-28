# 上游v6.37架构的生化批次

本技能保留parallel_batch.py、cli_pool.py、stage_pool_runner.py、cli_evidence.py、incremental_review.py、independent_delivery.py等完整执行链，不另造简化调度器。内容规范已替换为生化。旧软通技能及其冻结批次不受影响。

用户本轮是技能制作/维护时不启动生产。实际办案先递归识别优化书，剔除历史稿/重复版本/锁文件，按内容核定正式完整名称及同案附件。工作目录与输入目录分开；建批使用原始案件总目录，每案primary_source指向其原始小文件夹中的DOCX。项目书和附件只读，只有主控获准把已验收终稿写入对应目录。二进制DOC需先保留原/转换SHA并确认原案目录映射；不得把内部intake或sources快照目录当交付目录。当前自动路由以原始primary_source父目录为准，无法保持该映射时先解决来源目录，不猜测路径。

selection结构为projects:[{title,source_files:[相对路径],primary_source:相对路径}]，不凭文件名猜标题。正式技术标题按内容核定；交付文件名独立取自原始primary_source父目录完整名称。各案冻结不同目标路径，同名小文件夹在不同父目录可共存；同一小文件夹不能混放多个待撰写项目书。不得截短、清洗或加后缀掩盖目标冲突。重新扫描时识别并排除已有终稿，不将终稿选成新来源。

```text
python scripts/parallel_batch.py scan --input 输入目录 --out 扫描.json
python scripts/parallel_batch.py init --input 输入目录 --work-root 工作目录 --selection 选择.json --controller 本批控制器标识
python scripts/cli_pool.py run --manifest 批次manifest.json --workers 真实总容量 --controller 同一控制器标识
```

init冻结本技能/规则/模型/来源；以后命令自动重定向到快照。三池上限16/8/8、目标32、在制最多64；64GB内存建议最多同时开32个CLI任务，实际容量必须核定并显式传workers。draft→review→revise(需要时)→新会话review；同案一个活动attempt。stage_pool_runner的独立准备/收稿通道和发布通道保持原版，完成即流转补位，通过即放回本案小文件夹，不等全批。真实CLI身份、模型/强度、会话日志和退出证据由cli_evidence校验，配置不证明执行。

手工collaboration通道用reserve --prepare返回的spawn_arguments及worker_context，真实派发后保存dispatch并bind；收稿按worker-receipt，record后立即deliver。命令参数以脚本--help及cli-workers.md为准，不伪造派发证据。draft高、review/revise极高强度沿batch-policy，不能静默换模型。

六项键保留，source_support包含配方/实验数据及原表，formulas包含化学式/单位上下标，figures覆盖全部终图。生化输出契约在原pass和交付门禁接入，不新增模型轮次；源绑定检查不能被旧软通禁词误阻断。总控仍核实际语义、图和全部当前页。改稿后新SHA、新渲染及独立重验，未做not_run。

新批次使用source_case_files策略：建批冻结各案原始primary_source父目录、目录身份和“小文件夹完整名称.docx”，通过后由同一原子发布通道逐案放回。例如“总目录/案件甲/技术项目优化说明书.docx”对应“总目录/案件甲/案件甲.docx”，项目书及样品数据保留。直接输入单案小文件夹时使用该文件夹本身。init及发布均检查同名冲突；已有文件即使内容相同也不冒认、不覆盖，不自动增加终稿、日期或案号后缀。文件夹缺失、替换、链接跳转或同路径多案时停止相关发布并报告。工作记录和待处理说明仍留工作区；发布副本必须与已验收稿SHA一致。旧冻结批次保持原桌面策略，不迁移历史稿。完成后释放其专属worker，不结束共享Office/其他项目进程。

恢复先summary、收已有结果，确认旧进程退出后cancel/重派，保留失败日志，不重算源SHA放行。内部工具缺陷按tool-fault-recovery修复验证并接续，冻结身份异常不放行。无CLI时才按真实子代理容量执行；无法独立审查只能交候选状态，不造pass。旧serial兼容代码保留但新生化批次只走当前三池。
