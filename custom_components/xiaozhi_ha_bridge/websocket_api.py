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
    def __init__(self, device_id, client_id, ws):
        self.device_id = device_id
        self.client_id = client_id
        self.ws = ws
        self.session_id = str(uuid.uuid4())
        self.status = DEVICE_STATUS_CONNECTED
        self.connected_time = datetime.now()
        self.last_activity = datetime.now()
        self.audio_chunks = []
        
    def update_activity(self):
        self.last_activity = datetime.now()
        
    def set_status(self, status):
        self.status = status
        self.update_activity()

async def async_setup_ws(hass):
    """注册 WebSocket 路由"""
    app = hass.http.app
    app.router.add_route("GET", WS_PATH, lambda req: ws_handler(hass, req))
    _LOGGER.info("🚀 xiaozhi_ha_bridge WebSocket 服务已启动: %s", WS_PATH)

async def ws_handler(hass, request):
    """WebSocket 连接处理"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    # 获取配置
    config = hass.data.get(DOMAIN, {}).get("config", {})
    debug = config.get(CONF_DEBUG, True)
    require_token = config.get(CONF_REQUIRE_TOKEN, False)
    allowed_tokens = config.get(CONF_ALLOWED_TOKENS, [])
    
    device = None
    
    if debug:
        _LOGGER.info("🔗 xiaozhi_ha_bridge: 新的终端连接请求")

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                msg_type = data.get("type")
                
                if debug:
                    _LOGGER.debug("📨 收到消息: %s", data)

                if msg_type == "hello":
                    # 处理握手
                    device = await handle_hello(hass, ws, data, config, debug, require_token, allowed_tokens)
                    if not device:
                        await ws.close()
                        return ws
                        
                elif msg_type == "listen":
                    if device:
                        await handle_listen(hass, ws, device, data, debug)
                        
                elif msg_type == "abort":
                    if device:
                        await handle_abort(hass, ws, device, data, debug)
                        
                # 扩展：IoT设备控制
                elif msg_type == "iot_control":
                    if device:
                        await handle_iot_control(hass, ws, device, data, debug)
                        
            elif msg.type == WSMsgType.BINARY:
                # 收到音频帧
                if device:
                    device.audio_chunks.append(msg.data)
                    device.update_activity()
                    if debug:
                        _LOGGER.debug("🎵 收到音频帧: %d bytes", len(msg.data))
                        
            elif msg.type == WSMsgType.ERROR:
                _LOGGER.error("❌ WebSocket连接异常: %s", ws.exception())
                
    except Exception as e:
        _LOGGER.error("❌ WebSocket处理异常: %s", e)
    finally:
        if device:
            device.set_status(DEVICE_STATUS_DISCONNECTED)
            # 从设备管理器中移除
            devices = hass.data.get(DOMAIN, {}).get("devices", {})
            if device.device_id in devices:
                del devices[device.device_id]
            if debug:
                _LOGGER.info("📱 设备已断开: %s (连接时长: %s)", 
                           device.device_id, 
                           datetime.now() - device.connected_time)
        else:
            if debug:
                _LOGGER.info("🔌 未知设备断开连接")
    return ws

async def handle_hello(hass, ws, data, config, debug, require_token, allowed_tokens):
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
    device = XiaozhiDevice(device_id, client_id, ws)
    
    # 添加到设备管理器
    devices = hass.data.get(DOMAIN, {}).get("devices", {})
    devices[device_id] = device
    
    if debug:
        _LOGGER.info("📱 设备已连接: %s (客户端ID: %s)", device_id, client_id)
    
    # 返回server hello
    response = {
        "type": "hello",
        "session_id": device.session_id,
        "audio_params": {
            "format": "opus",
            "sample_rate": 16000,
            "channels": 1,
            "frame_duration": 60
        },
        "transport": "websocket",
        "server_info": {
            "name": "xiaozhi_ha_bridge",
            "version": "0.1.0",
            "features": ["stt", "tts", "iot_control", "emotion"]
        }
    }
    
    await ws.send_json(response)
    if debug:
        _LOGGER.info("✅ 握手成功: %s", device_id)
    
    return device

async def handle_listen(hass, ws, device, data, debug):
    """处理语音识别消息"""
    state = data.get("state")
    
    if state == "start":
        device.audio_chunks = []
        device.set_status(DEVICE_STATUS_LISTENING)
        await ws.send_json({"type": "listen", "state": "listening"})
        if debug:
            _LOGGER.info("🎤 开始语音识别: %s", device.device_id)
            
    elif state == "stop":
        device.set_status(DEVICE_STATUS_SPEAKING)
        if debug:
            _LOGGER.info("🛑 结束语音识别: %s (音频帧数: %d)", 
                       device.device_id, len(device.audio_chunks))
        
        # 处理音频
        if device.audio_chunks:
            result = await process_audio(hass, device, b"".join(device.audio_chunks), debug)
            
            # 发送识别结果
            await ws.send_json({
                "type": "asr",
                "text": result.get("text", ""),
                "intent": result.get("intent", ""),
                "response": result.get("response", ""),
                "emotion": result.get("emotion", "neutral"),
                "confidence": result.get("confidence", 0.0)
            })
            
            # TTS
            tts_audio = await tts_speak(hass, result.get("response", ""), debug)
            if tts_audio:
                await ws.send_bytes(tts_audio)
                if debug:
                    _LOGGER.info("🔊 TTS音频已发送: %d bytes", len(tts_audio))
        
        device.audio_chunks = []
        device.set_status(DEVICE_STATUS_CONNECTED)

async def handle_abort(hass, ws, device, data, debug):
    """处理中止消息"""
    device.audio_chunks = []
    device.set_status(DEVICE_STATUS_CONNECTED)
    await ws.send_json({"type": "abort", "msg": "会话已中止"})
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

async def process_audio(hass, device, audio_bytes, debug):
    """调用HA Assist Pipeline进行语音识别和意图解析"""
    result = {"text": "", "intent": "", "response": "", "emotion": "neutral", "confidence": 0.0}
    
    try:
        # 获取配置
        config = hass.data.get(DOMAIN, {}).get("config", {})
        pipeline_id = config.get(CONF_PIPELINE_ID)
        language = config.get(CONF_LANGUAGE, "zh-CN")
        
        if debug:
            _LOGGER.info("🧠 开始语音识别处理 (pipeline: %s, 语言: %s)", pipeline_id, language)
        
        # 获取pipeline
        pipeline = await assist_pipeline.async_get_pipeline(hass, pipeline_id)
        
        # 语音识别
        stt_result = await pipeline.stt_stream(
            audio_bytes,
            sample_rate=16000,
            language=language,
            media_format="opus"
        )
        
        text = stt_result.get("text", "")
        result["text"] = text
        result["confidence"] = stt_result.get("confidence", 0.0)
        
        if debug:
            _LOGGER.info("🗣️ 识别结果: '%s' (置信度: %.2f)", text, result["confidence"])
        
        # 意图解析和对话
        if text:
            conversation_result = await conversation.async_converse(
                hass, text, None, language=language
            )
            
            response_text = conversation_result.response.speech.get("plain", {}).get("speech", text)
            result["response"] = response_text
            result["intent"] = conversation_result.response.intent.intent_type if conversation_result.response.intent else ""
            
            # 简单情感分析
            result["emotion"] = analyze_emotion(text, response_text)
            
            if debug:
                _LOGGER.info("💬 对话结果: '%s' (意图: %s, 情感: %s)", 
                           response_text, result["intent"], result["emotion"])
        
    except Exception as e:
        _LOGGER.error("❌ 语音识别失败: %s", e)
        result["response"] = "抱歉，我没有听清楚"
        result["emotion"] = "confused"
    
    return result

async def tts_speak(hass, text, debug):
    """调用HA TTS服务，将文本转为音频（OPUS）"""
    try:
        # 获取配置
        config = hass.data.get(DOMAIN, {}).get("config", {})
        tts_engine = config.get(CONF_TTS_ENGINE)
        language = config.get(CONF_LANGUAGE, "zh-CN")
        
        if debug:
            _LOGGER.info("🎵 开始TTS合成: '%s' (引擎: %s)", text, tts_engine)
        
        tts_result = await tts.async_get_tts_audio(
            hass, 
            engine=tts_engine, 
            message=text, 
            language=language, 
            options={}
        )
        
        if tts_result:
            return tts_result[1]  # 返回音频二进制
            
    except Exception as e:
        _LOGGER.error("❌ TTS失败: %s", e)
    
    return None

def analyze_emotion(input_text, response_text):
    """简单的情感分析"""
    # 这里可以集成更复杂的情感分析模型
    positive_words = ["好", "棒", "谢谢", "开心", "高兴", "喜欢"]
    negative_words = ["不", "坏", "错", "生气", "难过", "讨厌"]
    question_words = ["什么", "怎么", "为什么", "哪里", "谁", "?", "？"]
    
    text = input_text + " " + response_text
    
    if any(word in text for word in question_words):
        return "curious"
    elif any(word in text for word in positive_words):
        return "happy"
    elif any(word in text for word in negative_words):
        return "sad"
    else:
        return "neutral" 