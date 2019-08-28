from django.shortcuts import render
import pandas as pd
import numpy as np
from glob import glob
from features import create_plot

def get_stats(symbol):
    stats = {}

    curr_folder = "algorithm/data/backtest/{}".format(symbol)
    portfolio = pd.read_csv(curr_folder + "/portfolio.csv")
    stats['return'] = round(((portfolio.iloc[-1]['Value'] / portfolio.iloc[0]['Value']) - 1) * 100, 2)
    stats['vs_hodl'] = round(((portfolio.iloc[-1]['Value'] / portfolio.iloc[-1]['hodl']) - 1) * 100, 2)
    stats['start_cash'] = portfolio.iloc[0]['Value']
    stats['end_cash'] = portfolio.iloc[-1]['Value']
    stats['end_hodl'] = portfolio.iloc[-1]['hodl']

    portfolio = portfolio.rename(columns={'Value': symbol})
    return portfolio[['Date', symbol]], stats

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

    combined_portfolio['portfolio'] = combined_portfolio.drop('btc_portfolio', axis=1).sum(axis=1)
    combined_portfolio = combined_portfolio[['portfolio', 'btc_portfolio']]
    
    combined_portfolio = combined_portfolio.reset_index()
    combined_portfolio = combined_portfolio.rename(columns={'Date': 'Time'})


    fig = create_plot(combined_portfolio, 'portfolio', 'Portfolio Movement', 'btc_portfolio', 'Bitcoin Movement')
    html = fig.to_html()

    with open('interface/templates/interface/plotly.html', 'w') as file:
        file.write(html)

    forward_metrics = {}
    forward_metrics['Total Return'] = round((sum(df['end_cash'])/sum(df['start_cash'])  - 1) * 100, 2)
    forward_metrics['Return VS hodl'] = round((sum(df['end_cash'])/sum(df['end_hodl'])  - 1) * 100, 2) #I think hodl return is WRONG because our features file starts way earlier
    # forward_metrics['Return VS Bitcoin hodl'] = round((sum(df['end_cash'])/sum(df['end_hodl'])  - 1) * 100, 2) 
    
    #add stuffs like best performer, worst performer, best 24 hours and worst 24 hours

    print(forward_metrics)

    return render(request, "interface/index.html", {'forward_metrics': forward_metrics, 'coinwise_stats': coinwise_stats})