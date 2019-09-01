from django.shortcuts import render

import pandas as pd
import numpy as np

from glob import glob
from shutil import copy

import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
    combined_portfolio['btc_portfolio'] = btc['hodl']
    dates = []

    for file in files:
        symbol = file.split('/')[-1].replace('.csv', '')
        curr_df, coinwise_stats[symbol] = get_stats(symbol)
        combined_portfolio = curr_df.merge(combined_portfolio, on='Date', how='right')

    

    combined_portfolio['btc_portfolio'] = combined_portfolio['btc_portfolio'] * (len(combined_portfolio.columns) - 2)

    df = pd.DataFrame.from_dict(coinwise_stats)
    df = df.T

    combined_portfolio = combined_portfolio.set_index('Date')

    print(combined_portfolio.columns)
    div = pd.DataFrame(((combined_portfolio.iloc[-1] / combined_portfolio.iloc[0]) - 1) * 100).reset_index()
    div.columns = ['Symbol', 'Change']

    div['Change'] = div['Change'].round(2)

    dictionary = dict(zip(div.Symbol,div.Change))
    print(dictionary)

    combined_portfolio['portfolio'] = combined_portfolio.drop('btc_portfolio', axis=1).sum(axis=1)
    combined_portfolio = combined_portfolio[['portfolio', 'btc_portfolio']]
    
    combined_portfolio = combined_portfolio.reset_index()
    combined_portfolio = combined_portfolio.rename(columns={'Date': 'Time'})

    fig = create_plot(combined_portfolio, 'portfolio', 'Portfolio Movement', 'btc_portfolio', 'Bitcoin HODL Portfolio')
    html = fig.to_html()

    with open('interface/static/interface/plotly.html', 'w') as file:
        file.write(html)

    forward_metrics = {}
    forward_metrics['Total Return'] = round((sum(df['end_cash'])/sum(df['start_cash'])  - 1) * 100, 2)
    forward_metrics['Return VS hodl'] = round((sum(df['end_cash'])/sum(df['end_hodl'])  - 1) * 100, 2) #I think hodl return is WRONG because our features file starts way earlier
    
    # forward_metrics['Return VS Bitcoin hodl'] = round((sum(df['end_cash'])/sum(df['end_hodl'])  - 1) * 100, 2) 
    #add stuffs like best performer, worst performer, best 24 hours and worst 24 hours and stats of each
    

    symbols = get_symbols()

    combined = {**forward_metrics, **dictionary}

    return render(request, "interface/index.html", {'forward_metrics': combined, 'symbols': symbols})