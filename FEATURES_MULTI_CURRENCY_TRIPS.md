# Multi-Currency & Trip Archiving Features

## Overview

Your Crew Wallet app now supports **multiple currencies** and **trip archiving**, making it perfect for international sailing trips across different currency zones!

## 🌍 Multi-Currency Support

### Supported Currencies
- **EUR** (€) - Euro
- **DKK** (kr) - Danish Krone
- **SEK** (kr) - Swedish Krona  
- **GBP** (£) - British Pound

### How It Works

1. **Official Exchange Rates**: Uses European Central Bank (ECB) API for accurate, real-time exchange rates
2. **Daily Caching**: Rates are cached for 24 hours to minimize API calls and improve performance
3. **Automatic Conversion**: All amounts are automatically converted to EUR for balance calculations
4. **Dual Display**: You always see both the original currency AND the EUR equivalent

### Using Multi-Currency

**When Adding Deposits:**
- Select the currency from the dropdown (💱 Währung)
- Enter the amount in the selected currency
- The app automatically converts to EUR for calculations

**When Recording Expenses:**
- Choose your currency (EUR, DKK, SEK, GBP)
- Enter the amount in that currency
- Conversion to EUR happens automatically behind the scenes

**Viewing Amounts:**
- EUR amounts: Display as "100.00 €"
- Other currencies: Display as "100.00 DKK (≈ 13.42 €)"
- This way you always know both the original amount and EUR equivalent

### Example Scenario

Imagine you're sailing from Germany to Sweden to Denmark:
- Marina fee in Germany: 50.00 EUR
- Groceries in Sweden: 500.00 SEK (≈ 44.97 EUR)
- Diesel in Denmark: 300.00 DKK (≈ 40.23 EUR)

The app shows each amount in its original currency while calculating your total balance in EUR for easy settlement at the end of the trip.

## ⛵ Trip Management & Archiving

### Trip Organization

All your expenses, deposits, and crew members are now organized by **trip** (Törn). This makes it easy to:
- Keep multiple sailing trips separate
- Archive old trips when they're finished
- Start fresh for each new adventure
- Look back at past trip expenses

### Trip Statuses

- **Active**: The current trip you're working on (only ONE trip can be active at a time)
- **Archived**: Past trips that are finished and stored for reference

### Managing Trips

**Access Trip Management:**
- Click "⛵ Törns" in the navigation menu
- This shows all your trips and lets you create new ones

**Creating a New Trip:**
1. Enter trip name (e.g., "Baltic Sea 2025")
2. Enter start date
3. Click "Törn erstellen"
4. Your new trip becomes active automatically
5. The previous active trip gets archived

**Switching Between Trips:**
- **Activate an archived trip**: Click "✅ Aktivieren" to make it the active trip
- **Archive the current trip**: Click "📦 Archivieren" (you'll be asked to confirm)

### How Trips Work

- **All data is scoped to trips**: Crew members, deposits, and expenses belong to a specific trip
- **Only one active trip**: You can only work on one trip at a time
- **Independent crew lists**: Each trip can have different crew members with different codes
- **Separate balances**: Each trip has its own wallet balance and settlement calculations

### Example Workflow

1. **Start of Season**: Create "Baltic Sea Summer 2025" trip
2. **Add crew members** for this specific trip
3. **Track expenses** throughout the sailing season
4. **At season end**: Archive the trip
5. **Next trip**: Create "Mediterranean Fall 2025" with a fresh crew and balance

## 🔧 Technical Details

### Database Structure
- **Trip Model**: Links all crew, deposits, and expenses to a specific trip
- **Currency Fields**: Each deposit/expense stores both original amount + currency AND EUR equivalent
- **Active Trip Logic**: Dashboard and all pages automatically filter by active trip

### Exchange Rate Caching
- Rates are fetched once per day from ECB
- Cached in memory for 24 hours
- Falls back to 1.0 if API is unavailable (assumes EUR)
- Minimal performance impact

### Data Integrity
- Trip switching doesn't delete data - just changes what you see
- Archived trips preserve all historical data
- Crew member codes are unique per trip (not globally)
- Currency conversion happens at save time (not display time)

## 📊 Impact on Existing Features

### Balances & Settlement
- All calculations use EUR amounts for consistency
- Multi-currency expenses are included in settlement
- PayPal Pool link still works the same

### CSV Export
- Export includes original currency + EUR amount
- Filtered by active trip only
- Shows which trip the export is from

### Crew Management
- Crew codes must be unique within a trip
- Same person can use different codes in different trips
- Crew list shows only active trip members

## 💡 Tips for Crew

1. **Choose the right currency**: Always use the currency you actually paid in
2. **Check conversions**: The app shows EUR equivalents so you can verify they look correct
3. **One trip at a time**: Make sure you're on the right trip before adding data
4. **Archive when done**: Archive trips when finished to keep your workspace clean
5. **Exchange rates update daily**: Rates are cached, so small daily fluctuations won't affect past entries

## 🚀 Ready to Use!

The multi-currency and trip archiving features are now fully integrated into your app. Start by:

1. Creating your first trip at `/trips`
2. Adding crew members
3. Recording deposits and expenses with different currencies
4. Watching the automatic EUR conversion work its magic!

Happy sailing! ⛵🌊
