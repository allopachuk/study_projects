from datetime import datetime, timedelta
import pandas as pd
import pandahouse as ph
import telegram
import matplotlib.pyplot as plt
import seaborn as sns
import io
import sys
import os

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

connection = {'host': 'https://clickhouse.lab.karpov.courses',
              'database':'simulator_20230120',
              'user':'student', 
              'password':'dpo_python_2020'
             }

default_args = {
    'owner': 'a-lopachuk',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2023, 2, 14),
               }
              
schedule_interval = '*/15 * * * *'

# функция поиска аномалий в данных (межквартильный размах)
def check_anomaly(data, metric, a=3, n=5):
    if metric == 'ctr':
            n = 8
    data['q25'] = data[metric].shift(1).rolling(n).quantile(0.25)
    data['q75'] = data[metric].shift(1).rolling(n).quantile(0.75)
    data['iqr'] = data['q75'] - data['q25']
    data['high'] = data['q75'] + a*data['iqr']
    data['low'] = data['q25'] - a*data['iqr']

    data['high'] = data['high'].rolling(n, center=True, min_periods=1).mean()
    data['low'] = data['low'].rolling(n, center=True, min_periods=1).mean()

    if data[metric].iloc[-1] < data['low'].iloc[-1] or data[metric].iloc[-1] > data['high'].iloc[-1]:
        is_alert = 1
    else:
        is_alert = 0
    return is_alert, data

@dag(default_args=default_args, schedule_interval=schedule_interval, catchup=False)
def lopachuk_task_8():
    
    @task()    
    # система алертов
    def run_alerts(chat=None):
        chat_id = chat or 80664476
        my_token = "6182429108:AAEo9eJoc-v1CopC7oVMRUJ7dCH3HGWqoH4"
        my_bot = telegram.Bot(token=my_token)
        
        query = '''SELECT *
                     FROM 
                         (SELECT toStartOfFifteenMinutes(time) AS ts,
                                 toDate(time) AS date,
                                 formatDateTime(ts, '%R') AS hm,
                                 COUNT(DISTINCT user_id) AS feed_users,
                                 countIf(user_id, action='view') AS views,
                                 countIf(user_id, action='like') AS likes,
                                 ROUND(likes / views, 2) AS ctr
                            FROM simulator_20230120.feed_actions
                           WHERE time >= today() - 1
                             AND time < toStartOfFifteenMinutes(now())
                        GROUP BY ts, date, hm) f
                     JOIN          
                        (SELECT toStartOfFifteenMinutes(time) AS ts,
                                toDate(time) AS date,
                                formatDateTime(ts, '%R') AS hm,
                                COUNT(DISTINCT user_id) AS messenger_users,
                                COUNT(user_id) AS messages
                           FROM simulator_20230120.message_actions
                          WHERE time >= today() - 1
                            AND time < toStartOfFifteenMinutes(now())
                       GROUP BY ts, date, hm) m
                    USING (ts, date, hm)
                 ORDER BY ts'''
        
        df = ph.read_clickhouse(query=query, connection=connection)
        
        metrics_list = ['feed_users', 'views', 'likes', 'ctr', 'messenger_users', 'messages']
        for metric in metrics_list:
            #print(metric)
            data = df[['ts', 'date', 'hm', metric]].copy()
            is_alert, data = check_anomaly(data, metric)

            if is_alert == 1:
                msg = f'''Метрика {metric}\nТекущее значение: {data[metric].iloc[-1]:.2f}\nОтклонение на {abs(1 - (data[metric].iloc[-1] / data[metric].iloc[-97])):.2%}\nСсылка на дашборд: https://superset.lab.karpov.courses/superset/dashboard/2835/'''

                sns.set(rc={'figure.figsize':(25, 10)})
                sns.set_style("white")
                ax = sns.lineplot(x=data['ts'], y=data[metric], label = 'metric')
                ax = sns.lineplot(x=data['ts'], y=data['high'], label = 'high')
                ax = sns.lineplot(x=data['ts'], y=data['low'], label = 'low')

                for ind, label in enumerate(ax.get_xticklabels()):
                    if ind % 2 == 0:
                        label.set_visible(True)
                    else:
                        label.set_visible(False)

                ax.set(xlabel='time')
                ax.set(ylabel='')
                ax.set_title(metric, fontsize=15)
                ax.set(ylim=(0, None))

                plot_object = io.BytesIO()
                ax.figure.savefig(plot_object)
                plot_object.seek(0)
                plot_object.name = f'{metric}.png'
                plt.close()

                my_bot.sendMessage(chat_id=chat_id, text=msg)                                                                                                    
                my_bot.sendPhoto(chat_id=chat_id, photo=plot_object)
        
    run_alerts()

lopachuk_task_8 = lopachuk_task_8()