# Implementation Plan

- [x] 1. Create Navigation Infrastructure




  - [x] 1.1 Create PageType enum and navigation state model


    - Create `app/ui/navigation.py` with PageType enum
    - Define NavigationState dataclass
    - _Requirements: 1.1, 1.5_

  - [x] 1.2 Implement NavigationSidebar widget






    - Create vertical layout with icon buttons
    - Add tooltip support for each button
    - Implement highlight state for selected page
    - Add pageSelected signal
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.3 Implement PageContainer widget


    - Create QStackedWidget-based container
    - Add page registration method
    - Implement switch_to() with fade animation
    - Add pageChanged signal
    - _Requirements: 1.4, 6.1, 6.2_

  - [x] 1.4 Write property test for navigation state consistency


    - **Property 1: Navigation state consistency**
    - **Validates: Requirements 1.4, 1.5**

- [x] 2. Create Page Widgets




  - [x] 2.1 Create MarketOverviewPage


    - Create `app/ui/pages/market_overview.py`
    - Integrate existing price table widget
    - Add chart panel with splitter
    - Wire up symbol selection to chart update
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 2.2 Create PaperTradingFullPage


    - Create `app/ui/pages/paper_trading_page.py`
    - Create three-column layout (order/portfolio/history)
    - Integrate existing PaperTradingPanel components
    - Add real-time price display
    - _Requirements: 3.1, 3.2, 3.3, 3.4_


  - [x] 2.3 Create ChartAnalysisPage

    - Create `app/ui/pages/chart_analysis.py`
    - Create full-width chart layout
    - Add toolbar with timeframe selector
    - Add symbol selector dropdown
    - _Requirements: 4.1, 4.2, 4.3, 4.4_


  - [x] 2.4 Create SettingsPage

    - Create `app/ui/pages/settings.py`
    - Add data source configuration section
    - Add appearance settings section
    - Add column visibility toggles
    - Wire up settings to storage service
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 2.5 Write property test for settings persistence


    - **Property 4: Settings persistence round-trip**
    - **Validates: Requirements 5.5**
- [x] 3. Checkpoint - Ensure navigation components work









- [ ] 3. Checkpoint - Ensure navigation components work

  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Integrate Navigation into MainWindow






  - [x] 4.1 Refactor MainWindow layout

    - Remove existing dock widgets
    - Add NavigationSidebar to left edge
    - Add PageContainer as central widget
    - _Requirements: 1.1_

  - [x] 4.2 Register pages with PageContainer

    - Create and register MarketOverviewPage
    - Create and register PaperTradingFullPage
    - Create and register ChartAnalysisPage
    - Create and register SettingsPage
    - _Requirements: 1.4_


  - [x] 4.3 Wire up navigation signals
    - Connect NavigationSidebar.pageSelected to PageContainer.switch_to
    - Connect PageContainer.pageChanged to NavigationSidebar.set_current_page
    - Set default page to MarketOverview
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 4.4 Migrate data flow to new pages

    - Connect WebSocket data to MarketOverviewPage
    - Connect data provider to PaperTradingFullPage
    - Connect chart data to ChartAnalysisPage
    - Connect settings to SettingsPage
    - _Requirements: 2.4, 3.4, 4.4, 5.4_

  - [x] 4.5 Write property test for state preservation


    - **Property 3: State preservation across navigation**
    - **Validates: Requirements 6.3**
- [x] 5. Implement Page Transition Animations








- [ ] 5. Implement Page Transition Animations

  - [x] 5.1 Add fade-out animation for outgoing page


    - Use QPropertyAnimation with opacity
    - Duration: 150ms
    - _Requirements: 6.1_



  - [x] 5.2 Add fade-in animation for incoming page


    - Use QPropertyAnimation with opacity
    - Duration: 150ms
    - _Requirements: 6.2_




  - [x] 5.3 Handle animation interruption

    - Cancel current animation on new navigation
    - Jump to target page immediately
    - _Requirements: 6.4_
-

- [x] 6. Implement Responsive Layout




  - [x] 6.1 Add window resize handler


    - Detect window width changes
    - Toggle sidebar collapsed state at 800px breakpoint
    - _Requirements: 7.1, 7.2_


  - [x] 6.2 Implement collapsed sidebar mode

    - Hide button labels when collapsed
    - Reduce sidebar width to icon-only
    - _Requirements: 7.1_


  - [x] 6.3 Add page container responsive adjustments

    - Adjust page layouts based on available width
    - _Requirements: 7.3, 7.4_


  - [x] 6.4 Write property test for responsive behavior

    - **Property 6: Responsive sidebar behavior**
    - **Validates: Requirements 7.1**
-


- [x] 7. Final Checkpoint - Ensure all tests pass



  - Ensure all tests pass, ask the user if questions arise.

