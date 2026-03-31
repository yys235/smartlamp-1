# Smart Lamp Web App

独立的 Python 3.14 Web 应用，提供：

- 灯泡网关自动发现
- 灯泡状态查看
- Web 端全灯控制
- Web 端单灯控制
- Web 端颜色与亮度设置
- 多网关查看与切换
- 面向 Home Assistant 的 REST API
- 可选 API 令牌认证

## 运行方式

```bash
cd webapp
uv sync --group dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

浏览器访问：

```text
http://127.0.0.1:8100
```

## 环境变量

- `SMART_LAMP_HOST`：默认 `0.0.0.0`
- `SMART_LAMP_PORT`：默认 `8100`
- `SMART_LAMP_UDP_PORT`：默认 `41328`
- `SMART_LAMP_TCP_PORT`：默认 `41330`
- `SMART_LAMP_DISCOVERY_TIMEOUT`：默认 `3.0`
- `SMART_LAMP_TCP_TIMEOUT`：默认 `5.0`
- `SMART_LAMP_STALE_GATEWAY_SECONDS`：默认 `30.0`
- `SMART_LAMP_CONFIRM_DELAY`：默认 `1.0`
- `SMART_LAMP_REFRESH_AFTER_WRITE`：默认 `true`
- `SMART_LAMP_INSTANCE_ID`：默认按主机和部署路径生成
- `SMART_LAMP_API_TOKEN`：默认未设置，设置后 `/api/*` 需要认证

## Home Assistant 对接

当前仓库已经提供第一版 HA 自定义集成：

```text
custom_components/smartlamp/
```

`webapp` 已新增这些对接接口：

- `GET /api/system`
- `GET /api/status`
- `GET /api/gateways`
- `GET /api/gateways/{gateway_id}`
- `POST /api/gateways/{gateway_id}/lamps/refresh`
- `POST /api/gateways/{gateway_id}/lamps/{device_id}/on`
- `POST /api/gateways/{gateway_id}/lamps/{device_id}/off`

认证支持：

- `Authorization: Bearer <token>`
- `X-API-Key: <token>`

## 测试

```bash
cd webapp
uv run pytest
```
