import logging
import asyncio
import yaml
from homeassistant.core import HomeAssistant, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er, label_registry as lr
from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)
DOMAIN = "dynamic_hk_bridge"
TARGET_FILE_NAME = "homekit_entities.yaml"

PLATFORMS = [Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """UI 託管核心進入點"""
    _LOGGER.info("🚀 [DHKB] 動態標籤橋接器已透過 UI 成功載入！")

    target_path = hass.config.path(TARGET_FILE_NAME)
    data = {"debounce_task": None}

    def get_current_settings():
        # 同步最安全的字典結合撈取法
        options = dict(entry.options or {})
        if not options:
            options = dict(entry.data or {})
        return {
            "show_label": options.get("show_label", "hk_show"),
            "hide_label": options.get("hide_label", "hk_hide"),
            "debounce_time": int(options.get("debounce_time", 5))
        }

    async def async_execute_sync():
        settings = get_current_settings()
        show_label = settings["show_label"]
        hide_label = settings["hide_label"]

        ent_reg = er.async_get(hass)
        lbl_reg = lr.async_get(hass)

        show_label_id = next((l.label_id for l in lbl_reg.async_list_labels() if l.name == show_label), None)
        hide_label_id = next((l.label_id for l in lbl_reg.async_list_labels() if l.name == hide_label), None)

        if not show_label_id:
            _LOGGER.warning(f"⚠️ [DHKB] 找不到白名單標籤 '{show_label}'，暫停同步。")
            return

        all_show_entities = [e.entity_id for e in ent_reg.entities.values() if show_label_id in e.labels]
        all_hide_entities = [e.entity_id for e in ent_reg.entities.values() if hide_label_id and hide_label_id in e.labels]
        final_sync_list = [e for e in all_show_entities if e not in all_hide_entities]

        try:
            def write_yaml():
                with open(target_path, 'w', encoding='utf-8') as f:
                    yaml.dump(final_sync_list, f, allow_unicode=True, default_flow_style=False)
            await hass.async_add_executor_job(write_yaml)
            _LOGGER.info(f"💾 [DHKB] 已將 {len(final_sync_list)} 個實體寫入 {TARGET_FILE_NAME}")
        except Exception as e:
            _LOGGER.error(f"❌ [DHKB] 寫入檔案失敗: {str(e)}")
            return

        try:
            await hass.services.async_call("homekit", "reload")
        except Exception as e:
            _LOGGER.error(f"❌ [DHKB] 呼叫 homekit.reload 服務失敗: {str(e)}")

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

    # 綁定重載監聽器
    unload_listener = entry.add_update_listener(async_update_listener)
    entry.async_on_unload(unload_listener)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.info("⚙️ [DHKB] 偵測到 UI 選項參數異動，正在動態重載整合...")
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸載整合時，同時卸載平台"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.info("⏹️ [DHKB] 已成功卸載整合項目與實體。")
    return unload_ok