from django.shortcuts import render

import pandas as pd
import numpy as np
import json

from glob import glob
from shutil import copy

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.common_utils import get_root_dir

def get_stats(symbol):
    stats = {}

    curr_folder = "algorithm/data/backtest/{}".format(symbol)
    portfolio = pd.read_csv(curr_folder + "/portfolio.csv")
    stats['return'] = round(((portfolio.iloc[-1]['Value'] / portfolio.iloc[0]['Value']) - 1) * 100, 2)
    stats['vs_hodl'] = round(((portfolio.iloc[-1]['Value'] / portfolio.iloc[-1]['hodl']) - 1) * 100, 2)
    stats['start_cash'] = round(portfolio.iloc[0]['Value'], 2)
    stats['end_cash'] = round(portfolio.iloc[-1]['Value'], 2)
    stats['end_hodl'] = round(portfolio.iloc[-1]['hodl'], 2)

    portfolio = portfolio.rename(columns={'Value': symbol})
    return portfolio[['Date', symbol]], stats

def get_features_stats(symbol):
    stats = {}
    
    curr_folder = "algorithm/data/backtest/{}".format(symbol)
    
    features = pd.read_csv(curr_folder + "/data.csv")

    with open(get_root_dir() + "/data/parameters.json") as f:
        json_info = json.load(f)

    features['Change'] = ((features['Open'] / features.shift(4)['Open']) - 1) * 100
    features['Change'] = features['Change'].fillna(0)
    
    stats['MACD Long Fulfilled'] = len(features[features['macd'] > json_info['long_macd_threshold']])
    stats['Long Change Fulfilled'] = len(features[features['Change'] > json_info['long_per_threshold']])
    stats['Long All Fulfilled'] = len(features[(features['macd'] > json_info['long_macd_threshold']) & (features['Change'] > json_info['long_per_threshold'])])
    stats['MACD Short Fulfilled'] = len(features[features['macd'] < json_info['short_macd_threshold']])
    stats['Short Change Fulfilled'] = len(features[features['Change'] < json_info['short_per_threshold']])
    stats['Short All Fulfilled'] = len(features[(features['macd'] < json_info['short_macd_threshold']) & (features['Change'] < json_info['short_per_threshold'])])
    
    stats['Current Change'] = features.iloc[-1]['Change']
    stats['Current MACD'] = features.iloc[-1]['macd']
    
    return stats

def get_symbols():
    files = glob('algorithm/data/backtest/*')
    symbols = [file.split('/')[-1].replace('.csv', '') for file in files]
    symbols.sort()

    return symbols

def coin_page(request, symbol):
    symbols = get_symbols()
    old_plotly_file = 'algorithm/data/backtest/{}/plotly.html'.format(symbol)
    plotly_file = 'interface/static/interface/plotly_{}.html'.format(symbol)

    copy(old_plotly_file, plotly_file)

    old_backtest_file = 'algorithm/data/backtest/{}/backtest.html'.format(symbol)
    backtest_file = 'interface/static/interface/backtest_{}.html'.format(symbol)

    copy(old_backtest_file, backtest_file)

    _, metrics = get_stats(symbol)
    print(metrics)

    return render(request, "interface/coinwise.html", {'symbols': symbols, 'forward_metrics': metrics, 'symbol_name': symbol})    

def create_plot(df, col1, col1_display, col2, col2_display):
    hovertext = []

    for i in range(len(df['Time'])):
        hovertext.append('{}: '.format(col1_display)+str(round(df[col1][i], 2))
                         +'<br>{}: '.format(col2_display)+str(round(df[col2][i], 2))
                        )
    
    fig = go.Figure(layout=go.Layout(xaxis={'spikemode': 'across'}))
    
    

    fig.add_trace(go.Scatter(x=df['Time'], y=df[col1], name=col1_display, text=hovertext,
                            marker={'color': '#1f77b4'}
                            ))
    
    fig.add_trace(go.Scatter(x=df['Time'], y=df[col2], name=col2_display, text=hovertext, 
                             marker={'color': '#d62728'}))


    fig.update_layout(xaxis_rangeslider_visible=True)
    return fig

#Add current prediction and all that. Change the table to better

# Create your views here.
def index(request):
    #my chart algorithm might be wrong
    files = glob('algorithm/data/backtest/*')

    coinwise_stats = {}
    combined_portfolio = pd.DataFrame()
    btc = pd.read_csv('algorithm/data/backtest/BTC/portfolio.csv')
    combined_portfolio['Date'] = btc['Date']
    dates = []

    for file in files:
        symbol = file.split('/')[-1].replace('.csv', '')
        curr_df, coinwise_stats[symbol] = get_stats(symbol)
        combined_portfolio = curr_df.merge(combined_portfolio, on='Date', how='right')

    
    combined_portfolio['btc_portfolio'] = btc['hodl']
    combined_portfolio['btc_portfolio'] = combined_portfolio['btc_portfolio'] * (len(combined_portfolio.columns) - 2)

    df = pd.DataFrame.from_dict(coinwise_stats)
    df = df.T

    combined_portfolio = combined_portfolio.set_index('Date')

    print(combined_portfolio.columns)
    div = pd.DataFrame(((combined_portfolio.iloc[-1] / combined_portfolio.iloc[0]) - 1) * 100).reset_index()
    div.columns = ['Symbol', 'Change']

    div['Change'] = div['Change'].round(2)
    div = div.sort_values('Change', ascending=False)

    

    combined_portfolio['portfolio'] = combined_portfolio.drop('btc_portfolio', axis=1).sum(axis=1)
    combined_portfolio = combined_portfolio[['portfolio', 'btc_portfolio']]
    
    combined_portfolio = combined_portfolio.reset_index()
    combined_portfolio = combined_portfolio.rename(columns={'Date': 'Time'})

    fig = create_plot(combined_portfolio, 'portfolio', 'Portfolio Movement', 'btc_portfolio', 'Bitcoin HODL Portfolio')
    html = fig.to_html()

    with open('interface/static/interface/plotly.html', 'w') as file:
        file.write(html)

    dictionary = dict(zip(div.Symbol,div.Change))
    print(dictionary)

    top_ten = ['TRX', 'OMG', 'MIOTA', 'ZEC', 'LTC', 'ETC', 'XTZ', 'BSV', 'SAN']

    btc['Date'] = pd.to_datetime(btc['Date'])
    top_df = df.loc[top_ten]

    forward_metrics = {}
    forward_metrics['Started From'] = btc.iloc[0]['Date'].strftime('%Y-%m-%d')
    forward_metrics['Traded for'] = str((btc.iloc[-1]['Date'] - btc.iloc[0]['Date']).days) + ' days'
    forward_metrics['Total Return'] = str(round((sum(df['end_cash'])/sum(df['start_cash'])  - 1) * 100, 2)) + " %"
    forward_metrics['Total Return - Predetermined Coins'] = str(round((sum(top_df['end_cash'])/sum(top_df['start_cash'])  - 1) * 100, 2))  + " %"
    forward_metrics['Return VS hodl all coins'] = str(round((sum(df['end_cash'])/sum(df['end_hodl'])  - 1) * 100, 2))  + " %"   
    
    # forward_metrics['Bitcoin hodl VS Portfolio'] = dictionary['btc_portfolio'] 
    del dictionary['btc_portfolio']

    symbols = get_symbols()

    #Features info calculation
    files = glob('algorithm/data/backtest/*')
    features_df = pd.DataFrame()


    for file in files:
        symbol = file.split('/')[-1].replace('.csv', '')
        curr_features = get_features_stats(symbol)
        curr_features['Symbol'] = symbol
        features_df = features_df.append(pd.Series(curr_features), ignore_index=True)

    with open(get_root_dir() + "/data/parameters.json") as f:
        json_info = json.load(f)

    features_df = features_df[['Symbol'] + list(features_df.columns[:-1])]

    features_df = features_df.sort_values('Current MACD').reset_index(drop=True)
    features_df = features_df.round(2)

    current_long = features_df[(features_df['Current MACD'] > json_info['long_macd_threshold']) & (features_df['Current Change'] < json_info['long_per_threshold'])]
    current_long = current_long[['Symbol', 'Current MACD', 'Current Change']].reset_index(drop=True)

    current_short = features_df[(features_df['Current MACD'] < json_info['short_macd_threshold']) & (features_df['Current Change'] > json_info['short_per_threshold'])]
    current_short = current_short[['Symbol', 'Current MACD', 'Current Change']].reset_index(drop=True)


    #Now add colors
    return render(request, "interface/index.html", {'forward_metrics': forward_metrics, 'current_parameters': json_info, 
                                                    'all_time_coinwise': dictionary, 'symbols': symbols, 'features': features_df.values.tolist(), 
                                                    'features_header': list(features_df.columns), 'current_long': current_long.values.tolist(),
                                                    'current_short': current_short.values.tolist(), 'long_short_headers': list(current_short.columns)})