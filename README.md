# Apple Home 動態標籤橋接器 (Dynamic HomeKit Bridge)

這是一個專為 Home Assistant 設計的自訂整合，允許您將複雜的『實體』動態橋接至 Apple HomeKit。
透過這個套件，您可以更靈活地管理哪些裝置要出現在 Apple 的「家庭」App 中，並隨時調整更新速度，讓整個系統用起來更順手。

## 功能特色
- **動態標籤篩選 (Dynamic Tagging)**：
    您可以透過標籤 (Tags) 來篩選想橋接的裝置。
    #提醒：請先在 Home Assistant 中為您的裝置建立好標籤，設定時直接選取即可。
- **彈性調整更新時間**：
    系統預設的更新頻率可能不符合您的需求，這裡提供簡單的開關，讓您可以根據裝置特性調整橋接器的同步速度。
- **HACS 友善**：
    支援透過 HACS 一鍵安裝與更新。

## 如何安裝

1. 確保您已安裝 [HACS](https://hacs.xyz/)。
2. 在 HACS 中點擊右上角的三個點，選擇 **「自訂儲存庫 (Custom repositories)」**。
3. 輸入網址：`https://github.com/x857-mkt/dynamic_hk_bridge`
4. 類別選擇 **Integration**。
5. 安裝後，**請務必重啟 Home Assistant**。
6. 前往「設定」➔「裝置與服務」➔「新增整合」搜尋「Apple Home 動態標籤橋接器」就可以開始設定了。

## 授權
本專案基於 MIT 授權條款。
