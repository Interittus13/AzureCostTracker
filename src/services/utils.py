from datetime import datetime, timedelta, timezone

# Returns YYYY-MM-DD
def format_date(date):
    return date.strftime("%Y-%m-%d")

def get_forecast_date(start_date):
    today = datetime.now(timezone.utc)
    if today.day >= start_date:
        first_day = today.replace(day=start_date)
        last_day = (first_day + timedelta(days=32)).replace(day=start_date) - timedelta(days=1)
        return first_day, last_day
    else:
        first_day = (today.replace(day=start_date) - timedelta(days=32)).replace(day=start_date)
        last_day = today.replace(day=start_date) - timedelta(days=1)
        return first_day, last_day

def calculate_cost(cost_data):
    total_cost = sum(item[0] for item in cost_data.get("properties", {}).get("rows", []) if isinstance(item[0], (int, float)))
    return total_cost

def print_cost_breakdown(cost_data):
    # print(f"\n🔹 {date_label} Cost Report {subscription_name}🔹")
    # print("=" * 40)

    total_rows = ""
    total_cost = 0.0
    rows = cost_data.get("properties", {}).get("rows", [])
    sorted_rows = sorted(rows, key=lambda x: float(x[0]), reverse=True)
    
    for item in sorted_rows:
        # Ensure proper unpacking and handle missing service names
        if len(item) < 4:
            continue

        cost, _, service_name, currency = item[:4]
        total_cost += cost if isinstance(cost, (int, float)) else 0

        total_rows += f"<tr><td>{service_name}</td><td>${cost:.2f} {currency}</td></tr>"

    return total_rows, total_cost
