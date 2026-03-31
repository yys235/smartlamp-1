# SmartLamp 接入 Home Assistant 实际部署说明

本文不是设计文档，而是面向实际部署的操作说明。

当前推荐链路：

```text
Home Assistant -> smartlamp webapp -> 原灯网关 -> 灯泡
```

## 1. 部署目标

部署完成后，Home Assistant 可以：

- 发现 SmartLamp 自定义集成
- 读取 `webapp` 暴露的网关和灯泡状态
- 将每个灯泡映射为 HA 中的 `light` 实体
- 在 HA 中执行开关、亮度、RGB 控制

## 2. 前提条件

需要满足：

- `webapp` 所在机器能和原灯网关通信
- 原灯网关能正常发现并控制灯泡
- Home Assistant 能通过 HTTP 访问 `webapp`
- Python 版本为 `3.14`
- 已安装 `uv`

建议网络关系：

- `webapp` 与原灯网关放在同一局域网
- Home Assistant 与 `webapp` 之间网络可达
- 如果跨机器部署，尽量给 `webapp` 所在机器固定 IP

## 3. 目录说明

当前仓库中与 HA 对接直接相关的目录：

- `webapp/`
- `custom_components/smartlamp/`
- `docs/home-assistant-integration-design.md`

其中：

- `webapp/` 是运行中的协议适配层
- `custom_components/smartlamp/` 是 HA 自定义集成

## 4. 启动 webapp

在 SmartLamp 项目根目录下执行：

```bash
cd /Users/yys235/projects/smartlamp/webapp
uv sync --group dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8100
```

默认访问地址：

```text
http://127.0.0.1:8100
```

如果 Home Assistant 不在同一台机器上，应改用 `webapp` 所在机器的局域网 IP，例如：

```text
http://192.168.123.20:8100
```

## 5. 建议的环境变量

最小可用配置可以直接启动，不一定需要额外环境变量。

生产或长期运行建议设置：

```bash
export SMART_LAMP_PORT=8100
export SMART_LAMP_API_TOKEN="replace-with-a-long-random-token"
export SMART_LAMP_STALE_GATEWAY_SECONDS=30
```

说明：

- `SMART_LAMP_API_TOKEN`
  用于保护 `/api/*` 接口，HA 配置时需要填写同一令牌
- `SMART_LAMP_STALE_GATEWAY_SECONDS`
  用于网关离线判定，超过该秒数未收到广播则视为离线

如果你不设置 `SMART_LAMP_API_TOKEN`：

- `webapp` API 默认不启用认证
- 更适合纯内网调试
- 不建议暴露给不可信网络

## 6. 启动后先做接口自检

### 6.1 不带认证

```bash
curl http://127.0.0.1:8100/api/system
curl http://127.0.0.1:8100/api/status
```

### 6.2 带认证

```bash
curl -H "Authorization: Bearer replace-with-a-long-random-token" \
  http://127.0.0.1:8100/api/system
```

返回正常时，`/api/system` 应包含：

- `instance_id`
- `version`
- `api_version`
- `auth_enabled`

## 7. 安装 Home Assistant 自定义集成

将下面这个目录复制到 Home Assistant 配置目录：

[custom_components/smartlamp](/Users/yys235/projects/smartlamp/custom_components/smartlamp)

目标路径通常是：

```text
/config/custom_components/smartlamp
```

也就是最终结构应类似：

```text
/config
  custom_components
    smartlamp
      __init__.py
      manifest.json
      config_flow.py
      light.py
      button.py
      ...
```

如果你的 Home Assistant 是容器部署：

- 先确认宿主机上挂载的 HA 配置目录
- 把 `smartlamp` 整个目录复制进去

如果你的 Home Assistant 是 Supervised / HAOS：

- 可以通过 Samba、SSH、File editor 或 VS Code 插件把目录放到 `/config/custom_components/`

## 8. 重启 Home Assistant

复制完自定义集成后，需要重启 Home Assistant。

重启完成后，进入：

```text
设置 -> 设备与服务 -> 添加集成
```

搜索：

```text
SmartLamp
```

## 9. 在 HA 中填写配置

添加集成时，填写：

- `Webapp URL`
- `API token`
- `Scan interval`
- `Request timeout`

推荐值：

- `Webapp URL`: `http://<smartlamp主机IP>:8100`
- `API token`: 与 `SMART_LAMP_API_TOKEN` 一致；如果未设置可留空
- `Scan interval`: `10`
- `Request timeout`: `5`

示例：

```text
Webapp URL: http://192.168.123.20:8100
API token: replace-with-a-long-random-token
Scan interval: 10
Request timeout: 5
```

## 10. 接入成功后的效果

接入成功后：

- 每个网关会在 HA 中显示为一个 device
- 每个灯泡会显示为一个 `light` 实体
- 灯泡控制通过 `webapp` 转发到原灯网关
- 网关级刷新按钮会显示为诊断类 `button` 实体

当前唯一标识规则：

```text
instance_id + gateway_id + device_id
```

这能避免多网关场景下实体冲突。

## 11. 推荐部署方式

### 11.1 单机部署

适合：

- Home Assistant 和 `webapp` 部署在同一台机器

优点：

- 简单
- 网络路径短
- 排错方便

注意：

- 原灯网关广播和 TCP 访问仍然必须能到达这台机器

### 11.2 双机部署

适合：

- Home Assistant 跑在软路由、NAS 或独立主机
- `webapp` 跑在更接近灯网关的 Linux 主机上

优点：

- `webapp` 可以部署在离灯网关最近的网络位置
- HA 不需要理解底层私有协议

注意：

- HA 到 `webapp` 的 HTTP 必须可达
- 建议给 `webapp` 固定 IP

## 12. 建议的 systemd 运行方式

如果 `webapp` 部署在 Linux 主机上，建议用 `systemd` 托管。

示例：

```ini
[Unit]
Description=SmartLamp Webapp
After=network.target

[Service]
Type=simple
User=smartlamp
WorkingDirectory=/opt/smartlamp/webapp
Environment=SMART_LAMP_PORT=8100
Environment=SMART_LAMP_API_TOKEN=replace-with-a-long-random-token
ExecStart=/usr/local/bin/uv run uvicorn app.main:app --host 0.0.0.0 --port 8100
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

部署后：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now smartlamp-webapp.service
sudo systemctl status smartlamp-webapp.service
```

## 13. 常见问题排查

### 13.1 HA 找不到 SmartLamp 集成

检查：

- `custom_components/smartlamp` 是否放到了 HA 配置目录下
- 目录名是否是 `smartlamp`
- `manifest.json` 是否存在
- Home Assistant 是否已重启

### 13.2 HA 能添加集成，但提示无法连接

检查：

- `webapp` 是否已经启动
- `Webapp URL` 是否写成了正确的机器 IP
- HA 机器是否能访问 `http://<webapp-ip>:8100/api/system`
- 防火墙是否放行 `8100`

可以在 HA 主机上直接测试：

```bash
curl http://<webapp-ip>:8100/api/system
```

### 13.3 提示认证失败

检查：

- `SMART_LAMP_API_TOKEN` 是否已经设置
- HA 配置的 `API token` 是否与环境变量一致
- 是否意外带了旧 token

### 13.4 HA 中没有灯泡实体

检查顺序：

1. `webapp` 页面里是否已经能看到网关和灯泡
2. `/api/status` 返回里是否带有 `gateways/current_gateway/lamps`
3. 原灯网关是否真的已经发现到灯泡

如果 `webapp` 自己都看不到灯泡，HA 侧也不会有实体。

### 13.5 网关频繁在线/离线切换

检查：

- 原灯网关广播是否稳定
- `SMART_LAMP_STALE_GATEWAY_SECONDS` 是否设置过小
- 网络是否存在丢包或跨网段广播问题

如有必要，可以先把离线阈值调大：

```bash
export SMART_LAMP_STALE_GATEWAY_SECONDS=60
```

### 13.6 控制命令发出后状态更新慢

这是因为当前链路是：

```text
HA -> webapp -> 网关 -> 灯泡 -> 下一轮刷新
```

可调整：

- HA 的 `Scan interval`
- `webapp` 的确认与刷新参数

但不建议把轮询间隔调得过小，否则会增加局域网设备压力。

## 14. 建议的上线顺序

建议按这个顺序部署：

1. 先确保 `webapp` 页面能正常发现和控制灯泡
2. 再验证 `/api/system` 和 `/api/status`
3. 再安装 HA 自定义集成
4. 最后再做 HA 自动化、场景和语音联动

不要一开始就直接在 HA 里排查底层问题，否则定位会很慢。

## 15. 当前版本边界

当前第一版已经能满足：

- 多网关
- 多灯泡
- 开关
- 亮度
- RGB
- 网关刷新

当前还不包含：

- 自动打包发布为 HACS
- 云端接入
- MQTT 桥接
- 灯泡 effect / transition / 色温能力
- HA 运行环境下的完整端到端集成测试

## 16. 相关文档

- 总体说明：[README.md](/Users/yys235/projects/smartlamp/README.md)
- HA 设计文档：[home-assistant-integration-design.md](/Users/yys235/projects/smartlamp/docs/home-assistant-integration-design.md)
- `webapp` 说明：[webapp/README.md](/Users/yys235/projects/smartlamp/webapp/README.md)
