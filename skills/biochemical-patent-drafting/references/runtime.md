# DOCX运行环境与页面验收

公开分享包保留匿名样本结构统计及已清洗的五分区模板；不含原始题名、原件哈希、技术项目书、人工终稿、实验数据或图片。runtime.json保持空配置，必须在新电脑探测并验证Python、文档渲染器、WPS或LibreOffice、Poppler和字体后填写；安装技能不等于环境就绪。未配置时预检会拒绝运行。

每批一次核验本机[运行配置](runtime.json)。先由依赖加载器取得真实Python与文档工具，检查python-docx、lxml、Pillow、pypdf、pdf2image和Poppler。配置中的路径、程序哈希、字体文件及后端身份属于当前机器；换机或升级后重新探测、核验并用小样实测，不能复制旧机器路径或凭程序名称认定成功。分享包的空白配置须完成设置才能运行。

|转换后端|需核实的配置|
|---|---|
|WPS|conversion_backend=wps；wps_program及其SHA；匹配位数的wps_powershell及其SHA；wps_progid缺省KWPS.Application|
|LibreOffice|conversion_backend=libreoffice；libreoffice及其SHA；官方documents渲染器renderer|
|共同依赖|python、poppler_dir、font_files中实际数学/正文/标题字体文件；不改变系统PATH或共享Office设置|

使用已配置的文档Python执行：

```text
python scripts/render_docx_checked.py --preflight
python scripts/render_docx_checked.py 当前稿.docx --output-dir 本attempt/render-r1 --reuse --compact
python scripts/render_docx_checked.py 当前稿.docx --output-dir 本attempt/render-r1 --verify --compact
```

预检只证明依赖可用；首次配置或环境变化必须实际渲染并查看小样。普通批次先核内容，有明确待改项先修改；内容可通过时由review渲染当前稿，或复用当前作者目录下的有效同稿证据。`--reuse`仅在输入路径及字节、工具/配置/字体/DPI指纹和全部产物一致时生效。改稿使用新渲染目录，不覆盖旧证据；检查器成功不代表语义或页面通过。

render.json绑定当前DOCX的SHA、实际转换程序、PDF、连续page-N.png及各自哈希；PDF页数须等于PNG数量。生成状态为rendered_pending_visual_review。review须验证这些身份并实看全部当前页，或按冻结增量复查规则继承已实看的同图页面；未查看的页面不能签发通过。标题边框、表格跨页、公式字形、正文分页等以真实页面为准，不用HTML或截图拼接替代Word渲染。

WPS导出跨批次串行，模型撰写等阶段可继续并行。仅打开本次唯一临时副本且只读，仅关闭本次Document；不更改Visible/DisplayAlerts，不退出或按名称终止共享WPS/Office进程。LibreOffice仅对子进程设置已验证工具PATH，并使用独立临时用户配置。后端失败时保留明确失败状态，不静默切换或降低模型强度。

发现缺字、问号、粗斜体或OMML异常，先核源结构与同一哈希DOCX的实际显示，区分稿件错误和转换器失真；不能为迁就渲染而改公式含义。需要兼容后端时，先核其程序身份和配置再重新生成同稿证据，不能借用另一稿或旧哈希的页面。

失败日志保留在本次输出目录：render.json、renderer.log，或WPS的converter.stdout.txt、converter.stderr.txt、converter-result.json及rasterizer.log。超时只处理本次创建的helper，先按唯一副本路径检查可能遗留的只读文档，不反复启动转换或终止共享应用。保留未通过稿件，按[恢复规范](tool-fault-recovery.md)修复后继续。