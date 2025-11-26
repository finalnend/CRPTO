# Implementation Plan

- [x] 1. Create core utility classes





  - [x] 1.1 Create QuantityCalculator class with buy/sell calculation methods


    - Implement `calculate_buy_quantity(balance, price, percentage)` method
    - Implement `calculate_sell_quantity(position_size, percentage)` method
    - Add input validation for edge cases (zero price, negative values)
    - _Requirements: 1.2, 1.3_

  - [x] 1.2 Write property tests for QuantityCalculator

    - **Property 1: Buy Quantity Preset Calculation**
    - **Property 2: Sell Quantity Preset Calculation**
    - **Validates: Requirements 1.2, 1.3**
  - [x] 1.3 Create InputValidator class with validation logic


    - Implement `validate_quantity()` method returning (ValidationState, message)
    - Handle invalid inputs (negative, zero, non-numeric)
    - Handle warning states (exceeds balance/position)
    - Handle valid states (within limits)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 1.4 Write property tests for InputValidator

    - **Property 4: Invalid Input Detection**
    - **Property 5: Buy Over-Budget Warning**
    - **Property 6: Sell Over-Position Warning**
    - **Property 7: Valid Input Detection**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [x] 2. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.
-

- [x] 3. Create UI components for order panel enhancements




  - [x] 3.1 Create QuickPresetButtons widget


    - Create QWidget with 4 QPushButtons (25%, 50%, 75%, 100%)
    - Emit `presetClicked` signal with percentage value
    - Add `set_enabled()` method for disabling when price unavailable
    - Style buttons with consistent theme
    - _Requirements: 1.1, 1.4_
  - [x] 3.2 Create QuantitySlider widget







    - Create QWidget with QSlider and value display
    - Implement `set_range()`, `set_value()`, `get_value()` methods
    - Emit `valueChanged` signal on slider movement
    - Support Decimal precision for crypto quantities
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.3 Write property test for slider-input sync

    - **Property 3: Slider-Input Bidirectional Sync**
    - **Validates: Requirements 2.2, 2.3**
  - [x] 3.4 Create SymbolDropdown widget


    - Create dropdown with symbol list and current prices
    - Implement filtering based on text input
    - Emit `symbolSelected` signal on selection
    - Style dropdown to match application theme
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  - [x] 3.5 Write property tests for SymbolDropdown


    - **Property 11: Symbol Selection Updates**
    - **Property 12: Symbol Filter Matching**
    - **Validates: Requirements 8.3, 8.5**
-

- [x] 4. Checkpoint - Ensure all tests pass




  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Create Toast notification system




  - [x] 5.1 Create ToastNotification widget


    - Create QFrame-based notification with message and icon
    - Support success (green), error (red), info (blue) types
    - Implement auto-dismiss with QTimer
    - Add click-to-dismiss functionality
    - Add fade-in/fade-out animations
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [x] 5.2 Create ToastManager class


    - Manage notification stacking (vertical positioning)
    - Provide `show_success()`, `show_error()`, `show_info()` methods
    - Handle multiple simultaneous notifications
    - Clean up dismissed notifications
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
-

- [x] 6. Create OrderConfirmationDialog




  - [x] 6.1 Implement OrderConfirmationDialog


    - Create QDialog with order details display
    - Show symbol, type, quantity, price, total value
    - Add Confirm and Cancel buttons
    - Return boolean result from exec()
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 6.2 Write property test for confirmation threshold


    - **Property 8: Large Order Confirmation Threshold**
    - **Validates: Requirements 4.1**
-

- [x] 7. Checkpoint - Ensure all tests pass




  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Enhance PaperTradingPanel with new features





  - [x] 8.1 Integrate SymbolDropdown into order panel


    - Add dropdown button next to symbol input
    - Connect dropdown selection to symbol input
    - Update price display on symbol selection
    - Wire up symbol list from data provider
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  - [x] 8.2 Integrate QuickPresetButtons into order panel

    - Add preset buttons below quantity input
    - Connect preset clicks to quantity calculation
    - Update quantity input and slider on preset click
    - Disable presets when price unavailable
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 8.3 Integrate QuantitySlider into order panel
    - Add slider below quantity input
    - Implement bidirectional sync with quantity input
    - Update slider range based on balance/position
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 8.4 Add input validation visual feedback
    - Apply border colors based on ValidationState
    - Show tooltips for warning/error states
    - Update button enabled state based on validation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 8.5 Add keyboard shortcuts
    - Handle Enter key for Buy action
    - Handle Shift+Enter for Sell action
    - Handle Escape for clearing inputs
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 8.6 Integrate order confirmation dialog

    - Check order value against 50% threshold
    - Show confirmation dialog for large orders
    - Execute or cancel based on dialog result
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 8.7 Integrate ToastManager for order results

    - Show success toast on order execution
    - Show error toast on order failure
    - Include order details in toast message
    - _Requirements: 6.1, 6.2_

- [x] 9. Enhance PortfolioView with quick actions





  - [x] 9.1 Add Close button to position rows


    - Add Close button column to positions table
    - Style button color based on unrealized P&L
    - _Requirements: 7.1, 7.4_
  - [x] 9.2 Implement close position functionality


    - Connect Close button to order form pre-fill
    - Set symbol, order_type=SELL, quantity=position_size
    - _Requirements: 7.2_

  - [x] 9.3 Write property tests for position quick actions

    - **Property 9: Close Position Pre-fill**
    - **Property 10: Close Button Color by P&L**
    - **Validates: Requirements 7.2, 7.4**
- [x] 10. Final Checkpoint - Ensure all tests pass









- [ ] 10. Final Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

