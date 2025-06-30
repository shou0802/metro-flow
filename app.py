
from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.io as pio
import uuid

app = Flask(__name__)
DATA_PATH = 'data'
df = pd.read_csv(f'{DATA_PATH}/metro_hourly_flow_2024.csv')
station_info = pd.read_csv(f'{DATA_PATH}/station_info.csv')

# 處理日期欄
if 'date' not in df.columns and '日期' in df.columns:
    df['date'] = pd.to_datetime(df['日期'])
else:
    df['date'] = pd.to_datetime(df['date'])

df['month'] = df['date'].dt.month
df['weekday'] = df['date'].dt.weekday
df['is_weekend'] = df['weekday'] >= 5

@app.route('/', methods=['GET', 'POST'])
def index():
    months = list(range(1, 13))
    districts = sorted(station_info['district'].unique())
    return render_template('index.html', months=months, districts=districts)

@app.route('/result', methods=['POST'])
def result():
    selected_months = list(map(int, request.form.getlist('month')))
    selected_districts = request.form.getlist('district')
    day_type = request.form['day_type']

    filtered = df[df['month'].isin(selected_months)]
    if selected_districts:
        filtered = filtered[filtered['district'].isin(selected_districts)]
    if day_type != 'all':
        filtered = filtered[filtered['is_weekend'] == (day_type == 'holiday')]

    day_label = {
        "all": "全部日",
        "weekday": "平日",
        "holiday": "假日"
    }[day_type]

    station_avg = (
        filtered.groupby('station_name')[['entry_count', 'exit_count']]
        .mean()
        .round(0)
        .astype(int)
        .reset_index()
        .sort_values('entry_count', ascending=False)
    )

    # 改中文欄位名稱
    station_avg.columns = ['車站名稱', '平均進站人數', '平均出站人數']

    # 數字加上千位逗號
    station_avg['平均進站人數'] = station_avg['平均進站人數'].map('{:,}'.format)
    station_avg['平均出站人數'] = station_avg['平均出站人數'].map('{:,}'.format)

    # 產出 HTML 表格，加入 table id 供 DataTables 使用
    table_html = station_avg.to_html(
        index=False,
        classes='table table-bordered table-hover align-middle text-center',
        table_id='resultTable'
    )

    # 折線圖（Plotly）
    top5_stations = station_avg['車站名稱'].head(5).tolist()
    hourly = (
        filtered.groupby(['hour', 'station_name'])[['entry_count', 'exit_count']]
        .mean()
        .reset_index()
    )
    hourly_plot = hourly[hourly['station_name'].isin(top5_stations)]

    entry_df = hourly_plot.copy()
    entry_df['type'] = '進站人數（實線）'
    entry_df['value'] = entry_df['entry_count']

    exit_df = hourly_plot.copy()
    exit_df['type'] = '出站人數（虛線）'
    exit_df['value'] = exit_df['exit_count']

    combined_df = pd.concat([entry_df, exit_df], axis=0)

    fig = px.line(
        combined_df,
        x="hour",
        y="value",
        color="station_name",
        line_dash="type",
        markers=True,
        title=f"各站每小時平均進出站人數（{day_label}）",
        labels={"value": "人數", "hour": "時間（時）", "station_name": "站名"},
    )
    fig.update_layout(
        legend_title="站名與類型",
        xaxis=dict(dtick=1),
        height=600
    )

    plot_html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

    return render_template(
        'result.html',
        table=table_html,
        plot_html=plot_html,
        day_label=day_label,
        selected_months=selected_months,
        selected_districts=selected_districts
    )

if __name__ == '__main__':
    app.run(debug=True)

