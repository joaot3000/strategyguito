﻿# strategyguito
# TradingView to Alpaca Email Bot

Automatically trades SPY based on TradingView email alerts.

## Setup
1. Clone repository
2. Create `.env` file (use `.env.example` as template)
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Deployment
1. Set environment variables in Render
2. Connect GitHub repository
3. Deploy using `render.yaml`

## Alert Format
TradingView emails must contain:
- "Buy" for long positions
- "Sell" for short positions
