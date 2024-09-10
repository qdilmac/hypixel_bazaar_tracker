from flask import Flask, jsonify, render_template
import requests

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
            # Get the lowest buy price (buying price)
            buy_prices = [b['pricePerUnit'] for b in item_data['buy_summary']]
            lowest_buy_price = min(buy_prices, default=0)
            
            # Get the highest sell price (selling price)
            sell_prices = [s['pricePerUnit'] for s in item_data['sell_summary']]
            highest_sell_price = max(sell_prices, default=0)
            
            # Skip items with a zero or negative price
            if lowest_buy_price <= 0 or highest_sell_price <= 0:
                continue
            
            # Calculate profit margin
            profit_margin = lowest_buy_price - highest_sell_price
            
            if profit_margin > 999999:
                continue
            
            # Append to results
            profit_margins.append({
                'item_id': item_id,
                'lowest_buy_price': lowest_buy_price,
                'highest_sell_price': highest_sell_price,
                'profit_margin': profit_margin
            })
    
    # Sort by profit margin in descending order
    return sorted(profit_margins, key=lambda x: x['profit_margin'], reverse=True)

@app.route('/')
def index():
    bazaar_data = get_bazaar_data()
    profit_margins = calculate_profit_margin(bazaar_data)
    return render_template('index.html', profit_margins=profit_margins)

if __name__ == '__main__':
    app.run(debug=True)