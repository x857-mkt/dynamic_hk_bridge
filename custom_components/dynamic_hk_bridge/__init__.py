import logging
import asyncio
from homeassistant.core import HomeAssistant, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er, label_registry as lr
from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)
DOMAIN = "dynamic_hk_bridge"
PLATFORMS = [Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """UI 託管核心進入點"""
    _LOGGER.info("🚀 [DHKB] 動態標籤橋接器已透過 UI 成功載入！")

    data = {"debounce_task": None}

    def get_current_settings():
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
        
        # 【修正 1】支援半形逗號複選切分
        show_labels = [tag.strip() for tag in settings["show_label"].split(",") if tag.strip()]
        hide_labels = [tag.strip() for tag in settings["hide_label"].split(",") if tag.strip()]

        ent_reg = er.async_get(hass)
        lbl_reg = lr.async_get(hass)

        # 找出所有對應的標籤 ID 列表
        all_labels = lbl_reg.async_list_labels()
        show_label_ids = [l.label_id for l in all_labels if l.name in show_labels]
        hide_label_ids = [l.label_id for l in all_labels if l.name in hide_labels]

        if not show_label_ids:
            _LOGGER.warning("[DHKB] 找不到任何有效的白名單標籤，暫停同步。")
            return

        # 篩選實體
        all_show_entities = [
            e.entity_id for e in ent_reg.entities.values() 
            if any(lid in e.labels for lid in show_label_ids)
        ]
        all_hide_entities = [
            e.entity_id for e in ent_reg.entities.values() 
            if any(lid in e.labels for lid in hide_label_ids)
        ]
        final_sync_list = [e for e in all_show_entities if e not in all_hide_entities]

        _LOGGER.info(f"🔍 [DHKB] 經標籤計算，最終應同步至 HomeKit 的實體數量: {len(final_sync_list)}")

        # 【核心修正 2】直接對 HA 的原生 HomeKit 整合實施「動態動手術」覆蓋設定
        homekit_entries = hass.config_entries.async_entries("homekit")
        if not homekit_entries:
            _LOGGER.warning("[DHKB] 警告：目前系統中找不到任何原生的 HomeKit 整合實例，請確保已建立 HomeKit 橋接器。")
            return

        for hk_entry in homekit_entries:
            current_hk_options = dict(hk_entry.options)
            
            # 強制改寫原生 HomeKit 的過濾規則
            current_hk_options["filter"] = {
                "include_domains": [],
                "include_entities": final_sync_list,  # 灌入我們的白名單
                "exclude_domains": [],
                "exclude_entities": []
            }
            
            # 將新的過濾清單寫入原生 HomeKit 記憶體
            hass.config_entries.async_update_entry(hk_entry, options=current_hk_options)
            _LOGGER.info(f"⚡ [DHKB] 已將過濾規則強制注入 HomeKit 執行個體: {hk_entry.title}")

        # 呼叫 HomeKit 重新載入，讓變更立即生效
        try:
            await hass.services.async_call("homekit", "reload")
            _LOGGER.info("🔄 [DHKB] 已成功觸發 homekit.reload 服務！")
        except Exception as e:
            _LOGGER.error(f"❌ [DHKB] 呼叫 homekit.reload 失敗: {str(e)}")

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

    # 監聽實體異動
    entry.async_on_unload(
        hass.bus.async_listen("entity_registry_updated", async_handle_entity_updated)
    )

    # 綁定重載監聽器
    unload_listener = entry.add_update_listener(async_update_listener)
    entry.async_on_unload(unload_listener)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 【核心修正 3】啟動時「立刻執行一次同步」，確保重啟 HA 後過濾名單生效！
    hass.async_create_task(async_execute_sync())

    return True

async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.info("⚙️ [DHKB] 偵測到 UI 選項參數異動，正在動態重載整合...")
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.info("⏹️ [DHKB] 已成功卸載整合項目與實體。")
    return unload_ok