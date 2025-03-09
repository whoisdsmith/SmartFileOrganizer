import pandas as pd
import numpy as np

# Create sales data
np.random.seed(42)

# Generate dates
dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')

# Create product categories and products
categories = ['Electronics', 'Furniture', 'Office Supplies', 'Clothing']
products = {
    'Electronics': ['Smartphone', 'Laptop', 'Tablet', 'Headphones', 'Monitor'],
    'Furniture': ['Desk', 'Chair', 'Bookshelf', 'Cabinet', 'Sofa'],
    'Office Supplies': ['Notebook', 'Pen Set', 'Stapler', 'Paper', 'Binder'],
    'Clothing': ['T-shirt', 'Jeans', 'Sweater', 'Socks', 'Jacket']
}

# Create regions and cities
regions = {
    'North': ['New York', 'Boston', 'Philadelphia'],
    'South': ['Atlanta', 'Miami', 'Dallas'],
    'West': ['Los Angeles', 'San Francisco', 'Seattle'],
    'Midwest': ['Chicago', 'Detroit', 'Minneapolis']
}

# Generate sales data
data = []
for _ in range(1000):
    date = np.random.choice(dates)
    category = np.random.choice(categories)
    product = np.random.choice(products[category])
    region_name = np.random.choice(list(regions.keys()))
    city = np.random.choice(regions[region_name])
    
    units_sold = np.random.randint(1, 20)
    unit_price = np.random.uniform(10, 1000)
    if category == 'Electronics':
        unit_price *= 2  # Electronics are more expensive
    
    total_sales = units_sold * unit_price
    discount = np.random.uniform(0, 0.3)
    
    data.append({
        'Date': date,
        'Category': category,
        'Product': product,
        'Region': region_name,
        'City': city,
        'Units Sold': units_sold,
        'Unit Price': round(unit_price, 2),
        'Total Sales': round(total_sales, 2),
        'Discount': round(discount, 2)
    })

# Create DataFrame
df = pd.DataFrame(data)

# Create a pivot table for a summary sheet
pivot = pd.pivot_table(
    df,
    values='Total Sales',
    index=['Category', 'Product'],
    columns='Region',
    aggfunc='sum',
    margins=True,
    margins_name='Grand Total'
)

# Save to Excel with multiple sheets
with pd.ExcelWriter('test_files/sales_data.xlsx') as writer:
    df.to_excel(writer, sheet_name='Sales Data', index=False)
    pivot.to_excel(writer, sheet_name='Sales by Region')
    
    # Create a summary sheet
    summary = pd.DataFrame({
        'Metric': ['Total Sales', 'Average Order Value', 'Total Units Sold', 'Number of Orders'],
        'Value': [
            f"${df['Total Sales'].sum():,.2f}",
            f"${df['Total Sales'].mean():,.2f}",
            f"{df['Units Sold'].sum():,}",
            f"{len(df):,}"
        ]
    })
    summary.to_excel(writer, sheet_name='Summary', index=False)

print("Excel file created: test_files/sales_data.xlsx")