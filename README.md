# Smart Lamp

面向 Keelight / 乐逗智能灯泡的局域网控制项目，当前仓库包含：

- Java 服务端：原始灯泡控制实现
- Arduino/ESP8266 固件：Blinker / 天猫精灵接入代码
- Python `webapp`：当前主用的 Web 控制端，支持多网关、多灯泡查看与控制

## 当前项目结构

```text
src/        Java 服务端
arduino/    ESP8266 / Arduino 固件
webapp/     Python 3.14 Web 应用
docs/       功能、灯控拆分、HA 接入设计文档
```

## 当前推荐使用方式

当前更推荐直接使用 `webapp` 作为局域网控制入口。

`webapp` 已实现：

- 多网关发现
- 多灯泡查看
- 单灯 / 全灯控制
- RGB 颜色控制
- 亮度控制
- 自动刷新 / 手动刷新切换
- 面向 Home Assistant 接入的 REST API

默认本地访问地址：

```text
http://127.0.0.1:8100
```

## Web App 启动

要求：

- Python 3.14
- `uv`

启动步骤：

```bash
cd webapp
uv sync --group dev
uv run uvicorn app.main:app --host 127.0.0.1 --port 8100
```

如果要改端口，请避开已占用端口。

## 自动化测试

当前自动化测试覆盖 `webapp` 部分。

运行方式：

```bash
cd webapp
uv run pytest
```

当前仓库中的开发约定是：

- 每次代码修改后都要自动运行一次测试
- 如果测试失败，需要继续修复直到通过或明确说明阻塞原因

## 已有文档

- 功能文档：[docs/functional-doc.md](docs/functional-doc.md)
- 灯泡控制功能拆分：[docs/lamp-control-features.md](docs/lamp-control-features.md)
- Home Assistant 接入设计文档：[docs/home-assistant-integration-design.md](docs/home-assistant-integration-design.md)

## Java 服务端说明

`src/` 下保留原始 Java 版本的灯泡控制逻辑，核心能力包括：

- 监听网关 UDP 广播
- 通过 TCP 协议读取灯泡
- 通过 HTTP 接口控制灯泡

该部分适合继续做协议分析或兼容性对照，但当前仓库新增功能主要围绕 `webapp` 进行。

## Arduino / ESP8266 固件说明

`arduino/Ledo.ino` 提供：

- Blinker 对接
- 天猫精灵接入
- 局域网网关发现
- 灯泡状态读取与基础控制

使用前需要填写：

- Blinker 设备密钥
- Wi-Fi SSID
- Wi-Fi 密码

## Home Assistant 接入方向

当前推荐路线不是让 Home Assistant 直接对接底层 UDP/TCP 协议，而是：

1. 保留 `webapp` 作为灯泡控制网关
2. 开发 Home Assistant 自定义集成，通过 REST 调用 `webapp`

详细设计见：

[docs/home-assistant-integration-design.md](docs/home-assistant-integration-design.md)

## 最近更新

本次更新主要包含：

- 新增 Python 3.14 `webapp`
- 支持多网关发现与切换控制
- 优化 Web 页面布局和极端场景显示
- 增加 `pytest` 自动化测试
- 新增 Home Assistant 接入设计文档

## 注意事项

- `webapp` 需要与灯泡网关处于同一局域网
- 当前接口默认用于内网环境，未默认启用认证
- 多网关场景下，实体和控制都应以 `gateway_id + device_id` 作为唯一定位
