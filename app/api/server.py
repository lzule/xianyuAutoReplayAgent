"""简单本地后台。"""

from __future__ import annotations

import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _html_page() -> str:
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>闲鱼机器人后台</title>
  <style>
    body { font-family: "Microsoft YaHei", sans-serif; margin: 24px; background: #f7f8fa; color: #1f2329; }
    h1 { margin-bottom: 8px; }
    .status-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
    .grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 16px; }
    .card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }
    button { border: 0; padding: 6px 12px; border-radius: 8px; background: #3370ff; color: #fff; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; }
    td, th { padding: 8px; border-bottom: 1px solid #eef1f4; text-align: left; vertical-align: top; }
    .manual { color: #d4380d; font-weight: bold; }
    .auto { color: #389e0d; font-weight: bold; }
    .muted { color: #86909c; }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; }
    .ok { background: #f6ffed; color: #389e0d; }
    .warn { background: #fff7e6; color: #d46b08; }
    .err { background: #fff1f0; color: #cf1322; }
    .mono { font-family: Consolas, monospace; word-break: break-all; }
  </style>
</head>
<body>
  <h1>闲鱼客户机器人后台</h1>
  <p class="muted">这里可以查看最近会话、转人工记录和预约记录，也可以手动切换接管状态。</p>
  <div class="card" style="margin-bottom:16px;">
    <h2>闲鱼接入状态</h2>
    <div id="load-error" class="muted"></div>
    <div id="runtime-status"></div>
    <h3>最近接入事件</h3>
    <div id="runtime-events"></div>
    <h3>本地自检</h3>
    <div id="self-check"></div>
  </div>
  <div class="grid">
    <div class="card">
      <h2>最近会话</h2>
      <div id="conversations"></div>
    </div>
    <div class="card">
      <h2>转人工记录</h2>
      <div id="escalations"></div>
    </div>
    <div class="card">
      <h2>预约记录</h2>
      <div id="appointments"></div>
    </div>
  </div>
  <script>
    async function fetchJson(url, options) {
      const resp = await fetch(url, options);
      return await resp.json();
    }
    async function toggle(chatId, manual) {
      await fetchJson('/api/manual/' + chatId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manual_mode: manual })
      });
      load();
    }
    function renderTable(items, type) {
      if (!items.length) return '<p class="muted">暂无数据</p>';
      if (type === 'conversation') {
        return `<table><tr><th>客户</th><th>状态</th><th>最近消息</th><th>操作</th></tr>${items.map(item => `
          <tr>
            <td>${item.customer_name}<div class="muted">${item.chat_id}</div></td>
            <td><span class="${item.manual_mode ? 'manual' : 'auto'}">${item.manual_mode ? '人工接管' : '自动回复'}</span></td>
            <td>${item.last_message}</td>
            <td>${item.manual_mode
              ? `<button onclick="toggle('${item.chat_id}', false)">恢复自动</button>`
              : `<button onclick="toggle('${item.chat_id}', true)">手动接管</button>`}</td>
          </tr>`).join('')}</table>`;
      }
      return `<table>${items.map(item => `<tr><td>${Object.values(item).join('<br>')}</td></tr>`).join('')}</table>`;
    }
    function badge(value) {
      const lower = String(value || '').toLowerCase();
      const cls = lower === 'ok' || lower === 'true' || lower === 'connected' ? 'ok' :
        (lower.includes('error') || lower.includes('failed') || lower === 'closed' ? 'err' : 'warn');
      return `<span class="badge ${cls}">${value || 'unknown'}</span>`;
    }
    function renderStatus(data) {
      const c = data.connection || {};
      return `
        <div class="status-grid">
          <div><div class="muted">Cookie 已加载</div><div>${badge(c.cookie_loaded ? 'ok' : 'missing')}</div></div>
          <div><div class="muted">闲鱼接入</div><div>${badge(c.xianyu_enabled ? 'enabled' : 'disabled')}</div></div>
          <div><div class="muted">Token 状态</div><div>${badge(c.token_status)}</div></div>
          <div><div class="muted">WebSocket 状态</div><div>${badge(c.websocket_status)}</div></div>
          <div><div class="muted">自动回复</div><div>${badge(c.auto_reply_enabled ? 'enabled' : 'disabled')}</div></div>
          <div><div class="muted">飞书提醒</div><div>${badge(c.feishu_enabled ? 'enabled' : 'disabled')}</div></div>
          <div><div class="muted">最近消息时间</div><div>${c.last_message_at || '暂无'}</div></div>
          <div><div class="muted">断线次数</div><div>${c.disconnect_count ?? 0}</div></div>
        </div>
        <table>
          <tr><th>项目</th><th>内容</th></tr>
          <tr><td>Cookie 长度</td><td>${c.cookie_length ?? 0}</td></tr>
          <tr><td>最近错误</td><td class="mono">${c.last_error || '暂无'}</td></tr>
          <tr><td>最近错误时间</td><td>${c.last_error_at || '暂无'}</td></tr>
          <tr><td>最近原始消息摘要</td><td class="mono">${c.last_raw_message_summary || '暂无'}</td></tr>
          <tr><td>最近跳过原因</td><td class="mono">${c.last_skip_reason || '暂无'}</td></tr>
        </table>
      `;
    }
    function renderEvents(items) {
      if (!items.length) return '<p class="muted">暂无接入事件</p>';
      return `<table><tr><th>时间</th><th>阶段</th><th>状态</th><th>说明</th></tr>${items.map(item => `
        <tr>
          <td>${item.time}</td>
          <td>${item.stage}</td>
          <td>${badge(item.status)}</td>
          <td class="mono">${item.detail}</td>
        </tr>`).join('')}</table>`;
    }
    function renderSelfCheck(check) {
      const rows = [];
      const cookieHealth = check.cookie_health || {};
      const missingFields = cookieHealth.missing_fields || [];
      rows.push(`<tr><td>.env 已加载</td><td>${badge(check.env_loaded ? 'ok' : 'missing')}</td></tr>`);
      rows.push(`<tr><td>Cookie 已读取</td><td>${badge(check.cookie_loaded ? 'ok' : 'missing')}</td></tr>`);
      rows.push(`<tr><td>Cookie 长度</td><td>${check.cookie_length ?? 0}</td></tr>`);
      rows.push(`<tr><td>Cookie 关键字段</td><td>${badge(missingFields.length ? 'missing' : 'ok')} ${missingFields.length ? missingFields.join(', ') : '关键字段齐全'}</td></tr>`);
      rows.push(`<tr><td>Cookie 字段数量</td><td>${cookieHealth.field_count ?? 0}</td></tr>`);
      rows.push(`<tr><td>系统代理</td><td>${check.use_system_proxy ? '使用系统代理' : '不使用系统代理'}</td></tr>`);
      rows.push(`<tr><td>运行目录可写</td><td>${badge(check.runtime_dir_writable ? 'ok' : 'failed')}</td></tr>`);
      rows.push(`<tr><td>数据库路径</td><td class="mono">${check.database_path || '暂无'}</td></tr>`);
      const configRows = (check.config_files || []).map(item => `<div>${item.exists ? 'OK' : 'MISSING'} - <span class="mono">${item.path}</span></div>`).join('');
      rows.push(`<tr><td>配置文件</td><td>${configRows || '暂无'}</td></tr>`);
      return `<table>${rows.join('')}</table>`;
    }
    async function load() {
      const errEl = document.getElementById('load-error');
      try {
        const runtime = await fetchJson('/api/status');
        const conversations = await fetchJson('/api/conversations');
        const escalations = await fetchJson('/api/escalations');
        const appointments = await fetchJson('/api/appointments');
        document.getElementById('runtime-status').innerHTML = renderStatus(runtime);
        document.getElementById('runtime-events').innerHTML = renderEvents(runtime.events || []);
        document.getElementById('self-check').innerHTML = renderSelfCheck(runtime.self_check || {});
        document.getElementById('conversations').innerHTML = renderTable(conversations.items, 'conversation');
        document.getElementById('escalations').innerHTML = renderTable(escalations.items, 'other');
        document.getElementById('appointments').innerHTML = renderTable(appointments.items, 'other');
        errEl.textContent = `最后刷新: ${new Date().toLocaleTimeString()}`;
      } catch (err) {
        errEl.textContent = `页面刷新失败: ${err}`;
      }
    }
    load();
    setInterval(load, 5000);
  </script>
</body>
</html>"""


class AdminServer:
    def __init__(self, host: str, port: int, app_service: "BotApplication") -> None:
        self.host = host
        self.port = port
        self.app_service = app_service
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.logger = logging.getLogger(__name__)

    def start(self) -> None:
        app_service = self.app_service

        class Handler(BaseHTTPRequestHandler):
            def _write_json(self, payload: dict) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/":
                    body = _html_page().encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path == "/api/conversations":
                    self._write_json({"items": app_service.get_conversations()})
                    return
                if self.path == "/api/status":
                    self._write_json(app_service.get_runtime_status())
                    return
                if self.path == "/api/escalations":
                    self._write_json({"items": app_service.get_escalations()})
                    return
                if self.path == "/api/appointments":
                    self._write_json({"items": app_service.get_appointments()})
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:  # noqa: N802
                if self.path.startswith("/api/manual/"):
                    chat_id = self.path.rsplit("/", 1)[-1]
                    length = int(self.headers.get("Content-Length", "0"))
                    body = json.loads(self.rfile.read(length) or b"{}")
                    manual_mode = bool(body.get("manual_mode"))
                    app_service.set_manual_mode(chat_id, manual_mode)
                    self._write_json({"ok": True, "chat_id": chat_id, "manual_mode": manual_mode})
                    return
                if self.path == "/api/debug/simulate":
                    length = int(self.headers.get("Content-Length", "0"))
                    body = json.loads(self.rfile.read(length) or b"{}")
                    result = app_service.simulate_local_message(
                        message_text=str(body.get("message_text", "")).strip(),
                        chat_id=str(body.get("chat_id", "debug-chat")),
                        sender_id=str(body.get("sender_id", "debug-user")),
                        sender_name=str(body.get("sender_name", "本地测试客户")),
                        item_id=str(body.get("item_id", "debug-item")),
                        notify=bool(body.get("notify", False)),
                    )
                    self._write_json({"ok": True, "result": result})
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def log_message(self, format: str, *args: object) -> None:
                return

        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.logger.info("后台已启动: http://%s:%s", self.host, self.port)

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
