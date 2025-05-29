# 小智HA桥接组件 (Xiaozhi HA Bridge) 🤖

[![GitHub release](https://img.shields.io/github/release/zhouruhui/xiaozhi-ha-bridge.svg)](https://github.com/zhouruhui/xiaozhi-ha-bridge/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.7%2B-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🎯 **小智AI终端与Home Assistant的完美桥接解决方案**

## 📋 简介

小智HA桥接组件是专为小智AI终端设备开发的Home Assistant自定义组件。它提供了完整的WebSocket桥接服务，让小智终端能够无缝集成Home Assistant的Assist Pipeline，实现：

- 🗣️ **本地语音识别** - 使用HA的STT服务
- 🧠 **智能对话处理** - 集成HA的会话AI
- 🔊 **文本转语音** - 支持多种TTS引擎
- 🏠 **IoT设备控制** - 语音控制智能家居设备
- 🔐 **安全认证** - 支持访问令牌验证

## ✨ 主要特性

| 功能 | 描述 | 状态 |
|------|------|------|
| 🎙️ **完整语音管道** | STT → 对话 → TTS 完整流程 | ✅ |
| 📱 **多设备支持** | 同时连接多个小智终端 | ✅ |
| 🌐 **多语言支持** | 中文、英文等8种语言 | ✅ |
| ⚙️ **易于配置** | 图形化配置界面 | ✅ |
| 🔍 **调试模式** | 详细日志记录 | ✅ |
| 🔐 **访问控制** | Token认证机制 | ✅ |

## 🚀 快速开始

### 1. 通过HACS安装 (推荐)

#### 方法A：自定义存储库
1. 打开HACS → 集成
2. 点击右上角 `⋮` → `自定义存储库`
3. 输入存储库URL：`https://github.com/zhouruhui/xiaozhi-ha-bridge`
4. 类别选择：`Integration`
5. 点击 `添加` → `安装`
6. 重启Home Assistant

#### 方法B：直接下载
1. 下载最新[Release](https://github.com/zhouruhui/xiaozhi-ha-bridge/releases)
2. 解压到 `config/custom_components/xiaozhi_ha_bridge/`
3. 重启Home Assistant

### 2. 添加集成

1. **Home Assistant设置** → **设备与服务**
2. 点击 **添加集成**
3. 搜索 **"小智HA桥接"** 或 **"Xiaozhi HA Bridge"**
4. 按照向导完成配置

### 3. 配置小智终端

在小智终端中配置WebSocket连接：

```json
{
  "websocket": {
    "url": "ws://YOUR_HA_IP:8123/api/xiaozhi_ws",
    "version": 3,
    "token": "YOUR_ACCESS_TOKEN"
  }
}
```

## ⚙️ 配置选项

### 基础配置

| 选项 | 描述 | 默认值 | 必填 |
|------|------|--------|------|
| 服务名称 | 在HA中显示的名称 | "小智HA桥接" | ✅ |
| Assist Pipeline | 语音处理管道 | 默认管道 | ❌ |
| TTS引擎 | 文本转语音引擎 | 默认引擎 | ❌ |
| 语言 | 语音识别语言 | zh-CN | ❌ |

### 高级配置

| 选项 | 描述 | 默认值 | 推荐 |
|------|------|--------|------|
| 调试模式 | 启用详细日志 | False | 开发时启用 |
| 需要访问令牌 | Token认证 | False | ✅ 建议启用 |
| 允许的令牌 | 白名单Token | [] | 生产环境必须 |

## 🔧 进阶配置

### 生成访问令牌

1. **Home Assistant** → **个人资料** → **安全性**
2. 点击 **创建令牌**
3. 输入名称：`xiaozhi_terminal`
4. 复制生成的令牌

### 多实例部署

支持创建多个桥接实例：
- 第一个实例：`/api/xiaozhi_ws`
- 后续实例：`/api/xiaozhi_ws_{entry_id}`

### OTA自动配置

如果使用OTA服务器，更新配置：

```python
# ../OTA/ota_server.py
WEBSOCKET_CONFIG = {
    "url": "ws://192.168.1.100:8123/api/xiaozhi_ws",
    "version": 3,
    "token": "YOUR_LONG_LIVED_ACCESS_TOKEN"
}
```

## 🐛 故障排除

### 常见问题

#### ❌ 组件安装失败
```bash
# 检查HA日志
tail -f home-assistant.log | grep xiaozhi
```
**解决方案**：
- 确认HA版本 ≥ 2024.7.0
- 重启HA后重试
- 检查文件权限

#### ❌ 小智终端无法连接
**检查项目**：
- [ ] WebSocket URL正确
- [ ] 网络连通性
- [ ] 端口8123开放
- [ ] Token有效（如启用认证）

#### ❌ 语音识别不工作
**检查项目**：
- [ ] Assist Pipeline配置
- [ ] 音频格式：OPUS 16kHz
- [ ] 麦克风权限
- [ ] 网络延迟

### 调试模式

启用详细日志记录：

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.xiaozhi_ha_bridge: debug
```

查看关键日志：
```
📱 设备已连接: device_123
🚀 Assist Pipeline 启动: pipeline_id  
🎵 收到音频帧: 1024 bytes
📡 Pipeline事件: stt-start
```

## 📊 系统要求

### Home Assistant
- **版本**: 2024.7.0+
- **组件**: assist_pipeline, tts, conversation, websocket_api

### 小智终端
- **硬件**: ESP32-S3
- **音频**: OPUS编码器
- **固件**: 支持WebSocket Protocol v3

### 网络
- **协议**: WebSocket (ws://)
- **端口**: 8123 (HA默认端口)
- **延迟**: < 100ms (推荐)

## 🤝 贡献指南

欢迎贡献代码！

1. **Fork** 项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 **Pull Request**

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/zhouruhui/xiaozhi-ha-bridge.git

# 软链接到HA
ln -s $(pwd)/custom_components/xiaozhi_ha_bridge ~/.homeassistant/custom_components/

# 重启HA
sudo systemctl restart home-assistant@homeassistant
```

## 📄 许可证

本项目基于 [MIT许可证](LICENSE) 开源。

## 🔗 相关项目

- 🏠 [Home Assistant](https://www.home-assistant.io/)
- 📦 [HACS](https://hacs.xyz/)
- 🤖 [小智AI终端项目](https://github.com/zhouruhui/xiaozhi-my)
- 🔧 [ESPHome语音助手](https://github.com/esphome/wake-word-voice-assistants)

## 📞 支持

- 📚 [文档](https://github.com/zhouruhui/xiaozhi-ha-bridge/wiki)
- 🐛 [问题反馈](https://github.com/zhouruhui/xiaozhi-ha-bridge/issues)
- 💬 [讨论区](https://github.com/zhouruhui/xiaozhi-ha-bridge/discussions)

---

<div align="center">

**🌟 如果这个项目对你有帮助，请给个Star支持一下！**

Made with ❤️ by [zhouruhui](https://github.com/zhouruhui)

</div> 