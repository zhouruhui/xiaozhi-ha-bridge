import voluptuous as vol
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from .websocket_api import async_setup_ws
from .const import (
    DOMAIN, 
    CONF_PIPELINE_ID, 
    CONF_TTS_ENGINE, 
    CONF_LANGUAGE, 
    CONF_DEBUG,
    CONF_REQUIRE_TOKEN,
    CONF_ALLOWED_TOKENS,
    DEFAULT_LANGUAGE,
    DEFAULT_DEBUG,
    DEFAULT_REQUIRE_TOKEN
)

# 配置架构
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_PIPELINE_ID): cv.string,
        vol.Optional(CONF_TTS_ENGINE): cv.string,
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): cv.string,
        vol.Optional(CONF_DEBUG, default=DEFAULT_DEBUG): cv.boolean,
        vol.Optional(CONF_REQUIRE_TOKEN, default=DEFAULT_REQUIRE_TOKEN): cv.boolean,
        vol.Optional(CONF_ALLOWED_TOKENS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }, required=False)
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """设置组件"""
    # 获取配置
    conf = config.get(DOMAIN, {})
    
    # 存储配置到 hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = conf
    hass.data[DOMAIN]["devices"] = {}  # 设备管理器
    
    # 启动 WebSocket 服务
    await async_setup_ws(hass)
    return True 