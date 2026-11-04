"""Mobile-first research dashboard. Never sends brokerage orders."""
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Pocket Paper Trader",page_icon="📱",layout="centered",initial_sidebar_state="collapsed")
st.markdown('''<style>
.block-container {padding-top:1.2rem;padding-left:1rem;padding-right:1rem;max-width:780px}
[data-testid="stMetric"] {background:#172238;border-radius:12px;padding:12px}
.stButton button {min-height:46px;width:100%}
[data-testid="stDataFrame"] {font-size:12px}
</style>''',unsafe_allow_html=True)
SYMBOLS=['SPY','QQQ','AAPL','MSFT','NVDA']
ET=ZoneInfo('America/New_York')

@st.cache_data(ttl=120,show_spinner=False)
def bars(symbol):
    df=yf.download(symbol,period='5d',interval='5m',auto_adjust=True,progress=False,prepost=False,threads=False)
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    if df.empty:return df
    return df.dropna(subset=['Open','High','Low','Close','Volume']).copy()

def indicators(df):
    x=df.copy()
    x['EMA9']=x['Close'].ewm(span=9,adjust=False).mean()
    x['EMA21']=x['Close'].ewm(span=21,adjust=False).mean()
    idx=pd.DatetimeIndex(x.index)
    dates=idx.tz_convert(ET).date if idx.tz is not None else idx.date
    typical=(x['High']+x['Low']+x['Close'])/3
    vol=x['Volume']
    x['VWAP']=(typical*vol).groupby(dates).cumsum()/vol.groupby(dates).cumsum().replace(0,np.nan)
    return x

def assessment(x):
    if len(x)<25:return ('WAIT',0,'Not enough candles')
    b=x.iloc[-1];a=x.iloc[-2]
    tests={'Above VWAP':b.Close>b.VWAP,'EMA9 above EMA21':b.EMA9>b.EMA21,
           'Above EMA9':b.Close>b.EMA9,'Volume confirmation':b.Volume>x.Volume.iloc[-21:-1].median(),
           'Break of prior high':b.Close>a.High}
    score=sum(bool(v) for v in tests.values())
    return ('SETUP' if score==5 else 'WAIT',score,', '.join(k for k,v in tests.items() if not v) or 'All five conditions met')

def replay(x,capital,risk,rr):
    """Next-open fills, cash only, max one trade/day, exit at next candle stop/target.
    Stops are conservatively prioritized when both touched; overnight trades close at last close.
    """
    out=[];cash=float(capital);pos=None;used_dates=set()
    if len(x)<27:return pd.DataFrame()
    for i in range(25,len(x)):
        bar=x.iloc[i]; t=x.index[i]; date=str(t.tz_convert(ET).date() if t.tzinfo else t.date())
        if pos:
            stop_hit=bar.Low<=pos['Stop'];target_hit=bar.High>=pos['Target']
            day_end=i==len(x)-1 or (str(x.index[i+1].tz_convert(ET).date() if x.index[i+1].tzinfo else x.index[i+1].date())!=date)
            if stop_hit or target_hit or day_end:
                # Gap through stop may produce worse fill than the stop level.
                price=min(float(bar.Open),pos['Stop']) if stop_hit else pos['Target'] if target_hit else float(bar.Close)
                pnl=(price-pos['Entry'])*pos['Shares']
                cash+=pnl
                out.append({**pos,'Exit time':str(t),'Exit':round(price,2),'P&L':round(pnl,2),'Balance':round(cash,2)})
                pos=None
            continue
        if i==len(x)-1 or date in used_dates:continue
        next_t=x.index[i+1]
        next_date=str(next_t.tz_convert(ET).date() if next_t.tzinfo else next_t.date())
        if next_date!=date:continue
        status,_,_=assessment(x.iloc[:i+1])
        if status!='SETUP':continue
        entry=float(x.iloc[i+1].Open)
        stop=float(x['Low'].iloc[i-3:i+1].min())
        distance=entry-stop
        if distance<=0 or distance/entry>0.02:continue
        shares=min(int(risk/distance),int(cash/entry))
        if shares<1:continue
        pos={'Symbol':st.session_state.get('selected','SPY'),'Entry time':str(next_t),'Entry':round(entry,2),'Stop':round(stop,2),'Target':round(entry+rr*distance,2),'Shares':shares}
        used_dates.add(date)
    return pd.DataFrame(out)

st.title('📱 Pocket Paper Trader')
st.caption('Mobile market scanner + historical paper-trade replay · NO real orders')
with st.expander('⚙️ Simulator settings',expanded=False):
    capital=st.number_input('Virtual starting cash ($)',100.0,100000.0,1000.0,100.0)
    risk=st.number_input('Max planned risk per trade ($)',1.0,1000.0,5.0,1.0)
    rr=st.slider('Reward / risk target',1.0,4.0,2.0,0.5)
    st.caption('Cash-only whole shares. No leverage. One trade per symbol per day.')
if st.button('↻ Refresh market snapshot'):
    bars.clear();st.rerun()
scan=[];datasets={}
with st.spinner('Fetching recent 5-minute candles…'):
    for sym in SYMBOLS:
        try:
            df=bars(sym)
            if df.empty:scan.append({'Symbol':sym,'Status':'NO DATA','Score':'—','Last':'—'});continue
            x=indicators(df);datasets[sym]=x
            status,score,_=assessment(x)
            scan.append({'Symbol':sym,'Status':status,'Score':f'{score}/5','Last':f'${float(x.Close.iloc[-1]):,.2f}'})
        except Exception:
            scan.append({'Symbol':sym,'Status':'UNAVAILABLE','Score':'—','Last':'—'})
st.subheader('Market scanner')
st.dataframe(pd.DataFrame(scan),hide_index=True,use_container_width=True)
st.caption('Data: Yahoo Finance via yfinance; may be delayed, stale, or unavailable. Refreshes only when this page reruns or you tap Refresh. Not an always-on scanner.')
if not datasets:st.error('No data available right now. Try again later.');st.stop()
symbol=st.selectbox('Inspect symbol',list(datasets),key='selected')
x=datasets[symbol];status,score,why=assessment(x);last=x.iloc[-1]
c1,c2=st.columns(2)
c1.metric('Latest candle close',f'${last.Close:,.2f}')
c2.metric('Setup',f'{status} · {score}/5')
c3,c4=st.columns(2)
c3.metric('VWAP',f'${last.VWAP:,.2f}')
c4.metric('EMA9',f'${last.EMA9:,.2f}')
st.info('Signal explanation: '+ ('All five conditions met; not a recommendation to buy.' if status=='SETUP' else 'Missing: '+why))
st.caption('Last candle timestamp: '+str(x.index[-1]))
st.line_chart(x[['Close','VWAP','EMA9','EMA21']].tail(100),height=260)
st.subheader('🧪 Paper-trade replay')
st.caption('Historical replay over the available ~5 trading days. This is NOT continuous simulated execution. It does not place or monitor trades when the app is closed.')
trades=replay(x,capital,risk,rr)
if trades.empty:
    st.warning('No completed simulated trades matched these rules in the available sample.')
else:
    pnl=float(trades['P&L'].sum());win=float((trades['P&L']>0).mean()*100)
    a,b=st.columns(2);a.metric('Replay P&L',f'${pnl:+,.2f}');b.metric('Win rate',f'{win:.0f}%')
    a,b=st.columns(2);a.metric('Trades',len(trades));b.metric('Ending cash',f'${capital+pnl:,.2f}')
    st.dataframe(trades.iloc[::-1],hide_index=True,use_container_width=True)
    st.line_chart(trades.set_index('Exit time')['Balance'],height=190)
st.warning('Educational prototype only. Short historical sample, no spread, commissions, slippage or taxes; no evidence of profitability. Live signals are unverified and may use incomplete candles. Never use these results as a trading recommendation.')
st.caption('Version 1 mobile · research and simulation only')
