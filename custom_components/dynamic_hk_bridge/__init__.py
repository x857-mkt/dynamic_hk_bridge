import logging
import asyncio
import yaml
from homeassistant.core import HomeAssistant, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er, label_registry as lr

_LOGGER = logging.getLogger(__name__)
DOMAIN = "dynamic_hk_bridge"
TARGET_FILE_NAME = "homekit_entities.yaml"

# 我們不需要透過整合來「建立」實體，所以直接保持空白，避免底層衝突
PLATFORMS = []

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.error("🚀 [DHKB] 極簡純白名單模式已成功啟動！")

    target_path = hass.config.path(TARGET_FILE_NAME)
    data = {"debounce_task": None}

    def get_current_settings():
        options = dict(entry.options or {})
        if not options:
            options = dict(entry.data or {})
        return {
            "show_label": options.get("show_label", "hk_show"),
            "debounce_time": int(options.get("debounce_time", 5))
        }

    async def async_execute_sync():
        settings = get_current_settings()
        show_label_target = settings["show_label"]

        ent_reg = er.async_get(hass)
        lbl_reg = lr.async_get(hass)

        # 同時兼容 label_id 與標籤名稱
        show_label_ids = {show_label_target}
        for label_entry in lbl_reg.async_list_labels():
            if label_entry.name == show_label_target or label_entry.label_id == show_label_target:
                show_label_ids.add(label_entry.label_id)

        show_entities = []

        # 全域實體掃描
        for entity_id, entity_entry in ent_reg.entities.items():
            entity_labels = entity_entry.labels if hasattr(entity_entry, "labels") else getattr(entity_entry, "labels", set())
            if not entity_labels:
                entity_labels = set()

            if entity_labels & show_label_ids:
                show_entities.append(entity_id)

        total_show = len(show_entities)
        _LOGGER.error(f"🔍 [DHKB] 極簡計算：具備 {show_label_target} 的總數: {total_show}")

        final_entities = show_entities

        # 🛡️ 核彈防護罩：如果是空的，塞入虛擬實體防止 HomeKit 暴走全開
        if total_show == 0:
            _LOGGER.error("⚠️ [DHKB] 警告：白名單為空！已啟動防護機制，注入虛擬實體以阻擋 HomeKit 全開。")
            final_entities = ["sensor.dhkb_safe_dummy"]
        else:
            _LOGGER.error(f"📌 [DHKB] 準備放行的實體有：{', '.join(final_entities)}")

        # 寫入 YAML
        yaml_data = {"filter": {"include_entities": final_entities}}
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            _LOGGER.error(f"❌ [DHKB] 寫入失敗: {str(e)}")

        # 強制注入原生 HomeKit 並重載
        hk_reg = hass.data.get("homekit")
        if hk_reg and isinstance(hk_reg, dict):
            for hk_key, hk_instance in hk_reg.items():
                if hasattr(hk_instance, "instance") and hk_instance.instance:
                    hk_instance.instance.file_include_entities = final_entities
                    _LOGGER.error(f"🚀 [DHKB] 已將過濾清單強制灌入: {hk_key}")

        try:
            await hass.services.async_call("homekit", "reload")
            _LOGGER.error("✨ [DHKB] 成功觸發 HomeKit 重載！")
        except Exception as e:
            _LOGGER.error(f"❌ [DHKB] 重載失敗: {str(e)}")

    async def async_handle_entity_updated(event: Event) -> None:
        action = event.data.get("action")
        if action != "update":
            return

        settings = get_current_settings()
        debounce_time = settings["debounce_time"]

        if data["debounce_task"] and not data["debounce_task"].done():
            data["debounce_task"].cancel()

        async def delay_execution():
            await asyncio.sleep(debounce_time)
            await async_execute_sync()

        data["debounce_task"] = hass.async_create_task(delay_execution())

    entry.async_on_unload(
        hass.bus.async_listen("entity_registry_updated", async_handle_entity_updated)
    )

    unload_listener = entry.add_update_listener(async_update_listener)
    entry.async_on_unload(unload_listener)

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    hass.async_create_task(async_execute_sync())

    return True

async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if PLATFORMS:
        return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return True