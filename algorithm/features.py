'''
Contains the modules required for features creation and backtesting
'''

import pandas as pd
import numpy as np
import csv

from glob import glob
import os
import json
import io

import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
from bokeh.plotting import figure, output_file, save

import swifter
import ta
import backtrader as bt

from utils.common_utils import get_root_dir

#maybe create a percentage of influential users
def tweets_to_features(group):
    features = {}
    
    # bots = group[group['predicted'] == 1]
    # humans = group[group['predicted'] == 0]
    
    features['number_of_tweets'] = len(group)
    # try:
    #     features['percentage_bots'] = (len(bots)/len(group)) * 100
    # except:
    #     features['percentage_bots'] = 0
        
    features['total_influence'] = group['avg_influence'].sum()
    
    try:
        features['sentistrength_total'] = sum(group['pos_neg'] * group['avg_influence'])
    except:
        features['sentistrength_total'] = 0
        
#     try:
#         features['vader_total'] = sum(group['vader_emotion'] * group['avg_influence'])
#     except:
#         features['vader_total'] = 0
    
    try:
        features['sentistrength_total_mean'] = sum(group['pos_neg'] * group['avg_influence'])/sum(group['avg_influence'])
    except:
        features['sentistrength_total_mean'] = 0
        
#     try:
#         features['vader_total_mean'] = sum(group['vader_emotion'] * group['avg_influence'])/sum(group['avg_influence'])
#     except:
#         features['vader_total_mean'] = 0
    
    return pd.Series(features)

def get_features(tweet_df, price_df, coin_name, curr_start, curr_end, minutes=30):
    '''
    Parameters:
    ___________
    tweet_df (DataFrame):
    Dataframe of tweets for the current coin
    
    price_df (DataFrame):
    Dataframe of price of the current coin
    
    coin_name (string):
    Name of coin
    
    curr_start (Timestamp):
    Starting time of the current all_cleaned
    
    curr_end (Timestamp):
    Ending time of the current all_cleaned
    '''
    features_dir = get_root_dir() + "/data/features"

    if not os.path.isdir(features_dir):
        os.makedirs(features_dir)
    
    features_file = features_dir + '/{}.csv'.format(coin_name)
    
    userwise_inf_file = os.path.join(get_root_dir(), 'data/userwise_influence.csv')
    userwise_inf = pd.read_csv(userwise_inf_file)

    tweet_df['Time'] = pd.to_datetime(tweet_df['Time'])
    tweet_df = tweet_df.sort_values('Time')
    
    tweet_df = tweet_df.merge(userwise_inf[['username', 'avg_influence', 'total_influence']], left_on='User', right_on='username', how='left')
    tweet_df['avg_influence'] = tweet_df['avg_influence'].fillna(2) #half the average if that user does not exist. This number goes down as our dataset goes up
    tweet_df['total_influence'] = tweet_df['total_influence'].fillna(6) #half the average for same reason

    price_df = price_df[(price_df['Time'] >= curr_start) & (price_df['Time'] <= curr_end)].reset_index(drop=True)
    features = tweet_df.groupby('Time').apply(tweets_to_features)
    features = price_df.merge(features, how='left', on='Time')
    features = features.fillna(0)

    if os.path.isfile(features_file):
        features = pd.concat([pd.read_csv(features_file), features])
        features['Time'] = pd.to_datetime(features['Time'])
        features = features.sort_values('Time')
        features = features.drop_duplicates('Time',keep='last')

    features.to_csv(features_file, index=None)

    return features
    
def create_plot(df, col1, col1_display, col3="Open", col3_display="Price"):
    hovertext = []

    for i in range(len(df['Time'])):
        hovertext.append('{}: '.format(col1_display)+str(round(df[col1][i], 2))
                         +'<br>{}: '.format(col3_display)+str(round(df[col3][i], 2))
                        )
    
    fig = go.Figure(layout=go.Layout(xaxis={'spikemode': 'across'}))
    
    

    fig.add_trace(go.Scatter(x=df['Time'], y=df[col1], name=col1_display, text=hovertext,
                            yaxis='y3', marker={'color': '#1f77b4'}
                            ))
    
    fig.add_trace(go.Scatter(x=df['Time'], y=df[col3], name=col3_display, text=hovertext, 
                             marker={'color': '#d62728'}))


    fig.update_layout(xaxis_rangeslider_visible=True)

    fig.update_layout(xaxis=dict(
                      domain=[0, 0.92]
                    ),
                      yaxis=dict(
                        title=col3_display,
                        titlefont=dict(
                            color="#d62728"
                        ),
                        tickfont=dict(
                            color="#d62728"
                        )
                    ),
                    yaxis3=dict(
                    title=col1_display,
                    titlefont=dict(
                        color="#1f77b4"
                    ),
                    tickfont=dict(
                        color="#1f77b4"
                    ),
                    anchor="x",
                    overlaying="y",
                    side="right",
                    position=0.98
                    )  
                )
    return fig

def resampler(df):
    ret = {}
    ret['Open'] = df['Open'].iloc[0]
    ret['Close'] = df['Close'].iloc[-1]
    ret['High'] = max(df['High'])
    ret['Low'] = min(df['Low'])
    ret['Volume'] = sum(df['Volume'])
    return pd.Series(ret)

class PandasData_Custom(bt.feeds.PandasData):
    lines = ('macd',)
    params = (
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('macd', 6)
    )

class tradeStrategy(bt.Strategy):
    def __init__(self):
        global long_macd_threshold, long_per_threshold, long_close_threshold, short_macd_threshold, short_per_threshold, short_close_threshold
        self.long_macd_threshold = long_macd_threshold
        self.long_per_threshold = long_per_threshold
        self.long_close_threshold = long_close_threshold
        
        self.short_macd_threshold = short_macd_threshold #was a mistake on grid search run it again with better parameters now i know what works
        self.short_per_threshold = short_per_threshold
        self.short_close_threshold = short_close_threshold
        
        global symbol
        self.symbol = symbol
        self.current_positions = {}
        self.current_positions[self.symbol] = 0
        
        
        self.dataopen = self.datas[0].open
        self.dataclose = self.datas[0].close
        
        self.macd = self.datas[0].macd
        
        self.buy_percentage = 0
        self.order=None
        self.buyprice=None
        self.buycomm=None
        self.position_time=None
        
        self.trades = io.StringIO()
        self.trades_writer = csv.writer(self.trades)
        
        self.operations = io.StringIO()
        self.operations_writer = csv.writer(self.operations)
        
        self.portfolioValue = io.StringIO()
        self.portfolioValue_writer = csv.writer(self.portfolioValue)
        
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
#         print("Datetime: {} Message: {} Percentage: {}".format(dt, txt, self.buy_percentage))
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                ordertype = "BUY"
                #self.log("BUY EXECUTED, Price: {}, Cost: {}, Comm: {}".format(order.executed.price, order.executed.value, order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                ordertype = "SELL"
                #self.log("SELL EXECUTED, Price: {}, Cost: {}, Comm: {}".format(order.executed.price, order.executed.value, order.executed.comm))

            self.trades_writer.writerow([self.datas[0].datetime.datetime(0), ordertype, order.executed.price, order.executed.value, order.executed.comm])
        
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")
            self.log(order.Rejected)
            self.trades_writer.writerow([self.datas[0].datetime.datetime(0) , 'Rejection', 0, 0, 0])
            
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log('OPERATION PROFIT, GROSS: {}, NET: {}'.format(trade.pnl, trade.pnlcomm))
        self.operations_writer.writerow([self.datas[0].datetime.datetime(0), trade.pnlcomm])
    
    def get_logs(self):
        '''
        Returns:
        ________
        portfolioValue (df):
        Date and Value of portfolio
        
        trades (df):
        'Date', 'Type', 'Price', 'Total Spent', 'Comission'
        
        operations (df):
        'Date', 'Profit'
        '''
        self.portfolioValue.seek(0)
        portfolioValueDf = pd.read_csv(self.portfolioValue, names=['Date', 'Value'])
        
        portfolioValueDf['Date'] = pd.to_datetime(portfolioValueDf['Date'])
        portfolioValueDf = portfolioValueDf.set_index('Date')
        portfolioValueDf = portfolioValueDf.resample('1D').agg({'Date': lambda x: x.iloc[0], 'Value': lambda x: x.iloc[-1]})['Date']
        
        self.trades.seek(0)
        tradesDf = pd.read_csv(self.trades, names=['Date', 'Type', 'Price', 'Total Spent', 'Comission'])
        
        self.operations.seek(0)
        operationsDf = pd.read_csv(self.operations, names=['Date', 'Profit'])
        
        return portfolioValueDf.reset_index(), tradesDf, operationsDf
    
    
    def next(self):
        self.portfolioValue_writer.writerow([self.datas[0].datetime.datetime(0), self.broker.getvalue()])
        
        if self.order:
            return
        
        per_change = ((self.dataopen[0]/self.dataopen[-4]) - 1) * 100
        
        total_possible_size = (self.broker.get_cash()/self.dataopen[0]) * 0.95
        
            
        if not self.position:
            if self.macd > self.long_macd_threshold and per_change < self.long_per_threshold:
                self.log("LONG CREATE {}".format(self.dataopen[0]))
                self.current_positions[self.symbol] = total_possible_size
                
                self.order = self.buy(size=self.current_positions[self.symbol])
            elif self.macd < self.short_macd_threshold and per_change > self.short_per_threshold:
                self.log("SHORT CREATE {}".format(self.dataopen[0]))
                self.current_positions[self.symbol] = total_possible_size
                
                self.order = self.sell(size=self.current_positions[self.symbol])
        else:
            if self.position.size > 0:         
                #LONG OPEN
                if self.macd < self.long_close_threshold:
                    self.log("LONG CLOSE {}".format(self.dataopen[0]))
                    self.order = self.sell(size=self.current_positions[self.symbol])
                    
                    if self.macd < self.short_macd_threshold and per_change > self.short_per_threshold:
                        self.log("SHORT CREATE {}".format(self.dataopen[0]))
                        self.current_positions[self.symbol] = total_possible_size

                        self.order = self.sell(size=self.current_positions[self.symbol])
                else:
                    self.log("HODL {}".format(self.dataopen[0]))
                                
            elif self.position.size < 0:
                if self.macd > self.short_close_threshold:
                    self.log("SHORT CLOSE {}".format(self.dataopen[0]))
                    self.order = self.buy(size=self.current_positions[self.symbol])
                    
                    if self.macd > self.long_macd_threshold and per_change < self.long_per_threshold:
                        self.log("LONG CREATE {}".format(self.dataopen[0]))
                        self.current_positions[self.symbol] = total_possible_size

                        self.order = self.buy(size=self.current_positions[self.symbol])
                else:
                    self.log("HODL {}".format(self.dataopen[0]))

def perform_backtest(symbol_par, n_fast_par, n_slow_par, long_macd_threshold_par, long_per_threshold_par, long_close_threshold_par, 
                    short_macd_threshold_par, short_per_threshold_par, short_close_threshold_par, initial_cash=10000, comission=0.1, df=None):
    '''
    Parameter:
    __________

    symbol_par (string):
    The symbol to use

    n_fast_par (int):
    Fast EMA line used during MACD calculation

    n_slow_par (int):
    Slower EMA line used during MACD calculation

    long_macd_threshold_par (int):
    The threshold of normalized macd, above which we might open a long position

    long_per_threshold_par (int):
    The value of percentage change over the last 2 hours above which we might open a long position
    #Might make this a parameter too

    long_close_threshold_par (int):
    Threshold of normalized macd, below which we will close the opened long position

    short_macd_threshold_par (int):
    The threshold of normalized macd, below which we might open a short position

    short_per_threshold_par (int):
    The value of percentage change over the last 2 hours below which we might open a short position

    short_close_threshold_par (int):
    Threshold of normalized macd, above which we will close the opened short position

    initial_cash (int) (optional):
    The cash to start from. Initiall 10k

    comission (int) (option):
    int fraction value. Defaults to 0.1%. This is much higher than normal. Staying on the safe side.

    df (Dataframe) (option):
    Uses df as features dataframe if specified. Otherwise reads the coin folder
    
    '''
    global n_fast
    global n_slow

    global long_macd_threshold
    global long_per_threshold
    global long_close_threshold
    global short_macd_threshold
    global short_per_threshold
    global short_close_threshold
    global symbol

    n_fast = n_fast_par
    n_slow = n_slow_par

    long_macd_threshold = long_macd_threshold_par
    long_per_threshold = long_per_threshold_par
    long_close_threshold = long_close_threshold_par
    short_macd_threshold = short_macd_threshold_par
    short_per_threshold = short_per_threshold_par
    short_close_threshold = short_close_threshold_par
    symbol = symbol_par

    features_file = get_root_dir() + "/data/features/{}.csv".format(symbol)

    if df is None:
        df = pd.read_csv(features_file)

    df['macd'] = ta.trend.macd(df['sentistrength_total'], n_fast=n_fast, n_slow=n_slow, fillna=True)
    df['macd'] = df['macd'].fillna(0)

    df['Time'] = pd.to_datetime(df['Time'])

    
    json_data = {}    

    json_data['mean'] = df['macd'].mean()
    json_data['std'] = df['macd'].std()

    df['macd'] = (df['macd'] - json_data['mean'])/json_data['std']

    df = df.dropna(subset=['Time'])

    curr_dir = get_root_dir() + "/data/backtest/{}".format(symbol)

    if not os.path.exists(curr_dir):
        os.makedirs(curr_dir)

    fig = create_plot(df, 'macd', 'SentiStength')

    plotly_json = fig.to_json()

    html = fig.to_html()

    with open(curr_dir + '/plotly.html', 'w') as file:
        file.write(html)

    with open(curr_dir + '/plotly.json', 'w') as file:
        file.write(plotly_json)

    df = df[['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'macd']]
    df.to_csv(os.path.join(curr_dir, "data.csv"), index=None)

    data = PandasData_Custom(dataname=df)
    cerebro = bt.Cerebro(cheat_on_open=True, maxcpus=None)
    cerebro.adddata(data)

    cerebro.addstrategy(tradeStrategy)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A)
    cerebro.addanalyzer(bt.analyzers.Calmar)
    cerebro.addanalyzer(bt.analyzers.DrawDown)
    cerebro.addanalyzer(bt.analyzers.Returns)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)

    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(comission/100)

    run = cerebro.run()

    portfolioValue, trades, operations = run[0].get_logs()

    # fig = cerebro.plot()
    # figure = fig[0][0]
    # figure.savefig(curr_dir + "/backtest.png")
    
    output_file(curr_dir + "/backtest.html")
    b = Bokeh(style='bar', plot_mode="tabs", scheme=Tradimo())
    b.plot_result(run)

    df = df.set_index('Time')
    df = df.resample('1D').apply(resampler)
    df = df.reset_index()
    df = df[['Time', 'Open']].merge(portfolioValue, left_on='Time', right_on='Date').drop('Time', axis=1)
    df['hodl'] = (initial_cash/df['Open'].iloc[0]) * df['Open']
    df = df.drop('Open', axis=1)

    df.to_csv(curr_dir + '/portfolio.csv', index=None)
    trades.to_csv(curr_dir + '/trades.csv', index=None)
    operations.to_csv(curr_dir + '/operations.csv', index=None)

    with open(os.path.join(curr_dir, "data.json"), 'w') as fp:
        json.dump(json_data, fp)