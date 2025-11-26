# Requirements Document

## Introduction

本功能旨在提升模擬交易 (Paper Trading) 頁面的 UI/UX 便利性，包括快速下單預設、輸入驗證回饋、數量滑桿、鍵盤快捷鍵、以及訂單確認等功能。目標是讓使用者能更高效、更直覺地進行模擬交易操作。

## Glossary

- **System**: 加密貨幣交易應用程式的模擬交易模組 (Paper Trading Module)
- **User**: 使用模擬交易功能的交易者
- **Quick Order Preset**: 快速下單預設，允許使用者透過百分比按鈕快速設定數量
- **Quantity Slider**: 數量滑桿，視覺化調整下單數量的控制元件
- **Order Confirmation**: 訂單確認對話框，在執行大額訂單前要求使用者確認
- **Input Validation**: 輸入驗證，即時檢查使用者輸入的有效性
- **Toast Notification**: 短暫顯示的通知訊息，用於回饋操作結果

## Requirements

### Requirement 1: Quick Order Presets

**User Story:** As a user, I want to quickly select common order quantities using percentage buttons, so that I can place orders faster without calculating exact amounts.

#### Acceptance Criteria

1. WHEN the Paper Trading order panel loads THEN the System SHALL display quick quantity preset buttons (25%, 50%, 75%, 100%)
2. WHEN a user clicks a percentage preset button for a BUY order THEN the System SHALL calculate the quantity based on available balance divided by current price multiplied by the percentage
3. WHEN a user clicks a percentage preset button for a SELL order THEN the System SHALL calculate the quantity based on current position size multiplied by the percentage
4. WHEN the current price is unavailable THEN the System SHALL disable the preset buttons and display a tooltip indicating price data is required

### Requirement 2: Quantity Slider

**User Story:** As a user, I want to use a slider to adjust order quantity visually, so that I can select amounts intuitively without typing.

#### Acceptance Criteria

1. WHEN the Paper Trading order panel loads THEN the System SHALL display a quantity slider below the quantity input field
2. WHEN a user drags the slider THEN the System SHALL update the quantity input field value in real-time
3. WHEN a user types in the quantity input field THEN the System SHALL update the slider position to reflect the entered value
4. WHEN the slider reaches maximum position THEN the System SHALL represent 100% of available balance for BUY or 100% of position for SELL

### Requirement 3: Input Validation Feedback

**User Story:** As a user, I want immediate visual feedback on my input validity, so that I can identify and correct errors before submitting orders.

#### Acceptance Criteria

1. WHEN a user enters an invalid quantity (negative, zero, or non-numeric) THEN the System SHALL display a red border on the quantity input field
2. WHEN a user enters a BUY quantity that exceeds affordable amount based on balance THEN the System SHALL display an orange warning border and tooltip
3. WHEN a user enters a SELL quantity that exceeds current position THEN the System SHALL display an orange warning border and tooltip
4. WHEN all inputs are valid and within limits THEN the System SHALL display a green border on the quantity input field
5. WHEN the symbol input is empty or invalid THEN the System SHALL disable the Buy and Sell buttons

### Requirement 4: Order Confirmation Dialog

**User Story:** As a user, I want to confirm large orders before execution, so that I can prevent accidental trades.

#### Acceptance Criteria

1. WHEN a user submits an order with value exceeding 50% of available balance THEN the System SHALL display a confirmation dialog before execution
2. WHEN the confirmation dialog is displayed THEN the System SHALL show order details including symbol, type, quantity, price, and total value
3. WHEN a user clicks Confirm in the dialog THEN the System SHALL execute the order
4. WHEN a user clicks Cancel in the dialog THEN the System SHALL cancel the order and return to the order form

### Requirement 5: Keyboard Shortcuts for Trading

**User Story:** As a user, I want to use keyboard shortcuts for common trading actions, so that I can trade more efficiently.

#### Acceptance Criteria

1. WHEN a user presses Enter in the quantity input field THEN the System SHALL trigger the Buy action
2. WHEN a user presses Shift+Enter in the quantity input field THEN the System SHALL trigger the Sell action
3. WHEN a user presses Escape on the Paper Trading page THEN the System SHALL clear all input fields
4. WHEN a user presses Tab THEN the System SHALL navigate between input fields in logical order (Symbol, Quantity, Buy, Sell)

### Requirement 6: Order Result Toast Notifications

**User Story:** As a user, I want to see clear toast notifications for order results, so that I know immediately when orders succeed or fail.

#### Acceptance Criteria

1. WHEN an order is successfully executed THEN the System SHALL display a green success toast with order summary (symbol, type, quantity, price)
2. WHEN an order fails THEN the System SHALL display a red error toast with the failure reason
3. WHEN a toast notification is displayed THEN the System SHALL auto-dismiss the notification after 4 seconds
4. WHEN a user clicks on a toast notification THEN the System SHALL dismiss the notification immediately

### Requirement 7: Position Quick Actions

**User Story:** As a user, I want quick action buttons on my positions, so that I can close or modify positions with fewer clicks.

#### Acceptance Criteria

1. WHEN a position is displayed in the Portfolio Positions table THEN the System SHALL show a "Close" button for each position row
2. WHEN a user clicks the Close button on a position THEN the System SHALL pre-fill the order form with a SELL order for the full position quantity
3. WHEN a user hovers over a position row THEN the System SHALL highlight the row and show available quick actions
4. WHEN a position has unrealized profit THEN the System SHALL display the Close button in green; WHEN unrealized loss THEN the System SHALL display the Close button in red

### Requirement 8: Symbol Quick Select Dropdown

**User Story:** As a user, I want a dropdown menu to quickly select trading symbols, so that I can switch between symbols without typing.

#### Acceptance Criteria

1. WHEN the Paper Trading order panel loads THEN the System SHALL display a dropdown button next to the symbol input field
2. WHEN a user clicks the dropdown button THEN the System SHALL display a list of available trading symbols
3. WHEN a user selects a symbol from the dropdown THEN the System SHALL fill the symbol input field and update the current price display
4. WHEN the dropdown is open THEN the System SHALL display symbols with their current prices
5. WHEN a user types in the symbol input field THEN the System SHALL filter the dropdown list to show matching symbols

