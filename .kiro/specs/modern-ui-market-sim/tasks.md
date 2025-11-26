# Implementation Plan

- [x] 1. Set up project structure and core interfaces
  - Create directory structure: `app/ui/`, `app/trading/`, `app/storage/`
  - Create `__init__.py` files for new packages
  - Add `hypothesis` to `requirements-dev.txt` for property-based testing
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 2. Implement Storage Service module
  - [x] 2.1 Create storage interfaces and JSON file storage
    - Implement `IStorageService` abstract base class in `app/storage/storage.py`
    - Implement `JsonFileStorage` class with save/load/delete methods
    - Use `pathlib` for cross-platform file path handling
    - _Requirements: 9.4, 8.3_

  - [x] 2.2 Write property test for storage round-trip
    - **Property 16: Portfolio serialization round-trip**
    - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 3. Implement Portfolio Manager module
  - [x] 3.1 Create Position and Transaction data models
    - Implement `Position` dataclass in `app/trading/models.py`
    - Implement `Transaction` dataclass with UUID generation
    - Use `Decimal` for all monetary values to avoid floating point errors
    - _Requirements: 5.5_

  - [x] 3.2 Implement IPortfolioManager interface and PortfolioManager class
    - Create `app/trading/portfolio.py` with interface and implementation
    - Implement balance tracking, position management, and transaction history
    - Implement average cost calculation using FIFO method
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2_

  - [x] 3.3 Write property test for portfolio initialization
    - **Property 3: Portfolio initialization with valid balance**
    - **Validates: Requirements 4.1**

  - [x] 3.4 Write property test for portfolio value calculation
    - **Property 4: Portfolio value calculation correctness**
    - **Validates: Requirements 4.2, 4.3**

  - [x] 3.5 Write property test for portfolio reset
    - **Property 5: Portfolio reset restores initial state**
    - **Validates: Requirements 4.4**

  - [x] 3.6 Write property test for buy order
    - **Property 6: Buy order balance and holdings update**
    - **Validates: Requirements 5.1**

  - [x] 3.7 Write property test for sell order
    - **Property 7: Sell order balance and holdings update**
    - **Validates: Requirements 5.2**

  - [x] 3.8 Write property test for transaction record completeness
    - **Property 10: Transaction record completeness**
    - **Validates: Requirements 5.5**

  - [x] 3.9 Implement PortfolioSerializer for JSON persistence
    - Add `serialize()` and `deserialize()` static methods
    - Handle Decimal and datetime serialization
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Order Service module
  - [x] 5.1 Create OrderResult and OrderRejectionReason models
    - Implement `OrderStatus` enum in `app/trading/orders.py`
    - Implement `OrderRejectionReason` enum
    - Implement `OrderResult` dataclass
    - _Requirements: 5.3, 5.4_

  - [x] 5.2 Create IDataProvider interface
    - Define abstract methods for `get_current_price()` and `is_connected()`
    - Create adapter class to wrap existing BinanceWsClient/BinanceRestProvider
    - _Requirements: 7.1, 7.2, 9.3_

  - [x] 5.3 Implement OrderService class
    - Implement `submit_buy()` with balance validation
    - Implement `submit_sell()` with holdings validation
    - Use injected IDataProvider for price lookup
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 7.2_

  - [x] 5.4 Write property test for insufficient balance rejection
    - **Property 8: Insufficient balance rejection**
    - **Validates: Requirements 5.3**

  - [x] 5.5 Write property test for insufficient holdings rejection
    - **Property 9: Insufficient holdings rejection**
    - **Validates: Requirements 5.4**

  - [x] 5.6 Write property test for order execution price
    - **Property 15: Order execution uses current price**
    - **Validates: Requirements 7.2**

- [x] 6. Implement Performance Analytics module
  - [x] 6.1 Create PerformanceMetrics dataclass and analytics class
    - Implement `PerformanceMetrics` dataclass in `app/trading/analytics.py`
    - Implement `IPerformanceAnalytics` interface
    - Implement `PerformanceAnalytics` class
    - _Requirements: 6.2, 6.3_

  - [x] 6.2 Implement realized PnL calculation
    - Track cost basis per symbol
    - Calculate PnL on sell transactions
    - _Requirements: 6.2_

  - [x] 6.3 Implement win rate and trade history sorting
    - Sort transactions by timestamp descending
    - Calculate win rate from profitable vs total trades
    - _Requirements: 6.1, 6.3_

  - [x] 6.4 Implement CSV export functionality
    - Use Python `csv` module for export
    - Include all transaction fields in output
    - _Requirements: 6.4_

  - [x] 6.5 Write property test for trade history sorting
    - **Property 11: Trade history sorting**
    - **Validates: Requirements 6.1**

  - [x] 6.6 Write property test for realized PnL calculation
    - **Property 12: Realized PnL calculation**
    - **Validates: Requirements 6.2**

  - [x] 6.7 Write property test for win rate calculation
    - **Property 13: Win rate calculation**
    - **Validates: Requirements 6.3**

  - [x] 6.8 Write property test for CSV export completeness
    - **Property 14: CSV export completeness**
    - **Validates: Requirements 6.4**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Acrylic Effect UI module
  - [x] 8.1 Create AcrylicWidget base class
    - Implement `app/ui/acrylic.py` with blur effect using QGraphicsBlurEffect
    - Implement fallback to solid background when effects not supported
    - Support configurable blur radius and tint opacity
    - _Requirements: 1.1, 1.4_

  - [x] 8.2 Implement theme-aware acrylic styling
    - Adjust opacity and blur for dark/light modes
    - Ensure contrast ratio compliance
    - Integrate with existing theme module
    - _Requirements: 1.2, 1.3_

  - [x] 8.3 Write property test for contrast ratio compliance
    - **Property 1: Theme contrast ratio compliance**
    - **Validates: Requirements 1.3**

- [x] 9. Implement Enhanced Visual Styling
  - [x] 9.1 Update theme module with gradient colors
    - Add positive/negative price color gradients to `app/theme.py`
    - Implement color selection function based on value sign
    - _Requirements: 3.1_

  - [x] 9.2 Implement table row styling enhancements
    - Add alternating row backgrounds with depth shadows
    - Implement accent-colored glow effect for selection
    - _Requirements: 3.2, 3.3_

  - [x] 9.3 Write property test for price color distinction
    - **Property 2: Positive/negative price color distinction**
    - **Validates: Requirements 3.1**

- [x] 10. Implement Paper Trading UI Panel
  - [x] 10.1 Create PaperTradingPanel widget
    - Create `app/ui/paper_trading.py` with main panel widget
    - Add order entry form (symbol, quantity, buy/sell buttons)
    - Display current balance and connection status
    - _Requirements: 5.1, 5.2, 7.3_

  - [x] 10.2 Create PortfolioView widget
    - Display positions table with symbol, quantity, avg cost, current value, PnL
    - Display total portfolio value and unrealized PnL
    - _Requirements: 4.2_

  - [x] 10.3 Create TradeHistoryView widget
    - Display transaction history in table format
    - Add export to CSV button
    - Display performance metrics (win rate, realized PnL)
    - _Requirements: 6.1, 6.4_

- [x] 11. Integrate Paper Trading with MainWindow
  - [x] 11.1 Add Paper Trading dock widget to MainWindow
    - Create new QDockWidget for paper trading panel
    - Add to right dock area alongside chart
    - Wire up data provider adapter to existing WS/REST clients
    - _Requirements: 7.1, 7.2_

  - [x] 11.2 Implement portfolio persistence on app lifecycle
    - Save portfolio state on application close
    - Restore portfolio state on application start
    - Handle corrupted data gracefully
    - _Requirements: 8.1, 8.2, 8.4_

  - [x] 11.3 Add connection status handling
    - Display warning when data connection lost
    - Disable order submission when disconnected
    - Resume operations when connection restored
    - _Requirements: 7.3, 7.4_

- [x] 12. Apply Acrylic Effect to UI Components
  - [x] 12.1 Apply acrylic effect to sidebar dock
    - Replace sidebar background with AcrylicWidget
    - Ensure text readability with proper contrast
    - _Requirements: 1.1, 1.3_

  - [x] 12.2 Apply acrylic effect to paper trading panel
    - Use consistent acrylic styling across panels
    - Maintain theme consistency
    - _Requirements: 1.1, 1.2_

- [x] 13. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implement Smooth Animations and Transitions
  - [x] 14.1 Create animation utilities module
    - Create `app/ui/animations.py` with animation helper classes
    - Implement FadeAnimator, PulseAnimator, ValueTransitionAnimator
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.4_

  - [x] 14.2 Implement price update fade animation
    - Add flash effect on price value changes in table cells
    - Green flash for price increase, red flash for decrease
    - Animation duration: 200ms
    - _Requirements: 2.1_

  - [x] 14.3 Implement hover highlight animations
    - Add hover effects to buttons with color transition
    - Add hover effects to table rows
    - Animation duration: 100ms
    - _Requirements: 2.3_

  - [x] 14.4 Implement critical alert pulsing animation
    - Add PulseAnimator for alert notifications
    - Yellow/orange pulsing effect on triggered alert rows
    - 3 pulse cycles with 800ms duration each
    - _Requirements: 3.4_
