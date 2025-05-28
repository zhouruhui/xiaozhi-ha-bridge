# Xiaozhi HA Bridge

[![GitHub release](https://img.shields.io/github/release/zhouruhui/xiaozhi-ha-bridge.svg)](https://github.com/zhouruhui/xiaozhi-ha-bridge/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/zhouruhui/xiaozhi-ha-bridge.svg)](LICENSE)

小智AI终端与Home Assistant之间的桥接组件，支持WebSocket音频流、语音识别、TTS、设备控制等功能。

## 项目概述

本项目为 [小智AI聊天机器人](https://github.com/78/xiaozhi-esp32) 提供与 Home Assistant 的集成方案，让小智终端可以直接与 HA 的语音助手交互，实现本地化的语音控制。

### 主要特性

- 🎤 **语音识别**：集成HA Assist Pipeline，支持多语言
- 🔊 **TTS语音合成**：支持多种TTS引擎
- 🏠 **IoT设备控制**：通过语音直接控制HA内设备
- 📱 **多设备管理**：支持多个小智终端同时连接
- 🔐 **Token鉴权**：可选的设备身份验证
- 😊 **情感分析**：简单的情感状态反馈
- 🐛 **详细调试**：丰富的日志输出便于调试

## 安装方法

### 方法1: HACS安装（推荐）

1. 在HACS中添加自定义仓库：`https://github.com/zhouruhui/xiaozhi-ha-bridge`
2. 搜索 "Xiaozhi HA Bridge" 并安装
3. 重启Home Assistant

### 方法2: 手动安装

1. 下载本仓库
2. 将 `custom_components/xiaozhi_ha_bridge` 目录复制到HA的 `custom_components` 目录下
3. 重启Home Assistant

## 配置说明

### HA端配置

在 `configuration.yaml` 中添加配置（可选）：

```yaml
xiaozhi_ha_bridge:
  pipeline_id: "01234567-89ab-cdef-0123-456789abcdef"  # 指定Assist Pipeline ID
  tts_engine: "tts.google_translate"                   # 指定TTS引擎
  language: "zh-CN"                                    # 语言设置
  debug: true                                          # 调试模式
  require_token: false                                 # 是否需要Token鉴权
  allowed_tokens:                                      # 允许的Token列表
    - "your-secret-token-1"
    - "your-secret-token-2"
```

### 终端配置

配置小智终端连接到HA：

#### 通过串口命令
```bash
set websocket url ws://192.168.1.100:8123/api/xiaozhi_ws
set websocket version 3
```

#### 通过OTA配置
```json
{
  "websocket": {
    "url": "ws://192.168.1.100:8123/api/xiaozhi_ws",
    "version": 3
  }
}
```

## 使用方法

1. 确保HA已安装并配置好Assist Pipeline和TTS服务
2. 安装本组件并重启HA
3. 配置小智终端连接到HA的WebSocket服务
4. 唤醒小智终端，开始语音交互

## 调试信息

启用调试模式后，可在HA日志中看到详细信息：

- 🔗 设备连接/断开状态
- 📨 消息收发详情
- 🎤 语音识别过程
- 🔊 TTS合成状态
- 🏠 IoT设备控制结果
- 😊 情感状态分析

查看方法：`设置 → 系统 → 日志`，搜索 `xiaozhi_ha_bridge`

## 支持的功能

### 语音交互
- 语音识别（STT）
- 意图理解
- 对话生成
- 语音合成（TTS）

### 设备控制
- 灯光控制
- 插座开关
- 空调控制
- 其他HA设备

### 扩展功能
- 多设备并发
- 情感状态反馈
- Token安全验证
- 详细日志调试

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 连接失败 | 检查WebSocket地址和端口，确认网络连通性 |
| 语音识别无响应 | 检查Assist Pipeline配置，确认音频格式 |
| TTS无声音 | 检查TTS引擎设置，查看相关日志 |
| 设备鉴权失败 | 检查Token配置，确认终端Token正确 |

## 技术架构

```
[小智终端] --WebSocket+OPUS音频--> [HA Bridge组件] --API--> [HA语音助手/设备控制]
         <----------------TTS音频-------------------/
```

## 依赖要求

- Home Assistant 2023.7及以上
- Assist Pipeline集成
- TTS集成（如Google Translate TTS）
- 小智AI终端固件

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 许可证

本项目采用MIT许可证，详见 [LICENSE](LICENSE) 文件。

## 相关项目

- [小智AI聊天机器人](https://github.com/78/xiaozhi-esp32) - ESP32终端固件
- [ESPHome Voice Assistant](https://esphome.io/components/voice_assistant.html) - 参考实现
- [Home Assistant](https://www.home-assistant.io/) - 智能家居平台

## 支持

如有问题或建议，请：

1. 查看 [Issues](https://github.com/zhouruhui/xiaozhi-ha-bridge/issues)
2. 提交新的Issue
3. 加入讨论群组

---

**让小智与你的智能家居无缝连接！** 🏠✨ 