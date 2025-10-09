# Crypto Ticker (PySide6)

Windows 桌面應用，使用 Python 後端 + PySide6 UI。

即時模式採 Binance WebSocket 串流；若斷線自動回退到 REST（Binance → CoinGecko → Coinbase）。

## 快速開始（Windows）

1. 建立虛擬環境
   - PowerShell: `py -3 -m venv .venv`
   - 啟用：`.venv\Scripts\Activate.ps1`

2. 安裝依賴
   - `pip install -r requirements.txt`

3. 執行
   - `python app\main.py`

4. 打包 EXE（選用）
   - `pip install -r requirements-dev.txt`
   - `build_exe.bat`（於 Windows 產出 `dist/CryptoTicker/CryptoTicker.exe`）
   - 若執行檔啟動失敗，先嘗試 `build_exe_debug.bat` 取得詳細 log（含 Qt plugin 載入）

## 功能

- 預設追蹤 `BTCUSDT`, `ETHUSDT`, `BNBUSDT`
- 可在上方輸入框新增代號（支援 `BTCUSDT` 或 `BTC/USDT` 等格式）
- 預設使用 Binance WebSocket（24hr ticker），顯示：最新價、24h 漲跌%、24h 高/低、24h 量、時間
- 若 WS 失敗自動改用 REST；亦可手動切換資料源（工具列）
- 點標題可排序（數值正確排序），工具列「Columns」可自訂欄位顯示
- 表格右鍵設定價格警報（上限/下限），觸發會以系統匣通知
- 關閉視窗預設最小化到系統匣（可在工具列切換）

## 注意事項

- Binance 公開 API 有頻率限制（REST），若追蹤代號過多或過短間隔可能觸發限制。
- 若你在中國大陸網路環境，可能需要代理才能存取 Binance API。

## 打包故障排查（PyInstaller）

- 平台外掛錯誤（如 Could not find the Qt platform plugin "windows"）
  - 以 `build_exe.bat` 的 `--collect-all PySide6` 將會打包所有 Qt 外掛（platforms/tls/imageformats 等）
- WebSocket/TLS 問題（wss 連線失敗）
  - 確認 `dist/CryptoTicker/PySide6/Qt/plugins/tls` 目錄存在；或以 `build_exe_debug.bat` 查看 `QT_DEBUG_PLUGINS` 訊息
- HTTPS 連線錯誤（SSL cert）
  - 已加入 `--collect-all certifi`，確保 `cacert.pem` 被打包；如仍有問題，請回報錯誤訊息

## 資料源說明

- Binance WS：`wss://stream.binance.com:9443`（24hr ticker），即時更新
- Binance REST：`/api/v3/ticker/24hr`（逐一請求，避免批次 400）
- CoinGecko REST：`/api/v3/simple/price`（以 USD 近似 USDT，含 24h 變化/量）
- Coinbase REST：`/products/<BASE-USD>/ticker` + `/stats`（計算 24h%）

註：非 USDT 市場的資料源（CoinGecko/Coinbase）以 USD 近似顯示，僅作故障回退之用。

## 後續可做

- 改為 WebSocket 訂閱（Binance Spot stream）
- 加入多資料源（CoinGecko/Coinbase）與故障切換
- 自訂欄位（高低價、成交額、最佳買賣價等）
- 匯出自訂清單、開機自動啟動
