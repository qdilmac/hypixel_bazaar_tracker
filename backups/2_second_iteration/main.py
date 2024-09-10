from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

# Replace 'YOUR_API_KEY' with your actual Hypixel API key
API_KEY = 'key'
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
            profit_margin = round(highest_sell_price - lowest_buy_price, 2)
            
            if profit_margin > 999999:
                continue
            
            # Normalize buy volume (cap to a maximum value)
            capped_buy_volume = min(buy_volume, 10000)  # Cap buy volume to 10,000

            # Calculate score with emphasis on buy volume
            score = round((capped_buy_volume / 10) + profit_margin, 2)
            
            # Append to results
            profit_margins.append({
                'item_id': item_id,
                'lowest_buy_price': round(lowest_buy_price, 2),
                'highest_sell_price': round(highest_sell_price, 2),
                'profit_margin': profit_margin,
                'buy_volume': round(buy_volume, 2),
                'sell_volume': round(sell_volume, 2),
                'score': score
            })
    
    # Sorting by a specified column
    sort_by = request.args.get('sort_by', 'score')
    sort_order = request.args.get('sort_order', 'desc')
    reverse = (sort_order == 'desc')
    
    return sorted(profit_margins, key=lambda x: x.get(sort_by, 0), reverse=reverse)

@app.route('/')
def index():
    bazaar_data = get_bazaar_data()
    profit_margins = calculate_profit_margin(bazaar_data)
    return render_template('index.html', profit_margins=profit_margins)

if __name__ == '__main__':
    app.run(debug=True)
