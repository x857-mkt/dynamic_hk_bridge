import logging
import asyncio
import yaml
import aiofiles
from homeassistant.core import HomeAssistant, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er, label_registry as lr

_LOGGER = logging.getLogger(__name__)
DOMAIN = "dynamic_hk_bridge"
TARGET_FILE_NAME = "homekit_entities.yaml"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.error("🚀 [DHKB] 極簡白名單模式 - 終極防漏版啟動！")
    target_path = hass.config.path(TARGET_FILE_NAME)
    data = {"debounce_task": None}

    def get_current_settings():
        options = dict(entry.options or {})
        return {"show_label": options.get("show_label", "hk_show"), "debounce_time": int(options.get("debounce_time", 5))}

    async def async_execute_sync():
        settings = get_current_settings()
        ent_reg = er.async_get(hass)
        lbl_reg = lr.async_get(hass)
        
        show_label_ids = {settings["show_label"]}
        for label_entry in lbl_reg.async_list_labels():
            if label_entry.name == settings["show_label"] or label_entry.label_id == settings["show_label"]:
                show_label_ids.add(label_entry.label_id)

        final_entities = [eid for eid, ent in ent_reg.entities.items() if (ent.labels & show_label_ids)]
        final_entities = final_entities if final_entities else ["sensor.dhkb_safe_dummy"]

        content = {"include_entities": final_entities}
        
        try:
            async with aiofiles.open(target_path, mode='w', encoding='utf-8') as f:
                await f.write(yaml.dump(content, allow_unicode=True))
        except Exception as e:
            _LOGGER.error(f"❌ [DHKB] 寫入失敗: {e}")

        # 🛡️ 終極防漏機制：直接篡改 HA 內建的 HomeKit UI 設定
        homekit_entries = hass.config_entries.async_entries("homekit")
        for hk_entry in homekit_entries:
            current_options = dict(hk_entry.options or {})
            
            # 撈取 HA HomeKit 的過濾器設定
            filter_dict = current_options.get("filter", {})
            
            # 🔥 強制清空所有網域級別的包含 (封死漏水漏洞)
            filter_dict["include_domains"] = []
            filter_dict["exclude_domains"] = []
            filter_dict["exclude_entities"] = []
            
            # 唯一只信任我們算出來的這份精準清單
            filter_dict["include_entities"] = final_entities
            
            current_options["filter"] = filter_dict
            
            # 寫回系統記憶體
            hass.config_entries.async_update_entry(hk_entry, options=current_options)
            _LOGGER.error(f"🚀 [DHKB] 已強制覆寫並鎖死 HomeKit 實例過濾器: {hk_entry.title}")
        
        # 觸發重載
        await hass.services.async_call("homekit", "reload")
        _LOGGER.error("✨ [DHKB] 成功觸發 HomeKit 重載！")

    async def async_handle_entity_updated(event: Event) -> None:
        if event.data.get("action") == "update":
            if data["debounce_task"] and not data["debounce_task"].done(): 
                data["debounce_task"].cancel()
            
            async def delay_execution():
                # 💡 這裡補回遺漏的 settings 讀取！
                settings = get_current_settings() 
                await asyncio.sleep(settings["debounce_time"])
                await async_execute_sync()
                
            data["debounce_task"] = hass.async_create_task(delay_execution())

    entry.async_on_unload(hass.bus.async_listen("entity_registry_updated", async_handle_entity_updated))
    hass.async_create_task(async_execute_sync())
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True