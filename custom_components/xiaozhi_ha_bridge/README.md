# 小智HA桥接组件 (Xiaozhi HA Bridge)

[![GitHub release](https://img.shields.io/github/release/zhouruhui/xiaozhi-ha-bridge.svg)](https://github.com/zhouruhui/xiaozhi-ha-bridge/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.7%2B-blue.svg)](https://www.home-assistant.io/)

## 📋 简介

小智HA桥接组件是一个Home Assistant自定义组件，为小智AI终端设备提供与Home Assistant Assist Pipeline的无缝集成。通过WebSocket连接，小智终端可以使用HA的语音识别、对话处理和文本转语音功能，实现完全本地化的语音助手体验。

## ✨ 功能特性

- 🔊 **完整语音管道支持** - 集成HA的STT、对话和TTS服务
- 🎯 **多设备管理** - 支持多个小智终端同时连接
- 🔐 **安全认证** - 支持访问令牌验证
- 🌍 **多语言支持** - 支持中文、英文等多种语言
- 📱 **IoT设备控制** - 通过语音控制HA中的设备
- 🛠️ **易于配置** - 完整的Config Flow支持
- 🔍 **调试模式** - 详细的日志记录功能

## 🚀 版本更新 (v0.2.0)

### 修复的关键问题
- ✅ **修复config_flow.py空文件问题** - 现在提供完整的配置界面
- ✅ **支持Config Entries** - 不再依赖YAML配置
- ✅ **多配置条目支持** - 可以创建多个桥接实例
- ✅ **HACS 2025.1.0兼容性** - 解决deprecated警告
- ✅ **完整的翻译支持** - 中英文界面

### 新增功能
- 🔧 **重新配置支持** - 可以修改现有配置
- 📊 **选项流程** - 高级选项配置
- 🔍 **Pipeline验证** - 自动验证可用的Assist Pipeline
- 🎛️ **TTS引擎选择** - 支持选择不同的TTS引擎

## 📦 安装方法

### 通过HACS安装 (推荐)

1. 在HACS中点击"集成"
2. 点击右上角的三个点，选择"自定义存储库"
3. 添加存储库URL: `https://github.com/zhouruhui/xiaozhi-ha-bridge`
4. 分类选择"Integration"
5. 点击"添加"
6. 在集成列表中找到"Xiaozhi HA Bridge"并安装
7. 重启Home Assistant

### 手动安装

1. 下载最新release
2. 解压到 `config/custom_components/xiaozhi_ha_bridge/`
3. 重启Home Assistant

## ⚙️ 配置

### 1. 添加集成

1. 进入Home Assistant设置 → 设备与服务
2. 点击"添加集成"
3. 搜索"小智HA桥接"或"Xiaozhi HA Bridge"
4. 按照配置流程进行设置

### 2. 配置选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| 服务名称 | 在HA中显示的服务名称 | "小智HA桥接" |
| Assist Pipeline | 使用的语音处理管道 | 默认管道 |
| TTS引擎 | 文本转语音引擎 | 默认引擎 |
| 语言 | 语音识别语言 | zh-CN |
| 调试模式 | 启用详细日志 | False |
| 需要访问令牌 | 是否需要Token认证 | False |
| 允许的访问令牌 | 允许的Token列表 | [] |

### 3. 小智终端配置

小智终端需要配置以下WebSocket连接信息：

```json
{
  "websocket": {
    "url": "ws://YOUR_HA_IP:8123/api/xiaozhi_ws",
    "version": 3,
    "token": "YOUR_ACCESS_TOKEN"
  }
}
```

### 4. OTA服务器配置

如果使用OTA服务器，请更新`../OTA/ota_server.py`中的配置：

```python
WEBSOCKET_CONFIG = {
    "url": "ws://YOUR_HA_IP:8123/api/xiaozhi_ws",
    "version": 3,
    "token": "YOUR_ACCESS_TOKEN"  # 可选
}
```

## 🔧 高级配置

### 多实例支持

可以创建多个桥接实例，每个实例使用不同的WebSocket路径：
- 第一个实例: `/api/xiaozhi_ws`
- 后续实例: `/api/xiaozhi_ws_{entry_id}`

### 访问令牌配置

1. 在HA中生成长期访问令牌
2. 在组件配置中启用"需要访问令牌"
3. 将令牌添加到"允许的访问令牌"列表
4. 在小智终端配置中添加token

### 调试模式

启用调试模式可以查看详细的WebSocket通信日志：

```yaml
logger:
  default: info
  logs:
    custom_components.xiaozhi_ha_bridge: debug
```

## 🎯 使用方法

### 基本语音控制

1. 确保小智终端已连接到HA
2. 说出语音命令，例如：
   - "打开客厅的灯"
   - "关闭空调"
   - "播放音乐"

### 查看连接状态

在Home Assistant中可以查看：
- 连接的设备数量
- 设备状态（已连接/监听中/说话中）
- 连接时间和活动状态

## 🔍 故障排除

### 常见问题

1. **组件加载失败**
   - 确保已重启HA
   - 检查日志中的错误信息
   - 验证文件结构完整

2. **小智终端无法连接**
   - 检查WebSocket URL是否正确
   - 验证网络连接
   - 确认端口8123可访问

3. **语音识别不工作**
   - 检查Assist Pipeline配置
   - 确认麦克风权限
   - 验证音频格式（OPUS 16kHz）

4. **Token认证失败**
   - 确认Token有效且未过期
   - 检查Token是否在允许列表中
   - 验证Token格式正确

### 日志分析

启用调试模式后，查看以下日志：

```
📱 设备已连接: device_123 (客户端ID: client_456, entry: entry_789)
🚀 Assist Pipeline 启动: pipeline_id
🎵 收到音频帧: 1024 bytes
📡 Pipeline事件: stt-start
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

本项目基于MIT许可证开源。

## 🔗 相关链接

- [Home Assistant](https://www.home-assistant.io/)
- [HACS](https://hacs.xyz/)
- [小智AI终端项目](https://github.com/zhouruhui/xiaozhi-my)
- [问题反馈](https://github.com/zhouruhui/xiaozhi-ha-bridge/issues)

---

**注意**: 本组件需要Home Assistant 2024.7或更高版本。 