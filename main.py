import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import warnings
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

def run_analysis_and_email():
    try:
        # --- PART 1: DATA ANALYSIS ---
        print("Step 1: Getting Nifty 500 List...")
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df_tickers = pd.read_csv(url)
        symbols = [s.strip() + ".NS" for s in df_tickers['Symbol'].tolist() if s.strip() != 'DUMMYHDLVR']

        print("Step 2: Downloading Data...")
        data = yf.download(symbols, period="60d", interval="1d", auto_adjust=True, threads=True, progress=False)['Close']
        data = data.dropna(axis=1, how='all')

        daily_returns = data.pct_change()
        daily_advances = (daily_returns > 0).sum(axis=1)
        daily_declines = (daily_returns < 0).sum(axis=1)

        avg_advances = daily_advances.rolling(window=20).mean()
        avg_declines = daily_declines.rolling(window=20).mean()

        total_avg_active = avg_advances + avg_declines
        mbr_series = (avg_advances - avg_declines) / total_avg_active

        df_analysis = pd.DataFrame({
            'Avg_Rising_20D': avg_advances,
            'Avg_Falling_20D': avg_declines,
            'MBR_Signal_20D': mbr_series
        }).dropna()

        # Latest Values
        latest = df_analysis.iloc[-1]
        last_date = df_analysis.index[-1].date()
        current_mbr = latest['MBR_Signal_20D']

        # Determine Signal
        signal_text = ""
        reason_text = ""
        if current_mbr > 0.10:
            signal_text = "STRONG BUY (Bullish Herding)"
            reason_text = "Pichle 1 mahine se consistently kharidari ho rahi hai."
        elif current_mbr > 0.0:
            signal_text = "WEAK BUY / NEUTRAL"
            reason_text = "Trend positive hai par weak hai."
        elif current_mbr < -0.10:
            signal_text = "STRONG SELL (Bearish Herding)"
            reason_text = "Pichle 1 mahine se consistently bikwali ho rahi hai."
        else:
            signal_text = "NEUTRAL / SIDEWAYS"
            reason_text = "Market directionless hai."

        # --- PART 2: GENERATE CHART ---
        plt.style.use('ggplot')
        plt.figure(figsize=(12, 6))
        plt.plot(df_analysis.index, df_analysis['MBR_Signal_20D'], color='blue', linewidth=2, label='20-Day Avg MBR')
        plt.axhline(0, color='black', linestyle='--')
        plt.axhline(0.10, color='green', linestyle=':', label='Buy Threshold')
        plt.axhline(-0.10, color='red', linestyle=':', label='Sell Threshold')
        plt.title(f'Nifty 500 Herding Signal ({last_date})')
        plt.legend()
        
        # Save chart instead of showing it
        chart_filename = "mbr_chart.png"
        plt.savefig(chart_filename)
        plt.close()

        # --- PART 3: SEND EMAIL ---
        email_sender = os.environ.get('EMAIL_USER')  # GitHub Secret se lega
        email_password = os.environ.get('EMAIL_PASS') # GitHub Secret se lega
        email_receiver = email_sender # Khud ko hi email bhejenge

        subject = f"Market Scan Report: {signal_text} [{last_date}]"
        
        body = f"""
        <html>
          <body>
            <h2>Nifty 500 MBR Analysis Report</h2>
            <p><strong>Date:</strong> {last_date}</p>
            <p><strong>Signal:</strong> {signal_text}</p>
            <p><strong>Reason:</strong> {reason_text}</p>
            <hr>
            <h3>Stats:</h3>
            <ul>
                <li><strong>Avg Rising Stocks (20D):</strong> {latest['Avg_Rising_20D']:.1f}</li>
                <li><strong>Avg Falling Stocks (20D):</strong> {latest['Avg_Falling_20D']:.1f}</li>
                <li><strong>MBR Value:</strong> {current_mbr:.4f}</li>
            </ul>
            <p>Chart is attached below.</p>
          </body>
        </html>
        """

        msg = MIMEMultipart()
        msg['From'] = email_sender
        msg['To'] = email_receiver
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        # Attach Chart
        with open(chart_filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {chart_filename}")
        msg.attach(part)

        # Send
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_sender, email_password)
        text = msg.as_string()
        server.sendmail(email_sender, email_receiver, text)
        server.quit()
        
        print("Email Sent Successfully!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_analysis_and_email()