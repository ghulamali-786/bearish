import requests
import time
from datetime import datetime, timedelta
from pytz import timezone  # Install with: pip install pytz

# ========== Configuration ==========
UTC_PLUS_5 = timezone('Asia/Karachi')  # UTC+5 timezone (Karachi, Islamabad)
TELEGRAM_BOT_TOKEN = '7874057425:AAFEESSpFnTQ9Dh1XUwVBMEZ78zQ4ouY-Gw'
TELEGRAM_CHAT_ID = ' 6018062533'

def send_telegram_message(message):
    """Send message to Telegram channel"""
    try:
        url = f"https://api.telegram.org/bot{7874057425:AAFEESSpFnTQ9Dh1XUwVBMEZ78zQ4ouY-Gw}/sendMessage"
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, params=params)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def get_next_check_time():
    """Calculate next 00:00 UTC+5"""
    now = datetime.now(UTC_PLUS_5)
    if now.hour >= 0 or now.minute > 0:
        next_day = now + timedelta(days=1)
        return UTC_PLUS_5.localize(datetime(next_day.year, next_day.month, next_day.day))
    return now

def fetch_usdt_pairs():
    """Get active USDT trading pairs"""
    try:
        response = requests.get('https://api.binance.com/api/v3/exchangeInfo')
        return [s['symbol'] for s in response.json()['symbols']
                if s['status'] == 'TRADING' 
                and s['quoteAsset'] == 'USDT'
                and s['symbol'].endswith('USDT')]
    except Exception as e:
        print(f"Error fetching pairs: {e}")
        return []

def check_engulfing(symbol):
    """Check for completed bearish engulfing pattern"""
    try:
        # Get candles in UTC timezone
        response = requests.get(
            'https://api.binance.com/api/v3/klines',
            params={'symbol': symbol, 'interval': '1d', 'limit': 2}
        )
        candles = response.json()
        if len(candles) < 2:
            return False
            
        prev = candles[0]
        curr = candles[1]
        
        prev_open = float(prev[1])
        prev_close = float(prev[4])
        curr_open = float(curr[1])
        curr_close = float(curr[4])
        
        return (
            prev_close > prev_open and  # Yesterday green
            curr_close < curr_open and  # Today red
            curr_open > prev_close and  # Engulf open
            curr_close < prev_open and  # Engulf close
            float(curr[2]) > float(prev[2]) and  # Higher high
            float(curr[3]) < float(prev[3])   # Lower low
        )
    except Exception as e:
        print(f"Error checking {symbol}: {e}")
        return False

def main_scan():
    """Run daily pattern check"""
    utc_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    local_time = datetime.now(UTC_PLUS_5).strftime('%Y-%m-%d %H:%M:%S')
    
    print("\n" + "="*50)
    print(f"UTC Time: {utc_time} | Local Time (UTC+5): {local_time}")
    
    pairs = fetch_usdt_pairs()
    if not pairs:
        send_telegram_message("⚠️ Error: Failed to fetch trading pairs")
        return
    
    print(f"Checking {len(pairs)} coins...")
    results = []
    
    for idx, symbol in enumerate(pairs, 1):
        try:
            if check_engulfing(symbol):
                results.append(symbol)
            print(f"Progress: {idx}/{len(pairs)}", end='\r')
            time.sleep(0.1)  # Rate limit protection
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    
    # Prepare and send message
    if results:
        message = f"🔻 <b>Bearish Engulfing Patterns Detected at 00:00 UTC+5</b>\n"
        message += "\n".join(results)
        message += f"\n\nUTC Time: {utc_time}\nLocal Time: {local_time}"
    else:
        message = f"✅ No patterns found\nUTC Time: {utc_time}\nLocal Time: {local_time}"
    
    if send_telegram_message(message):
        print("\nTelegram notification sent successfully!")
    else:
        print("\nFailed to send Telegram notification")

def run_scheduler():
    """Main scheduling loop"""
    print("Crypto Scanner - UTC+5 Version")
    print("Configured for daily 00:00 UTC+5 checks (19:00 UTC)\n")
    
    while True:
        try:
            next_check = get_next_check_time()
            sleep_seconds = (next_check - datetime.now(UTC_PLUS_5)).total_seconds()
            
            if sleep_seconds > 0:
                local_str = next_check.strftime('%Y-%m-%d %H:%M:%S')
                utc_str = next_check.astimezone(timezone('UTC')).strftime('%H:%M:%S')
                print(f"Next check at {local_str} UTC+5 ({utc_str} UTC)")
                time.sleep(sleep_seconds)
            
            main_scan()
            
            # Sleep 1 minute to avoid immediate recheck
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\nScanner stopped by user")
            break
        except Exception as e:
            print(f"Critical error: {e}")
            send_telegram_message(f"🚨 Scanner crashed: {str(e)}")
            time.sleep(3600)  # Wait 1 hour before retrying

if __name__ == "__main__":
    run_scheduler()