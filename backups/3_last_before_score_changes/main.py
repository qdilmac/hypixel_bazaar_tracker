from flask import Flask, jsonify, render_template, request
import requests
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
import plotly
import plotly.graph_objects as go
import json

app = Flask(__name__)

# Replace 'YOUR_API_KEY' with your actual Hypixel API key
API_KEY = '99417da1-2ddf-49fc-aa73-f4fa3c62fa6d'
BAZAAR_API_URL = 'https://api.hypixel.net/skyblock/bazaar?key=' + API_KEY


def get_bazaar_data():
    try:
        response = requests.get(BAZAAR_API_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def calculate_profit_margin(bazaar_data):
    profit_margins = []
    if bazaar_data and 'products' in bazaar_data:
        for item_id, item_data in bazaar_data['products'].items():
            # Skip items with 'ENCHANTMENT' in their ID
            if "enchantment" in item_id.lower():
                continue

            # Get the lowest buy price and total buy volume
            if item_data['buy_summary']:
                lowest_buy_price = item_data['buy_summary'][0]['pricePerUnit']
                buy_volume = sum(b['amount'] for b in item_data['buy_summary'])
            else:
                lowest_buy_price = 0
                buy_volume = 0
            
            # Get the highest sell price and total sell volume
            if item_data['sell_summary']:
                highest_sell_price = item_data['sell_summary'][0]['pricePerUnit']
                sell_volume = sum(s['amount'] for s in item_data['sell_summary'])
            else:
                highest_sell_price = 0
                sell_volume = 0
            
            # Skip items with a zero or negative price
            if lowest_buy_price <= 0 or highest_sell_price <= 0:
                continue
            
            # Calculate profit margin
            profit_margin = -round(highest_sell_price - lowest_buy_price, 2)
            
            if profit_margin > 999999:
                continue
            
            # Normalize buy volume (cap to a maximum value)
            capped_buy_volume = min(buy_volume, 10000)  # Cap buy volume to 10,000

            # Calculate score with emphasis on buy volume
            score = round((capped_buy_volume / 10) + profit_margin, 2)
            
            # Cap the score to 999
            capped_score = min(score, 1000000000)
            
            # Append to results
            profit_margins.append({
                'item_id': item_id,
                'lowest_buy_price': round(lowest_buy_price, 2),
                'highest_sell_price': round(highest_sell_price, 2),
                'profit_margin': profit_margin,
                'buy_volume': round(buy_volume, 2),
                'sell_volume': round(sell_volume, 2),
                'score': capped_score
            })
    
    # Sorting by a specified column
    sort_by = request.args.get('sort_by', 'score')
    sort_order = request.args.get('sort_order', 'desc')
    reverse = (sort_order == 'desc')
    
    return sorted(profit_margins, key=lambda x: x.get(sort_by, 0), reverse=reverse)

def generate_plot(item_data):
    # Example plot using Plotly
    fig = go.Figure()

    # Add buy summary trace
    buy_prices = [entry['pricePerUnit'] for entry in item_data.get('buy_summary', [])]
    buy_volumes = [entry['amount'] for entry in item_data.get('buy_summary', [])]
    fig.add_trace(go.Scatter(x=buy_prices, y=buy_volumes, mode='markers', name='Buy Summary'))

    # Add sell summary trace
    sell_prices = [entry['pricePerUnit'] for entry in item_data.get('sell_summary', [])]
    sell_volumes = [entry['amount'] for entry in item_data.get('sell_summary', [])]
    fig.add_trace(go.Scatter(x=sell_prices, y=sell_volumes, mode='markers', name='Sell Summary'))

    # Update layout
    fig.update_layout(
        title='Buy and Sell Summary',
        xaxis_title='Price',
        yaxis_title='Volume',
        template='plotly_dark'
    )

    # Convert Plotly figure to JSON
    plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return plot_json

@app.route('/')
def index():
    bazaar_data = get_bazaar_data()
    profit_margins = calculate_profit_margin(bazaar_data)
    return render_template('index.html', profit_margins=profit_margins)

@app.route('/plot/<item_id>')
def plot_image(item_id):
    bazaar_data = get_bazaar_data()
    if not bazaar_data or 'products' not in bazaar_data:
        return "Data not available", 404
    
    item_data = bazaar_data['products'].get(item_id)
    if not item_data:
        return "Item not found", 404
    
    img_base64 = generate_plot(item_data)
    return render_template('plot.html', img_base64=img_base64)

@app.route('/item/<item_id>')
def item_details(item_id):
    bazaar_data = get_bazaar_data()
    if not bazaar_data or 'products' not in bazaar_data:
        return "Data not available", 404
    
    item_data = bazaar_data['products'].get(item_id)
    if not item_data:
        return "Item not found", 404

    # Calculate necessary values
    lowest_buy_price = float(item_data['buy_summary'][0]['pricePerUnit']) if 'buy_summary' in item_data and item_data['buy_summary'] else 0
    highest_sell_price = float(item_data['sell_summary'][0]['pricePerUnit']) if 'sell_summary' in item_data and item_data['sell_summary'] else 0
    buy_volume = float(sum(b['amount'] for b in item_data['buy_summary'])) if 'buy_summary' in item_data else 0
    sell_volume = float(sum(s['amount'] for s in item_data['sell_summary'])) if 'sell_summary' in item_data else 0

    profit_margin = round(highest_sell_price - lowest_buy_price, 2) if lowest_buy_price and highest_sell_price else 'N/A'
    score = round((buy_volume / 10) + profit_margin, 2) if isinstance(profit_margin, (int, float)) else 'N/A'
    
    # Cap the score to 999
    capped_score = min(score, 999) if isinstance(score, (int, float)) else 'N/A'

    item_data['profit_margin'] = profit_margin
    item_data['buy_volume'] = buy_volume
    item_data['sell_volume'] = sell_volume
    item_data['score'] = capped_score

    # Generate plot image as JSON
    plot_json = generate_plot(item_data)
    
    return render_template('item_details.html', item_id=item_id, item_data=item_data, plot_json=plot_json)

@app.route('/suggestions')
def suggestions():
    bazaar_data = get_bazaar_data()
    if not bazaar_data or 'products' not in bazaar_data:
        return "Data not available", 404

    items = calculate_profit_margin(bazaar_data)
    suggestions = [{'item_id': item['item_id'], 'score': item['score'], 'suggestion': 'Suggestion based on score'} for item in items]
    
    return render_template('suggestions.html', suggestions=suggestions)

if __name__ == '__main__':
    app.run(debug=True)