from flask import Flask, jsonify, render_template, request
import requests
import plotly
import plotly.graph_objects as go
import json
import numpy as np
from datetime import datetime

app = Flask(__name__)

API_KEY = 'api_key'
BAZAAR_API_URL = 'https://api.hypixel.net/skyblock/bazaar?key=' + API_KEY

def get_bazaar_data():
    try:
        response = requests.get(BAZAAR_API_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def calculate_advanced_score(bazaar_data):
    scores = []

    for item_id, item_data in bazaar_data['products'].items():
        if "enchantment" in item_id.lower():
            continue

        buy_summary = item_data.get('buy_summary', [])
        sell_summary = item_data.get('sell_summary', [])

        if not buy_summary or not sell_summary:
            continue

        lowest_buy_price = buy_summary[0]['pricePerUnit']
        buy_volume = sum(b['amount'] for b in buy_summary)

        highest_sell_price = sell_summary[0]['pricePerUnit']
        sell_volume = sum(s['amount'] for s in sell_summary)

        if lowest_buy_price <= 0 or highest_sell_price <= 0:
            continue

        profit_margin = round(highest_sell_price - lowest_buy_price, 2)
        volume_ratio = min(buy_volume / 1000, 1)

        price_volatility = calculate_volatility(item_data)

        saturation_factor = calculate_market_saturation(item_data, bazaar_data)

        if price_volatility == 0:
            score = round((profit_margin * volume_ratio), 2) * (1 - saturation_factor)
        else:
            score = round((profit_margin * volume_ratio) / (price_volatility + 1) * (1 - saturation_factor), 2)

        capped_score = min(max(score, 0), 1000000000)

        scores.append({
            'item_id': item_id,
            'lowest_buy_price': round(lowest_buy_price, 2),
            'highest_sell_price': round(highest_sell_price, 2),
            'profit_margin': profit_margin,
            'buy_volume': round(buy_volume, 2),
            'sell_volume': round(sell_volume, 2),
            'price_volatility': round(price_volatility, 2),
            'saturation_factor': round(saturation_factor, 2),
            'score': capped_score
        })

    sort_by = request.args.get('sort_by', 'score')
    sort_order = request.args.get('sort_order', 'desc')
    reverse = (sort_order == 'desc')

    return sorted(scores, key=lambda x: x.get(sort_by, 0), reverse=reverse)

def calculate_volatility(item_data):
    buy_prices = [entry['pricePerUnit'] for entry in item_data.get('buy_summary', [])]
    sell_prices = [entry['pricePerUnit'] for entry in item_data.get('sell_summary', [])]
    prices = buy_prices + sell_prices
    
    if len(prices) < 2:
        return 0

    return round(np.std(prices), 2)
def calculate_market_saturation(item_data, bazaar_data):
    if not item_data.get('buy_summary') and not item_data.get('sell_summary'):
        print("Error: No buy or sell summary data available.")
        return 0

    total_market_volume = sum(
        sum(entry['amount'] for entry in item.get('buy_summary', [])) +
        sum(entry['amount'] for entry in item.get('sell_summary', []))
        for item in bazaar_data['products'].values()
    )

    item_volume = sum(entry['amount'] for entry in item_data.get('buy_summary', [])) + \
                  sum(entry['amount'] for entry in item_data.get('sell_summary', []))
    
    if total_market_volume <= 0:
        return 0

    saturation_factor = item_volume / total_market_volume

    scaling_factor = 1e6
    saturation_factor *= scaling_factor
    
    return saturation_factor

def generate_plot(item_data):
    fig = go.Figure()

    buy_prices = [entry['pricePerUnit'] for entry in item_data.get('buy_summary', [])]
    buy_volumes = [entry['amount'] for entry in item_data.get('buy_summary', [])]
    fig.add_trace(go.Scatter(x=buy_prices, y=buy_volumes, mode='markers', name='Buy Summary'))

    sell_prices = [entry['pricePerUnit'] for entry in item_data.get('sell_summary', [])]
    sell_volumes = [entry['amount'] for entry in item_data.get('sell_summary', [])]
    fig.add_trace(go.Scatter(x=sell_prices, y=sell_volumes, mode='markers', name='Sell Summary'))

    fig.update_layout(
        title='Buy and Sell Summary',
        xaxis_title='Price',
        yaxis_title='Volume',
        template='plotly_dark'
    )

    plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return plot_json

@app.route('/')
def index():
    bazaar_data = get_bazaar_data()
    if not bazaar_data:
        return "Data not available", 500
    profit_margins = calculate_advanced_score(bazaar_data)
    return render_template('index.html', profit_margins=profit_margins)

@app.route('/plot/<item_id>')
def plot_image(item_id):
    bazaar_data = get_bazaar_data()
    if not bazaar_data or 'products' not in bazaar_data:
        return "Data not available", 404
    
    item_data = bazaar_data['products'].get(item_id)
    if not item_data:
        return "Item not found", 404
    
    plot_json = generate_plot(item_data)
    return render_template('plot.html', plot_json=plot_json)

@app.route('/item/<item_id>')
def item_details(item_id):
    bazaar_data = get_bazaar_data()
    if not bazaar_data or 'products' not in bazaar_data:
        return "Data not available", 404

    all_scores = calculate_advanced_score(bazaar_data)

    item_score_data = next((item for item in all_scores if item['item_id'] == item_id), None)
    if not item_score_data:
        return "Item not found", 404

    item_data = bazaar_data['products'].get(item_id)
    if not item_data:
        return "Item not found", 404

    lowest_buy_price = float(item_data['buy_summary'][0]['pricePerUnit']) if 'buy_summary' in item_data and item_data['buy_summary'] else 0
    highest_sell_price = float(item_data['sell_summary'][0]['pricePerUnit']) if 'sell_summary' in item_data and item_data['sell_summary'] else 0
    buy_volume = float(sum(b['amount'] for b in item_data['buy_summary'])) if 'buy_summary' in item_data and item_data['buy_summary'] else 0
    sell_volume = float(sum(s['amount'] for s in item_data['sell_summary'])) if 'sell_summary' in item_data and item_data['sell_summary'] else 0

    profit_margin = round(highest_sell_price - lowest_buy_price, 2) if lowest_buy_price and highest_sell_price else 0
    score = item_score_data['score'] if item_score_data else 0

    capped_score = min(score, 999999) if isinstance(score, (int, float)) else 0

    item_data['lowest_buy_price'] = lowest_buy_price
    item_data['highest_sell_price'] = highest_sell_price
    item_data['buy_volume'] = buy_volume
    item_data['sell_volume'] = sell_volume
    item_data['profit_margin'] = profit_margin
    item_data['score'] = capped_score

    plot_json = generate_plot(item_data)
    
    return render_template('item_details.html', item_id=item_id, item_data=item_data, plot_json=plot_json)

@app.route('/suggestions')
def suggestions():
    bazaar_data = get_bazaar_data()
    if not bazaar_data or 'products' not in bazaar_data:
        return "Data not available", 404

    items = calculate_advanced_score(bazaar_data)
    suggestions = [{'item_id': item['item_id'], 'score': item['score'], 'suggestion': 'Suggestion based on score'} for item in items]
    
    return render_template('suggestions.html', suggestions=suggestions)

if __name__ == '__main__':
    app.run(debug=True)