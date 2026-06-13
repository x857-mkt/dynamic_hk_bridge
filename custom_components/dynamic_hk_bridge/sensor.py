from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """建立並新增動態橋接器的狀態感測器"""
    async_add_entities([DynamicHKBridgeStatusSensor(config_entry)], True)


class DynamicHKBridgeStatusSensor(SensorEntity):
    """用來代表這個整合的虛擬感測器，顯示目前運作狀態"""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._attr_name = "Apple Home Dynamic Bridge Status"
        self._attr_unique_id = f"{config_entry.entry_id}_status"
        self._attr_icon = "mdi:bridge"

    @property
    def state(self) -> str:
        """感測器數值直接顯示 Active 代表運作中"""
        return "Active"

    @property
    def extra_state_attributes(self) -> dict:
        """把目前的設定值當作屬性塞進去，方便除錯"""
        options = self._config_entry.options or self._config_entry.data
        return {
            "show_label": options.get("show_label", "hk_show"),
            "hide_label": options.get("hide_label", "hk_hide"),
            "debounce_time": options.get("debounce_time", 5),
        }