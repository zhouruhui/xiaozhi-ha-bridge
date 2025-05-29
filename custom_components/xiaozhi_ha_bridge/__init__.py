"""小智HA桥接组件"""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME

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

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """通过配置条目设置组件"""
    
    # 确保域数据存在
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # 合并数据和选项
    config = dict(entry.data)
    config.update(entry.options)
    
    # 存储配置到 hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "config": config,
        "devices": {},  # 设备管理器
        "entry": entry
    }
    
    # 设置调试日志级别
    if config.get(CONF_DEBUG, DEFAULT_DEBUG):
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        _LOGGER.debug("小智HA桥接调试模式已启用")
    
    # 启动 WebSocket 服务
    try:
        await async_setup_ws(hass, entry.entry_id)
        _LOGGER.info("小智HA桥接组件已成功设置: %s", config.get(CONF_NAME, "小智HA桥接"))
    except Exception as e:
        _LOGGER.error("小智HA桥接WebSocket服务启动失败: %s", e)
        return False
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置条目"""
    try:
        # 清理存储的数据
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            entry_data = hass.data[DOMAIN][entry.entry_id]
            
            # 断开所有设备连接
            devices = entry_data.get("devices", {})
            for device in devices.values():
                try:
                    if hasattr(device, 'ws') and device.ws:
                        await device.ws.close()
                except Exception as e:
                    _LOGGER.warning("关闭设备连接时出错: %s", e)
            
            # 移除数据
            del hass.data[DOMAIN][entry.entry_id]
            
            # 如果没有其他条目，清理域数据
            if not hass.data[DOMAIN]:
                del hass.data[DOMAIN]
        
        _LOGGER.info("小智HA桥接组件已成功卸载")
        return True
        
    except Exception as e:
        _LOGGER.error("卸载小智HA桥接组件时出错: %s", e)
        return False

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """重新加载配置条目"""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """更新选项时调用"""
    await async_reload_entry(hass, entry) 