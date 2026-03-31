# Smart Lamp Web App

独立的 Python 3.14 Web 应用，提供：

- 灯泡网关自动发现
- 灯泡状态查看
- Web 端全灯控制
- Web 端单灯控制
- Web 端颜色与亮度设置

## 运行方式

```bash
cd webapp
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

浏览器访问：

```text
http://127.0.0.1:8000
```

## 环境变量

- `SMART_LAMP_HOST`：默认 `0.0.0.0`
- `SMART_LAMP_PORT`：默认 `8000`
- `SMART_LAMP_UDP_PORT`：默认 `41328`
- `SMART_LAMP_TCP_PORT`：默认 `41330`
- `SMART_LAMP_DISCOVERY_TIMEOUT`：默认 `3.0`
- `SMART_LAMP_TCP_TIMEOUT`：默认 `5.0`
- `SMART_LAMP_CONFIRM_DELAY`：默认 `1.0`
- `SMART_LAMP_REFRESH_AFTER_WRITE`：默认 `true`
