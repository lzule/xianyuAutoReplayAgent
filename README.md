# 闲鱼客户机器人

这是你的正式项目目录。当前目标是先在 Windows 本地跑通真实闲鱼账号联调，确认能收消息、能自动回复、能转人工提醒，再考虑后续服务器部署。

## 第一版功能

- 接入闲鱼网页登录态，监听客户新消息。
- 根据常见问题自动回复基础咨询。
- 按固定规则报价，不自由乱报价格。
- 根据可预约时间给客户推荐时间。
- 遇到不确定、投诉、退款、关键承诺、特殊要求时转人工。
- 转人工时给客户说明，并通过飞书提醒你。
- 检测到你本人回复后，该会话自动静默，避免机器人抢答。
- 本地后台查看会话、接入状态、转人工记录和预约记录。

## 启动方式

先进入项目目录并激活环境：

```powershell
cd K:\xian\Jetson_BackBend\auto-project\闲鱼客户\xianyu-customer-bot
conda activate xianyu
python app\core\main.py
```

后台默认地址：

```text
http://127.0.0.1:8765
```

如果后台能打开，先看首页的“闲鱼接入状态”。这里会显示 Cookie 是否读取、Token 是否获取成功、消息通道是否连上、最近错误是什么。

## 配置文件

第一次使用时，把 `.env.example` 复制成 `.env`，然后填写：

- `COOKIES_STR`：从浏览器复制的完整闲鱼 Cookie。
- `FEISHU_WEBHOOK`：飞书群机器人地址，不用飞书时可以先留空。
- `USE_SYSTEM_PROXY`：默认 `false`，表示程序不走系统代理。除非你确定必须走代理，否则不要改。

## 如何获取闲鱼 Cookie

1. 用 Edge 或 Chrome 打开 `https://www.goofish.com/`。
2. 登录你的闲鱼账号，并确认页面右上角已经是登录状态。
3. 按 `F12` 打开开发者工具。
4. 进入 `Network`，中文界面一般叫“网络”。
5. 刷新闲鱼页面。
6. 在请求列表里点一个发往 `www.goofish.com` 或 `h5api.m.goofish.com` 的请求。
7. 在右侧找到 `Request Headers`，中文界面一般叫“请求标头”。
8. 找到 `Cookie` 这一行，复制它后面的完整内容。
9. 粘贴到 `.env` 里的 `COOKIES_STR=` 后面。
10. 保存 `.env`，重启程序。

不要复制 `Set-Cookie`，也不要只复制某一个字段。要复制的是请求头里的整条 `Cookie`。

## Cookie 一般长什么样

Cookie 是一整行文本，由很多 `名字=值` 组成，中间用英文分号隔开。大概长这样：

```text
t=...; cna=...; unb=...; cookie2=...; sgcookie=...; _m_h5_tk=xxxx_时间戳; _m_h5_tk_enc=...; tfstk=...
```

比较关键的字段通常包括：

- `_m_h5_tk`
- `unb`
- `cookie2`
- `sgcookie`
- `cna`

如果这些字段缺失，程序很可能无法接入。Cookie 属于账号登录凭证，不要发到公开仓库，也不要贴给不可信的人。

## 业务资料位置

- `configs/pricing/default.yaml`：价格规则。
- `configs/schedule/default.yaml`：可预约时间。
- `configs/handoff/default.yaml`：转人工规则。
- `knowledge/faq/common.yaml`：常见问题。
- `knowledge/services/jetson.yaml`：你的服务说明。
- `knowledge/style/`：后续放你的聊天样本，用来模仿说话风格。

## 当前限制

- 第一版不做 Docker。
- 第一版不做复杂后台。
- 第一版不自动学习你的说话方式，只预留资料入口。
- 第一版不接外部日历。

后续等真实收发消息稳定后，再继续补“更像你的回复风格”和“更细的报价/预约规则”。

## 变更与发布要求

- 每次改动必须新增一条 `docs/changes/YYYY-MM-DD-<topic>.md`。
- 每次改动必须更新 `CHANGELOG.md`。
- 推送前必须执行：

```bash
bash scripts/preflight_check.sh
```

- 隐私数据（真实 Cookie、Webhook、原始聊天）禁止推送到 GitHub。
- 详细流程见：`docs/change-and-release-process.md`
