# Xiaozhi Home Assistant Bridge

🤖 **小智AI终端 Home Assistant WebSocket桥接组件**

这是一个Home Assistant自定义组件，用于通过WebSocket协议连接小智AI终端设备，实现本地语音交互和智能家居控制。

## ✨ 功能特性

- 🔌 **WebSocket连接**：与小智AI终端建立实时WebSocket通信
- 🎤 **语音处理**：支持OPUS音频格式的语音识别和合成
- 🏠 **智能家居集成**：与HA Assist Pipeline无缝配合
- 📱 **设备管理**：自动发现和管理小智终端设备
- 🔊 **音频流**：高质量的双向音频传输
- 🛡️ **安全认证**：支持访问令牌验证

## 🎯 版本兼容性

| 组件版本 | 终端固件版本 | Home Assistant版本 | 状态 |
|---------|-------------|-------------------|------|
| v1.0.0  | v1.6.5+     | 2024.1+           | ✅ 稳定 |

## 📋 前置要求

- **Home Assistant** 2024.1 或更新版本
- **小智AI终端** 固件版本 1.6.5 或更新版本
- 本地网络环境（支持WebSocket通信）

## 🚀 安装指南

### 方法1：通过HACS安装（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. 在HACS中添加自定义仓库：
   ```
   https://github.com/zhouruhui/xiaozhi-ha-bridge
   ```
3. 搜索并安装 "Xiaozhi Home Assistant Bridge"
4. 重启Home Assistant

### 方法2：手动安装

1. 下载本仓库的代码
2. 将 `custom_components/xiaozhi_ha_bridge` 文件夹复制到Home Assistant的 `custom_components` 目录
3. 重启Home Assistant

## ⚙️ 配置说明

### 1. 添加集成

在Home Assistant中添加集成：

1. 进入 **设置** → **设备与服务** → **添加集成**
2. 搜索 "Xiaozhi Home Assistant Bridge"
3. 按照向导完成配置

### 2. 配置参数

| 参数 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `host` | WebSocket监听地址 | `0.0.0.0` | ❌ |
| `port` | WebSocket监听端口 | `8123` | ❌ |
| `path` | WebSocket路径 | `/api/xiaozhi_ws` | ❌ |
| `token_required` | 是否需要访问令牌 | `false` | ❌ |

### 3. 终端设备配置

确保你的小智AI终端固件已更新到v1.6.5+，并配置WebSocket地址：

```bash
# 通过串口或OTA配置
websocket_url ws://<HA_IP>:8123/api/xiaozhi_ws
websocket_version 3
```

## 🎵 音频配置

### 支持的音频格式

- **编码格式**：OPUS
- **采样率**：16000 Hz
- **声道数**：单声道（Mono）
- **帧长度**：60ms（推荐）

### 音频流程

```
[小智终端] ━━━ OPUS音频 ━━━▶ [HA Bridge] ━━━ PCM ━━━▶ [Assist Pipeline]
             ◀━━━ OPUS音频 ━━━             ◀━━━ TTS ━━━
```

## 🔧 使用示例

### 自动化配置

```yaml
# automation.yaml
- alias: "小智语音控制客厅灯"
  trigger:
    - platform: state
      entity_id: sensor.xiaozhi_voice_command
  condition:
    - condition: template
      value_template: "{{ '开灯' in trigger.to_state.state }}"
  action:
    - service: light.turn_on
      target:
        entity_id: light.living_room
```

### 脚本配置

```yaml
# scripts.yaml
xiaozhi_tts_announcement:
  alias: "小智语音播报"
  sequence:
    - service: xiaozhi_ha_bridge.send_tts
      data:
        entity_id: sensor.xiaozhi_device
        message: "{{ message }}"
        voice: "xiaomo"
```

## 🛠️ 故障排查

### 常见问题

#### 1. WebSocket连接失败
```
ERROR: WebSocket connection failed
```
**解决方案**：
- 检查终端设备的WebSocket地址配置
- 确认Home Assistant防火墙设置
- 验证网络连通性：`ping <HA_IP>`

#### 2. 音频无响应
```
WARNING: Audio stream timeout
```
**解决方案**：
- 确认音频格式：OPUS 16kHz单声道
- 检查网络延迟（应<50ms）
- 重启Home Assistant和终端设备

#### 3. 设备离线
```
INFO: Device disconnected
```
**解决方案**：
- 检查终端设备WiFi连接
- 确认OTA配置服务器可访问
- 查看终端设备串口日志

### 调试模式

启用调试日志：

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.xiaozhi_ha_bridge: debug
```

## 📊 监控面板

### Lovelace卡片示例

```yaml
# dashboard配置
type: entities
title: 小智AI终端
entities:
  - entity: sensor.xiaozhi_device_status
    name: 设备状态
  - entity: sensor.xiaozhi_audio_quality
    name: 音频质量
  - entity: switch.xiaozhi_voice_assistant
    name: 语音助手
```

## 🔄 版本更新

### v1.0.0 (2025.05.28)
- ✨ 初始版本发布
- ✅ WebSocket协议支持
- ✅ OPUS音频处理
- ✅ 设备自动发现
- ✅ Assist Pipeline集成

## 🤝 贡献指南

欢迎贡献代码！请：

1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 创建Pull Request

## 📝 开发计划

- [ ] 支持多设备同时连接
- [ ] 添加语音命令自定义
- [ ] 集成更多Home Assistant服务
- [ ] 支持设备群组管理
- [ ] 添加音频质量监控

## ⚖️ 许可证

本项目采用 [MIT许可证](LICENSE) 开源。

## 🔗 相关链接

- [小智AI终端项目](https://github.com/78/xiaozhi-esp32) - 终端固件源码
- [Home Assistant文档](https://www.home-assistant.io/docs/) - HA官方文档
- [ESPHome语音助手](https://esphome.io/components/voice_assistant.html) - 参考实现

## 💬 技术支持

- **GitHub Issues**：[提交问题](https://github.com/zhouruhui/xiaozhi-ha-bridge/issues)
- **QQ群**：376893254
- **电子邮件**：your-email@example.com

---

**🎉 享受与小智AI的智能对话体验！** 