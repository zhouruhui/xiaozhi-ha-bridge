# Xiaozhi HA Bridge

本组件为小智AI终端与Home Assistant之间的桥接，支持WebSocket音频流、语音识别、TTS、设备控制等。

## 功能特性

- ✅ **WebSocket音频流**：支持OPUS 16kHz单声道音频
- ✅ **多设备管理**：支持多个小智终端同时连接
- ✅ **语音识别**：集成HA Assist Pipeline
- ✅ **TTS语音合成**：支持多种TTS引擎
- ✅ **IoT设备控制**：通过语音控制HA内设备
- ✅ **情感分析**：简单的情感状态反馈
- ✅ **Token鉴权**：可选的设备身份验证
- ✅ **详细调试**：丰富的日志输出便于调试

## 安装方法

1. 将 `custom_components/xiaozhi_ha_bridge` 目录放入HA的 `custom_components` 目录下。
2. 重启Home Assistant。
3. 配置终端WebSocket地址为 `ws://<HA_IP>:8123/api/xiaozhi_ws`，协议version=3。
4. 终端唤醒后即可与HA语音助手交互。

## 配置选项

在 `configuration.yaml` 中添加以下配置（可选）：

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

## 调试信息

启用调试模式后，组件会输出详细的日志信息：

- 🔗 设备连接/断开
- 📨 消息收发详情
- 🎤 语音识别过程
- 🔊 TTS合成状态
- 🏠 IoT设备控制
- 😊 情感状态分析

查看日志：`设置 → 系统 → 日志`，搜索 `xiaozhi_ha_bridge`

## 支持的消息类型

### 终端 → HA
- `hello`：握手连接
- `listen`：开始/结束语音识别
- `abort`：中止会话
- `iot_control`：IoT设备控制
- 二进制音频帧：OPUS音频数据

### HA → 终端
- `hello`：握手回复
- `asr`：语音识别结果
- `listen`：识别状态
- `abort`：中止确认
- `iot_control`：控制结果
- 二进制音频帧：TTS音频数据

## 扩展功能说明

### 多设备管理
- 支持多个小智终端同时连接
- 每个设备有独立的会话ID和状态管理
- 设备连接时长和活动状态监控

### Token鉴权
- 可选的设备身份验证机制
- 支持多个预设Token
- 防止未授权设备接入

### 情感状态
- 基于对话内容的简单情感分析
- 支持：happy、sad、curious、neutral、confused
- 可扩展集成更复杂的情感分析模型

### IoT控制
- 通过语音直接控制HA内设备
- 支持灯光、插座、空调等常见设备
- 可扩展自定义控制指令

## 依赖要求

- Home Assistant 2023.7及以上
- Assist Pipeline集成
- TTS集成（如Google Translate TTS）

## 故障排除

1. **连接失败**：检查WebSocket地址和端口
2. **语音识别无响应**：检查Assist Pipeline配置
3. **TTS无声音**：检查TTS引擎设置
4. **设备鉴权失败**：检查Token配置

## 参考资料

- [ESPHome Voice Assistant](https://esphome.io/components/voice_assistant.html)
- [HA Assist Pipeline API](https://developers.home-assistant.io/docs/voice_assistants/assist_pipeline/)
- [HA TTS 服务](https://www.home-assistant.io/integrations/tts/)
- [自定义组件开发文档](https://developers.home-assistant.io/docs/creating_component_index/)

## 开发与贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License 