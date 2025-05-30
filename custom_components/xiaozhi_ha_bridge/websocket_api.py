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
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.components.http.const import KEY_AUTHENTICATED

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
    _LOGGER.info("🔍 [DEBUG] async_setup_ws开始: entry_id=%s", entry_id)
    
    app = hass.http.app
    _LOGGER.info("🔍 [DEBUG] 获取到HTTP应用: %s", type(app))
    
    # 创建测试HTTP处理函数
    async def test_handler(request):
        _LOGGER.info("🔍 [DEBUG] test_handler被调用: %s", request.path)
        return web.Response(text="Xiaozhi HA Bridge WebSocket endpoint is working!")
    
    # 创建路由处理函数，绑定entry_id，并绕过认证
    async def ws_handler_wrapper(request):
        _LOGGER.info("🔍 [DEBUG] ws_handler_wrapper被调用: %s", request.path)
        # 标记请求为已认证，绕过HA的认证中间件
        request[KEY_AUTHENTICATED] = True
        return await ws_handler(hass, request, entry_id)
    
    # 总是使用标准路径，避免设备端配置复杂化
    ws_path = WS_PATH
    test_path = ws_path + "/test"
    _LOGGER.info("🔍 [DEBUG] WebSocket路径: %s", ws_path)
    _LOGGER.info("🔍 [DEBUG] 测试路径: %s", test_path)
        
    # 记录现有路由（用于调试）
    existing_routes = []
    for route in app.router.routes():
        if hasattr(route, 'resource'):
            existing_routes.append(route.resource.canonical)
    
    _LOGGER.info("🔍 [DEBUG] 现有路由总数: %d", len(existing_routes))
    _LOGGER.info("🔍 [DEBUG] API相关路由: %s", [r for r in existing_routes if '/api/' in r][:10])
    
    try:
        # 注册测试HTTP端点（不需要认证）
        app.router.add_get(test_path, test_handler)
        _LOGGER.info("🔍 [DEBUG] 测试HTTP端点注册成功: %s", test_path)
        
        # 使用正确的WebSocket路由注册方式
        # 注意：这里不检查重复，让HA的路由系统处理
        app.router.add_get(ws_path, ws_handler_wrapper)
        _LOGGER.info("🔍 [DEBUG] WebSocket路由注册成功: %s", ws_path)
        
        # 验证路由是否真的注册了
        routes_found = {"ws": False, "test": False}
        for route in app.router.routes():
            if hasattr(route, 'resource'):
                if route.resource.canonical == ws_path:
                    routes_found["ws"] = True
                    _LOGGER.info("🔍 [DEBUG] WebSocket路由验证成功: %s", ws_path)
                elif route.resource.canonical == test_path:
                    routes_found["test"] = True
                    _LOGGER.info("🔍 [DEBUG] 测试路由验证成功: %s", test_path)
                
        if not routes_found["ws"]:
            _LOGGER.error("❌ [DEBUG] WebSocket路由注册后验证失败!")
        if not routes_found["test"]:
            _LOGGER.error("❌ [DEBUG] 测试路由注册后验证失败!")
        else:
            _LOGGER.info("✅ [DEBUG] 测试端点可用: http://your-ha-ip:8123%s", test_path)
            
    except Exception as e:
        _LOGGER.error("❌ [DEBUG] 路由注册失败: %s", e, exc_info=True)
        return
            
    _LOGGER.info("🚀 xiaozhi_ha_bridge WebSocket 服务已启动: %s (entry: %s)", ws_path, entry_id or "default")

async def ws_handler(hass, request, entry_id=None):
    """WebSocket 连接处理"""
    
    _LOGGER.info("🔍 [DEBUG] WebSocket连接请求开始处理")
    _LOGGER.info("🔍 [DEBUG] 请求路径: %s", request.path)
    _LOGGER.info("🔍 [DEBUG] 请求方法: %s", request.method)
    _LOGGER.info("🔍 [DEBUG] 请求协议: %s", request.scheme)  # 显示http或https
    _LOGGER.info("🔍 [DEBUG] 远程地址: %s", request.remote)
    _LOGGER.info("🔍 [DEBUG] 用户代理: %s", request.headers.get('User-Agent', 'Unknown'))
    
    # 记录所有headers
    _LOGGER.info("🔍 [DEBUG] 所有请求Headers:")
    for key, value in request.headers.items():
        _LOGGER.info("🔍 [DEBUG]   %s: %s", key, value)
    
    # 检查WebSocket升级
    connection = request.headers.get('Connection', '').lower()
    upgrade = request.headers.get('Upgrade', '').lower()
    _LOGGER.info("🔍 [DEBUG] Connection: %s, Upgrade: %s", connection, upgrade)
    
    if 'upgrade' not in connection or upgrade != 'websocket':
        _LOGGER.error("❌ [DEBUG] 不是有效的WebSocket升级请求")
        return web.Response(status=400, text="Bad Request: Not a WebSocket upgrade")
    
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
    
    _LOGGER.info("🔍 [DEBUG] 配置信息: debug=%s, require_token=%s", debug, require_token)
    
    # 从WebSocket headers中提取小智协议信息
    headers = request.headers
    auth_header = headers.get("Authorization", "")
    protocol_version = headers.get("Protocol-Version", "1")  # 小智协议默认版本1
    device_id = headers.get("Device-Id", "unknown")
    client_id = headers.get("Client-Id", str(uuid.uuid4()))
    
    _LOGGER.info("🔍 [DEBUG] 提取的协议信息:")
    _LOGGER.info("🔍 [DEBUG]   Authorization: %s", auth_header[:20] + "..." if auth_header else "无")
    _LOGGER.info("🔍 [DEBUG]   Protocol-Version: %s", protocol_version)
    _LOGGER.info("🔍 [DEBUG]   Device-Id: %s", device_id)
    _LOGGER.info("🔍 [DEBUG]   Client-Id: %s", client_id)
    
    if debug:
        _LOGGER.info("🔗 小智终端连接: device_id=%s, client_id=%s, protocol_version=%s", 
                    device_id, client_id, protocol_version)
    
    # Token鉴权
    if require_token:
        token = auth_header.replace("Bearer ", "").strip()
        if not token or (allowed_tokens and token not in allowed_tokens):
            _LOGGER.warning("🚫 [DEBUG] 设备鉴权失败: %s", device_id)
            # 直接关闭连接，不允许握手
            return web.Response(status=401, text="Unauthorized")
    
    _LOGGER.info("🔍 [DEBUG] 准备创建WebSocket连接")
    
    # 创建WebSocket连接
    try:
        ws = web.WebSocketResponse()
        _LOGGER.info("🔍 [DEBUG] WebSocket对象创建成功")
        
        await ws.prepare(request)
        _LOGGER.info("🔍 [DEBUG] WebSocket握手prepare完成")
        
    except Exception as e:
        _LOGGER.error("❌ [DEBUG] WebSocket创建失败: %s", e, exc_info=True)
        return web.Response(status=500, text="WebSocket creation failed")
    
    # 创建设备对象
    device = XiaozhiDevice(device_id, client_id, ws, actual_entry_id)
    devices_store[device_id] = device
    
    _LOGGER.info("🔍 [DEBUG] 设备对象创建完成")
    
    if debug:
        _LOGGER.info("📱 小智设备已连接: %s (协议版本: %s, entry: %s)", 
                    device_id, protocol_version, actual_entry_id)

    try:
        _LOGGER.info("🔍 [DEBUG] 开始WebSocket消息循环")
        
        async for msg in ws:
            _LOGGER.info("🔍 [DEBUG] 收到WebSocket消息: type=%s", msg.type)
            
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")
                    
                    _LOGGER.info("🔍 [DEBUG] 解析JSON消息成功: type=%s", msg_type)
                    if debug:
                        _LOGGER.debug("📨 收到消息: %s", data)

                    if msg_type == "hello":
                        # 处理hello握手消息
                        _LOGGER.info("🔍 [DEBUG] 处理hello消息")
                        await handle_hello(hass, ws, device, protocol_version, debug)
                            
                    elif msg_type == "assist_pipeline/run":
                        # Home Assistant Assist Pipeline 兼容协议
                        _LOGGER.info("🔍 [DEBUG] 处理assist_pipeline消息")
                        await handle_assist_pipeline(hass, ws, device, data, debug, config)
                            
                    elif msg_type == "listen":
                        _LOGGER.info("🔍 [DEBUG] 处理listen消息")
                        await handle_listen(hass, ws, device, data, debug, config)
                            
                    elif msg_type == "abort":
                        _LOGGER.info("🔍 [DEBUG] 处理abort消息")
                        await handle_abort(hass, ws, device, data, debug)
                            
                    # 扩展：IoT设备控制
                    elif msg_type == "iot_control":
                        _LOGGER.info("🔍 [DEBUG] 处理iot_control消息")
                        await handle_iot_control(hass, ws, device, data, debug)
                    
                    # 处理ping/pong保持连接
                    elif msg_type == "ping":
                        _LOGGER.info("🔍 [DEBUG] 处理ping消息")
                        await ws.send_json({"type": "pong"})
                        if debug:
                            _LOGGER.debug("🏓 Ping-Pong")
                    else:
                        _LOGGER.warning("🔍 [DEBUG] 未知消息类型: %s", msg_type)
                        
                except json.JSONDecodeError as e:
                    _LOGGER.error("❌ [DEBUG] JSON解析错误: %s", e)
                    await ws.send_json({"type": "error", "message": "Invalid JSON"})
                        
            elif msg.type == WSMsgType.BINARY:
                _LOGGER.info("🔍 [DEBUG] 收到二进制消息: %d bytes", len(msg.data))
                # 收到音频帧 - 处理Assist Pipeline二进制数据
                if device and device.pipeline_handler_id is not None:
                    await handle_binary_audio(hass, ws, device, msg.data, debug)
                        
            elif msg.type == WSMsgType.ERROR:
                _LOGGER.error("❌ [DEBUG] WebSocket连接异常: %s", ws.exception())
                break
                
            elif msg.type == WSMsgType.CLOSE:
                _LOGGER.info("🔍 [DEBUG] WebSocket连接正常关闭")
                break
                
    except Exception as e:
        _LOGGER.error("❌ [DEBUG] WebSocket处理异常: %s", e, exc_info=True)
    finally:
        _LOGGER.info("🔍 [DEBUG] WebSocket连接结束，开始清理")
        
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
    
    _LOGGER.info("🔍 [DEBUG] WebSocket处理完成")
    return ws

async def handle_hello(hass, ws, device, protocol_version, debug):
    """处理hello握手消息"""
    _LOGGER.info("🔍 [DEBUG] handle_hello开始: device_id=%s, protocol_version=%s", 
                device.device_id, protocol_version)
    
    # 按照小智协议返回hello确认
    response = {
        "type": "hello",
        "session_id": device.session_id,
        "protocol_version": protocol_version,
        "audio_settings": {
            "format": "opus",
            "sample_rate": 16000,
            "channels": 1,
            "frame_duration": 60  # 小智协议规定的60ms帧长
        },
        "server_info": {
            "name": "xiaozhi_ha_bridge", 
            "version": "0.2.5",
            "capabilities": ["stt", "tts", "assist_pipeline", "iot_control"]
        },
        "status": "connected"
    }
    
    _LOGGER.info("🔍 [DEBUG] 准备发送hello响应: %s", response)
    
    try:
        await ws.send_json(response)
        _LOGGER.info("🔍 [DEBUG] hello响应发送成功")
        
        if debug:
            _LOGGER.info("✅ 小智协议握手成功: %s (协议版本: %s)", device.device_id, protocol_version)
    except Exception as e:
        _LOGGER.error("❌ [DEBUG] hello响应发送失败: %s", e, exc_info=True)

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