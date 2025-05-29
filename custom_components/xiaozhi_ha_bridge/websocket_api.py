import asyncio
import logging
import json
import uuid
from datetime import datetime
from aiohttp import web, WSMsgType
from homeassistant.components import assist_pipeline
from homeassistant.components import tts
from homeassistant.components import conversation
from homeassistant.helpers import intent
from .const import (
    DOMAIN, 
    WS_PATH, 
    CONF_PIPELINE_ID, 
    CONF_TTS_ENGINE, 
    CONF_LANGUAGE, 
    CONF_DEBUG,
    CONF_REQUIRE_TOKEN,
    CONF_ALLOWED_TOKENS,
    DEVICE_STATUS_CONNECTED,
    DEVICE_STATUS_DISCONNECTED,
    DEVICE_STATUS_LISTENING,
    DEVICE_STATUS_SPEAKING
)

_LOGGER = logging.getLogger(__name__)

class XiaozhiDevice:
    """小智设备管理类"""
    def __init__(self, device_id, client_id, ws, entry_id):
        self.device_id = device_id
        self.client_id = client_id
        self.ws = ws
        self.entry_id = entry_id
        self.session_id = str(uuid.uuid4())
        self.status = DEVICE_STATUS_CONNECTED
        self.connected_time = datetime.now()
        self.last_activity = datetime.now()
        self.pipeline_handler_id = None
        self.current_pipeline = None
        
    def update_activity(self):
        self.last_activity = datetime.now()
        
    def set_status(self, status):
        self.status = status
        self.update_activity()

async def async_setup_ws(hass, entry_id=None):
    """注册 WebSocket 路由"""
    app = hass.http.app
    
    # 创建路由处理函数，绑定entry_id
    async def ws_handler_wrapper(request):
        return await ws_handler(hass, request, entry_id)
    
    # 总是使用标准路径，避免设备端配置复杂化
    ws_path = WS_PATH
        
    # 检查路由是否已经存在，避免重复注册
    for route in app.router.routes():
        if hasattr(route, 'resource') and route.resource.canonical == ws_path:
            _LOGGER.debug("WebSocket路由已存在，跳过注册: %s", ws_path)
            return
            
    app.router.add_route("GET", ws_path, ws_handler_wrapper)
    _LOGGER.info("🚀 xiaozhi_ha_bridge WebSocket 服务已启动: %s (entry: %s)", ws_path, entry_id or "default")

async def ws_handler(hass, request, entry_id=None):
    """WebSocket 连接处理"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    # 获取配置 - 优先使用指定的entry_id，否则使用第一个可用配置
    config = {}
    devices_store = {}
    actual_entry_id = entry_id
    
    if DOMAIN in hass.data:
        if entry_id and entry_id in hass.data[DOMAIN]:
            # 使用指定的配置条目
            entry_data = hass.data[DOMAIN][entry_id]
            config = entry_data.get("config", {})
            devices_store = entry_data.get("devices", {})
            actual_entry_id = entry_id
        else:
            # 使用第一个可用的配置条目
            first_entry_id = next(iter(hass.data[DOMAIN].keys()), None)
            if first_entry_id:
                entry_data = hass.data[DOMAIN][first_entry_id]
                config = entry_data.get("config", {})
                devices_store = entry_data.get("devices", {})
                actual_entry_id = first_entry_id
    
    debug = config.get(CONF_DEBUG, True)
    require_token = config.get(CONF_REQUIRE_TOKEN, False)
    allowed_tokens = config.get(CONF_ALLOWED_TOKENS, [])
    
    device = None
    
    if debug:
        _LOGGER.info("🔗 xiaozhi_ha_bridge: 新的终端连接请求 (entry: %s)", actual_entry_id)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                msg_type = data.get("type")
                
                if debug:
                    _LOGGER.debug("📨 收到消息: %s", data)

                if msg_type == "hello":
                    # 处理握手
                    device = await handle_hello(hass, ws, data, config, debug, require_token, allowed_tokens, devices_store, actual_entry_id)
                    if not device:
                        await ws.close()
                        return ws
                        
                elif msg_type == "assist_pipeline/run":
                    # Home Assistant Assist Pipeline 兼容协议
                    if device:
                        await handle_assist_pipeline(hass, ws, device, data, debug, config)
                        
                elif msg_type == "listen":
                    if device:
                        await handle_listen(hass, ws, device, data, debug, config)
                        
                elif msg_type == "abort":
                    if device:
                        await handle_abort(hass, ws, device, data, debug)
                        
                # 扩展：IoT设备控制
                elif msg_type == "iot_control":
                    if device:
                        await handle_iot_control(hass, ws, device, data, debug)
                        
            elif msg.type == WSMsgType.BINARY:
                # 收到音频帧 - 处理Assist Pipeline二进制数据
                if device and device.pipeline_handler_id is not None:
                    await handle_binary_audio(hass, ws, device, msg.data, debug)
                        
            elif msg.type == WSMsgType.ERROR:
                _LOGGER.error("❌ WebSocket连接异常: %s", ws.exception())
                
    except Exception as e:
        _LOGGER.error("❌ WebSocket处理异常: %s", e)
    finally:
        if device:
            # 清理pipeline
            if device.current_pipeline:
                try:
                    await device.current_pipeline.abort()
                except:
                    pass
            
            device.set_status(DEVICE_STATUS_DISCONNECTED)
            # 从设备管理器中移除
            if device.device_id in devices_store:
                del devices_store[device.device_id]
            if debug:
                _LOGGER.info("📱 设备已断开: %s (连接时长: %s)", 
                           device.device_id, 
                           datetime.now() - device.connected_time)
        else:
            if debug:
                _LOGGER.info("🔌 未知设备断开连接")
    return ws

async def handle_hello(hass, ws, data, config, debug, require_token, allowed_tokens, devices_store, entry_id):
    """处理hello握手消息"""
    device_id = data.get("device_id", "unknown")
    client_id = data.get("client_id", str(uuid.uuid4()))
    
    # Token鉴权
    if require_token:
        auth_header = data.get("authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if not token or (allowed_tokens and token not in allowed_tokens):
            if debug:
                _LOGGER.warning("🚫 设备鉴权失败: %s", device_id)
            await ws.send_json({"type": "error", "message": "鉴权失败"})
            return None
    
    # 创建设备对象
    device = XiaozhiDevice(device_id, client_id, ws, entry_id)
    
    # 添加到设备管理器
    devices_store[device_id] = device
    
    if debug:
        _LOGGER.info("📱 设备已连接: %s (客户端ID: %s, entry: %s)", device_id, client_id, entry_id)
    
    # 返回server hello - 兼容ESPHome语音助手格式
    response = {
        "type": "hello",
        "session_id": device.session_id,
        "audio_settings": {
            "format": "opus",
            "sample_rate": 16000,
            "channels": 1,
            "frame_duration": 60
        },
        "protocol_version": "1.0",
        "server_info": {
            "name": "xiaozhi_ha_bridge",
            "version": "0.2.0",
            "capabilities": ["stt", "tts", "assist_pipeline", "iot_control"]
        }
    }
    
    await ws.send_json(response)
    if debug:
        _LOGGER.info("✅ 握手成功: %s", device_id)
    
    return device

async def handle_assist_pipeline(hass, ws, device, data, debug, config):
    """处理Home Assistant Assist Pipeline请求"""
    try:
        pipeline_id = data.get("pipeline") or config.get(CONF_PIPELINE_ID)
        start_stage = data.get("start_stage", "stt")
        end_stage = data.get("end_stage", "tts")
        conversation_id = data.get("conversation_id")
        device_id = data.get("device_id", device.device_id)
        
        # 使用更新的Assist Pipeline API
        try:
            # 尝试使用新的API
            runner_data = await assist_pipeline.async_pipeline_from_audio_stream(
                hass,
                event_callback=lambda event: handle_pipeline_event(ws, device, event, debug),
                stt_metadata=assist_pipeline.SpeechMetadata(
                    language=config.get(CONF_LANGUAGE, "zh-CN"),
                    format=assist_pipeline.AudioFormats.OPUS,
                    codec=assist_pipeline.AudioCodecs.OPUS,
                    bit_rate=assist_pipeline.AudioBitRates.BITRATE_16,
                    sample_rate=assist_pipeline.AudioSampleRates.SAMPLERATE_16000,
                    channel=assist_pipeline.AudioChannels.CHANNEL_MONO,
                ),
                pipeline_id=pipeline_id,
                conversation_id=conversation_id,
                device_id=device_id,
                tts_audio_output="raw",
            )
        except AttributeError:
            # 如果新API不存在，回退到简化版本
            _LOGGER.warning("使用简化的Assist Pipeline实现（旧版本兼容）")
            # 简化的实现 - 直接调用对话服务
            response = await conversation.async_converse(
                hass, 
                text=data.get("text", ""), 
                conversation_id=conversation_id,
                device_id=device_id,
                language=config.get(CONF_LANGUAGE, "zh-CN")
            )
            
            # 发送对话响应
            await ws.send_json({
                "type": "conversation-response",
                "data": {
                    "response": response.response.speech.get("plain", {}).get("speech", ""),
                    "conversation_id": response.conversation_id
                }
            })
            return
        
        device.current_pipeline = runner_data
        device.pipeline_handler_id = getattr(runner_data, 'stt_binary_handler_id', 1)
        
        # 发送run-start事件
        await ws.send_json({
            "type": "run-start",
            "data": {
                "pipeline": pipeline_id,
                "language": config.get(CONF_LANGUAGE, "zh-CN"),
                "runner_data": {
                    "stt_binary_handler_id": device.pipeline_handler_id,
                    "timeout": data.get("timeout", 300)
                }
            }
        })
        
        if debug:
            _LOGGER.info("🚀 Assist Pipeline 启动: %s", pipeline_id)
            
    except Exception as e:
        _LOGGER.error("❌ Assist Pipeline 启动失败: %s", e)
        await ws.send_json({
            "type": "error",
            "data": {
                "code": "pipeline-start-failed",
                "message": str(e)
            }
        })

async def handle_binary_audio(hass, ws, device, binary_data, debug):
    """处理二进制音频数据"""
    if not device.current_pipeline:
        return
        
    try:
        # 检查是否是结束标记（单字节）
        if len(binary_data) == 1:
            # 音频流结束
            await device.current_pipeline.end_stream()
            if debug:
                _LOGGER.info("🎵 音频流结束")
        else:
            # 提取handler_id和音频数据
            handler_id = binary_data[0]
            audio_data = binary_data[1:]
            
            if handler_id == device.pipeline_handler_id:
                await device.current_pipeline.receive_audio(audio_data)
                if debug:
                    _LOGGER.debug("🎵 收到音频帧: %d bytes", len(audio_data))
                    
    except Exception as e:
        _LOGGER.error("❌ 音频处理失败: %s", e)

async def handle_pipeline_event(ws, device, event, debug):
    """处理pipeline事件"""
    try:
        event_type = event.type
        
        if debug:
            _LOGGER.debug("📡 Pipeline事件: %s", event_type)
        
        # 转发事件到客户端
        await ws.send_json({
            "type": event_type,
            "data": event.data if hasattr(event, 'data') else {}
        })
        
        # 特殊处理某些事件
        if event_type == "run-end":
            device.current_pipeline = None
            device.pipeline_handler_id = None
            device.set_status(DEVICE_STATUS_CONNECTED)
            
        elif event_type == "stt-start":
            device.set_status(DEVICE_STATUS_LISTENING)
            
        elif event_type == "tts-start":
            device.set_status(DEVICE_STATUS_SPEAKING)
            
    except Exception as e:
        _LOGGER.error("❌ Pipeline事件处理失败: %s", e)

async def handle_listen(hass, ws, device, data, debug, config):
    """处理旧版listen消息（向后兼容）"""
    state = data.get("state")
    
    if state == "start":
        # 转换为新的assist_pipeline格式
        await handle_assist_pipeline(hass, ws, device, {
            "type": "assist_pipeline/run",
            "start_stage": "stt",
            "end_stage": "tts",
            "input": {
                "sample_rate": 16000
            }
        }, debug, config)
        
    elif state == "stop":
        # 发送音频结束标记
        if device.pipeline_handler_id:
            await ws.send_bytes(bytes([device.pipeline_handler_id]))

async def handle_abort(hass, ws, device, data, debug):
    """处理中止消息"""
    if device.current_pipeline:
        await device.current_pipeline.abort()
        device.current_pipeline = None
        device.pipeline_handler_id = None
    
    device.set_status(DEVICE_STATUS_CONNECTED)
    await ws.send_json({"type": "abort", "message": "会话已中止"})
    if debug:
        _LOGGER.info("⏹️ 会话中止: %s", device.device_id)

async def handle_iot_control(hass, ws, device, data, debug):
    """处理IoT设备控制"""
    try:
        command = data.get("command", "")
        entity_id = data.get("entity_id", "")
        
        if debug:
            _LOGGER.info("🏠 IoT控制请求: %s -> %s", command, entity_id)
        
        # 调用HA服务
        domain, service = command.split(".", 1) if "." in command else ("homeassistant", command)
        service_data = {"entity_id": entity_id}
        
        await hass.services.async_call(domain, service, service_data)
        
        await ws.send_json({
            "type": "iot_control", 
            "status": "success",
            "message": f"已执行: {command}"
        })
        
        if debug:
            _LOGGER.info("✅ IoT控制成功: %s", command)
            
    except Exception as e:
        _LOGGER.error("❌ IoT控制失败: %s", e)
        await ws.send_json({
            "type": "iot_control", 
            "status": "error",
            "message": str(e)
        }) 