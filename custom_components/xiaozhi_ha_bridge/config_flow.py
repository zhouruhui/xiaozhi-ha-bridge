import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

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

class XiaozhiHABridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """小智HA桥接组件配置流程"""
    
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        """处理用户配置步骤"""
        errors = {}
        
        if user_input is not None:
            # 验证输入
            try:
                # 检查名称是否已存在
                await self.async_set_unique_id(user_input.get(CONF_NAME, "xiaozhi_ha_bridge"))
                self._abort_if_unique_id_configured()
                
                # 验证pipeline_id（如果提供）
                if user_input.get(CONF_PIPELINE_ID):
                    if not await self._validate_pipeline(user_input[CONF_PIPELINE_ID]):
                        errors[CONF_PIPELINE_ID] = "invalid_pipeline"
                
                if not errors:
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME, "小智HA桥接"),
                        data={
                            CONF_NAME: user_input.get(CONF_NAME, "小智HA桥接"),
                            CONF_PIPELINE_ID: user_input.get(CONF_PIPELINE_ID),
                            CONF_TTS_ENGINE: user_input.get(CONF_TTS_ENGINE),
                            CONF_LANGUAGE: user_input.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                            CONF_DEBUG: user_input.get(CONF_DEBUG, DEFAULT_DEBUG),
                            CONF_REQUIRE_TOKEN: user_input.get(CONF_REQUIRE_TOKEN, DEFAULT_REQUIRE_TOKEN),
                            CONF_ALLOWED_TOKENS: user_input.get(CONF_ALLOWED_TOKENS, []),
                        }
                    )
            except Exception as e:
                errors["base"] = "unknown"
        
        # 获取可用的pipeline列表
        pipelines = await self._get_available_pipelines()
        tts_engines = await self._get_available_tts_engines()
        
        data_schema = vol.Schema({
            vol.Optional(CONF_NAME, default="小智HA桥接"): str,
            vol.Optional(CONF_PIPELINE_ID): vol.In(pipelines) if pipelines else str,
            vol.Optional(CONF_TTS_ENGINE): vol.In(tts_engines) if tts_engines else str,
            vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In([
                "zh-CN", "en-US", "ja-JP", "ko-KR", "de-DE", "fr-FR", "es-ES", "it-IT"
            ]),
            vol.Optional(CONF_DEBUG, default=DEFAULT_DEBUG): bool,
            vol.Optional(CONF_REQUIRE_TOKEN, default=DEFAULT_REQUIRE_TOKEN): bool,
            vol.Optional(CONF_ALLOWED_TOKENS, default=[]): cv.multi_select([]),
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "domain": DOMAIN,
                "docs_url": "https://github.com/zhouruhui/xiaozhi-ha-bridge"
            }
        )

    async def async_step_reconfigure(self, user_input=None):
        """处理重新配置"""
        config_entry = self._get_reconfigure_entry()
        
        if user_input is not None:
            try:
                # 验证pipeline_id（如果提供）
                if user_input.get(CONF_PIPELINE_ID):
                    if not await self._validate_pipeline(user_input[CONF_PIPELINE_ID]):
                        return self.async_show_form(
                            step_id="reconfigure",
                            data_schema=self._get_reconfigure_schema(config_entry, user_input),
                            errors={CONF_PIPELINE_ID: "invalid_pipeline"}
                        )
                
                return self.async_update_reload_and_abort(
                    config_entry,
                    data_updates=user_input
                )
            except Exception:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._get_reconfigure_schema(config_entry, user_input),
                    errors={"base": "unknown"}
                )
        
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._get_reconfigure_schema(config_entry)
        )

    def _get_reconfigure_schema(self, config_entry, defaults=None):
        """获取重新配置的架构"""
        if defaults is None:
            defaults = config_entry.data
            
        return vol.Schema({
            vol.Optional(CONF_PIPELINE_ID, default=defaults.get(CONF_PIPELINE_ID)): str,
            vol.Optional(CONF_TTS_ENGINE, default=defaults.get(CONF_TTS_ENGINE)): str,
            vol.Optional(CONF_LANGUAGE, default=defaults.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)): vol.In([
                "zh-CN", "en-US", "ja-JP", "ko-KR", "de-DE", "fr-FR", "es-ES", "it-IT"
            ]),
            vol.Optional(CONF_DEBUG, default=defaults.get(CONF_DEBUG, DEFAULT_DEBUG)): bool,
            vol.Optional(CONF_REQUIRE_TOKEN, default=defaults.get(CONF_REQUIRE_TOKEN, DEFAULT_REQUIRE_TOKEN)): bool,
        })

    async def _validate_pipeline(self, pipeline_id):
        """验证pipeline ID是否有效"""
        try:
            from homeassistant.components import assist_pipeline
            pipelines = await assist_pipeline.async_get_pipelines(self.hass)
            return pipeline_id in [p.id for p in pipelines]
        except Exception:
            return True  # 如果无法验证，则假设有效

    async def _get_available_pipelines(self):
        """获取可用的pipeline列表"""
        try:
            from homeassistant.components import assist_pipeline
            pipelines = await assist_pipeline.async_get_pipelines(self.hass)
            return {p.id: p.name for p in pipelines}
        except Exception:
            return {}

    async def _get_available_tts_engines(self):
        """获取可用的TTS引擎列表"""
        try:
            # 使用正确的方法获取TTS实体
            from homeassistant.components import tts
            # 获取所有TTS实体而不是调用deprecated API
            tts_entities = self.hass.states.async_all("tts")
            return {entity.entity_id: entity.attributes.get("friendly_name", entity.entity_id) 
                   for entity in tts_entities}
        except Exception:
            return {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """返回选项流程"""
        return XiaozhiHABridgeOptionsFlow()


class XiaozhiHABridgeOptionsFlow(config_entries.OptionsFlow):
    """小智HA桥接组件选项流程"""

    async def async_step_init(self, user_input=None):
        """处理选项配置步骤"""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # 使用新的self.config_entry属性，它由HA自动提供
        current_options = self.config_entry.options or {}
        
        options_schema = vol.Schema({
            vol.Optional(
                CONF_DEBUG,
                default=current_options.get(CONF_DEBUG, DEFAULT_DEBUG)
            ): bool,
            vol.Optional(
                CONF_REQUIRE_TOKEN,
                default=current_options.get(CONF_REQUIRE_TOKEN, DEFAULT_REQUIRE_TOKEN)
            ): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        ) 