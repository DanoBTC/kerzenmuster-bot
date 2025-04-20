import requests
import pandas as pd
import datetime
import pytz
import matplotlib.pyplot as plt
import mplfinance as mpf
import time
import os

# === KONFIGURATION ===
SYMBOL = "BTCEUR"
GRANULARITY = "4h"
LIMIT = 50
INTERVAL_MINUTES = 10
TELEGRAM_BOT_TOKEN = "7624644037:AAFVX1hOSVQ6CwuESV2a89KaWDdEz2Io0YU"
TELEGRAM_CHAT_IDS = ["8103652120", "912069524"]

# === FUNKTION: Telegram-Nachricht senden ===
def send_telegram_message(bot_token, chat_ids, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chat_id in chat_ids:
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Fehler beim Senden der Nachricht an {chat_id}: {response.status_code}")
            print("Antwort:", response.text)
        else:
            print(f"✅ Nachricht erfolgreich an {chat_id} gesendet.")
    return True

# === FUNKTION: Kerzendaten abrufen ===
def get_candlestick_data(symbol, interval, limit=100):
    url = "https://api.bitget.com/api/v2/spot/market/candles"
    params = {
        "symbol": symbol,
        "granularity": interval,
        "limit": limit
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"❌ Fehler beim Abrufen der Kerzen: {response.status_code}")
        print("Antwort:", response.text)
        return None

    candles = response.json().get('data')
    if not candles:
        print("⚠️ Keine Kerzendaten gefunden.")
        return None

    data = []
    for candle in reversed(candles):
        timestamp = datetime.datetime.fromtimestamp(int(candle[0]) / 1000, pytz.utc)
        timestamp = timestamp.astimezone(pytz.timezone('Europe/Berlin'))
        open_, high, low, close = map(float, candle[1:5])
        data.append([timestamp, open_, high, low, close])

    df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close'])
    df.set_index('Time', inplace=True)
    df = df[::-1]  # neueste Kerzen rechts

    return df

# === FUNKTION: Candlestick-Chart anzeigen ===
def plot_candles(df, symbol, interval):
    print("🔍 Plotting Candlestick Chart...")  # Debugging-Ausgabe
    fig, axes = mpf.plot(df,
                         type='candlestick',
                         style='charles',
                         title=f"Kerzenformationen für {symbol} ({interval})",
                         ylabel='Preis (EUR)',
                         volume=False,
                         returnfig=True)
    
    axes[0].yaxis.tick_left()
    axes[0].yaxis.set_label_position('left')

    # Immer blockierend anzeigen, damit das Fenster offen bleibt
    plt.show(block=True)

# === FUNKTION: Überprüfen der bullischen Muster ===
def check_bullish_patterns(df):
    patterns = []

    # Bullish Engulfing
    if (
        df['Close'].iloc[-1] > df['Open'].iloc[-1] and
        df['Close'].iloc[-2] < df['Open'].iloc[-2] and
        df['Close'].iloc[-1] > df['Open'].iloc[-2] and
        df['Open'].iloc[-1] < df['Close'].iloc[-2]
    ):
        patterns.append("Bullish Engulfing")

    # Hammer  
    if (
        df['Close'].iloc[-1] > df['Open'].iloc[-1] and
        df['High'].iloc[-1] > df['Close'].iloc[-1] * 1.5 and
        (df['Close'].iloc[-1] - df['Open'].iloc[-1]) < 0.3 * (df['High'].iloc[-1] - df['Low'].iloc[-1])
    ):
        patterns.append("Hammer")

    # Inverted Hammer
    if (
        df['Close'].iloc[-1] > df['Open'].iloc[-1] and
        df['High'].iloc[-1] > df['Close'].iloc[-1] * 1.5 and
        (df['Open'].iloc[-1] - df['Close'].iloc[-1]) < 0.3 * (df['High'].iloc[-1] - df['Low'].iloc[-1])
    ):
        patterns.append("Inverted Hammer")

    # Piercing Line
    if (
        df['Close'].iloc[-1] > df['Open'].iloc[-1] and
        df['Close'].iloc[-2] < df['Open'].iloc[-2] and
        df['Close'].iloc[-1] > (df['Low'].iloc[-2] + df['Close'].iloc[-2]) / 2
    ):
        patterns.append("Piercing Line")

    # Morning Star (3-Kerzen-Formation)
    if len(df) >= 3:
        if (
            df['Close'].iloc[-3] < df['Open'].iloc[-3] and
            df['Close'].iloc[-2] > df['Open'].iloc[-2] and
            df['Close'].iloc[-1] > df['Open'].iloc[-1] and
            df['Close'].iloc[-2] > df['Close'].iloc[-3]
        ):
            patterns.append("Morning Star")

    return patterns


# === HAUPTSCHLEIFE ===
def check_and_plot():
    print("🔄 Abrufen der Kerzendaten...")
    df = get_candlestick_data(SYMBOL, GRANULARITY, limit=LIMIT)

    if df is None:
        print("⚠️ Keine Daten erhalten. Beende.")
        return

    print(f"📊 Kerzendaten erhalten: {df.head()}")
    plot_candles(df, SYMBOL, GRANULARITY)

    muster = check_bullish_patterns(df)

    if muster:
        print(f"🔍 Bullisches Muster erkannt: {', '.join(muster)}")

        muster_beschreibung = {
            "Bullish Engulfing": "Starke Umkehr. Entry nach Close. SL unter Tief. TP 1.5-2x SL.",
            "Hammer": "Kaufdruck nach Abverkauf. Entry über Hoch. SL unter Tief. TP 2x SL.",
            "Inverted Hammer": "Potenzielle Umkehr. Bestätigung abwarten! SL unter Tief. TP 1.5x SL.",
            "Piercing Line": "Starker Konter durch Käufer. Entry über Hoch. SL unter Tief. TP 2x SL.",
            "Morning Star": "3-Kerzen-Umkehr. Entry nach 3. Kerze. SL unter mittlerem Tief. TP 2x SL."
        }

        strategie_text = "\n\n📌 Strategieempfehlung:\n"
        for m in muster:
            if m in muster_beschreibung:
                strategie_text += f"• {m}: {muster_beschreibung[m]}\n"

        nachricht = (
            f"📈 Bullisches Muster erkannt: {', '.join(muster)}\n"
            f"📅 Zeit: {df.index[-1].strftime('%Y-%m-%d %H:%M')}"
            f"{strategie_text}"
        )

        send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, nachricht)
        print("✅ Nachricht gesendet.")
    else:
        print("🔍 Keine bullische Formation erkannt.")
    
    print(f"⏳ Warten auf nächste Runde...\n")

# === STARTPUNKT ===
if __name__ == "__main__":
    check_and_plot()

