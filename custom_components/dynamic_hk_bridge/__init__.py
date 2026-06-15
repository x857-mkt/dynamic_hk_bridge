import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

class DynamicHKBridgeConfigFlow(config_entries.ConfigFlow, domain="dynamic_hk_bridge"):
    """處理初次安裝時的設定流"""
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        # 防止重複安裝
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Apple Home 動態標籤橋接", 
                data=user_input
            )

        # 初始安裝欄位
        data_schema = vol.Schema({
            vol.Required("show_label", default="hk_show"): str,
            vol.Required("hide_label", default="hk_hide"): str,
            vol.Required("debounce_time", default=5): int,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """建立選項流實例"""
        return DynamicHKBridgeOptionsFlowHandler(config_entry)


class DynamicHKBridgeOptionsFlowHandler(config_entries.OptionsFlow):
    """處理點擊『設定 (Options)』後的選單異動，具備高相容性防禦機制"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """初始化選項流，全面相容新舊版 HA 核心核心"""
        try:
            # 嘗試以新版 HA 規格初始化（建構子需傳入 config_entry）
            super().__init__(config_entry)
        except TypeError:
            # 若失敗，則退回舊版 HA 規格初始化
            super().__init__()
        
        #self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """選項選單的初始步驟"""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # 1. 安全提取現有設定，防止任何 AttributeError 導致 500 錯誤
        current_options = {}
        if hasattr(self, "config_entry") and self.config_entry:
            current_options = dict(self.config_entry.options or self.config_entry.data or {})
        
        # 2. 【核心修復】強制轉換型態，徹底防止 Voluptuous 驗證預設值時崩潰
        default_show = str(current_options.get("show_label", "hk_show"))
        default_hide = str(current_options.get("hide_label", "hk_hide"))
        try:
            default_debounce = int(current_options.get("debounce_time", 5))
        except (ValueError, TypeError):
            default_debounce = 5

        _LOGGER.debug(
            "[DHKB] 載入設定選單成功。目前數值: show=%s, hide=%s, debounce=%d", 
            default_show, default_hide, default_debounce
        )

        # 3. 建立嚴謹的安全 Schema
        options_schema = vol.Schema({
            vol.Required("show_label", default=default_show): str,
            vol.Required("hide_label", default=default_hide): str,
            vol.Required("debounce_time", default=default_debounce): int,
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)