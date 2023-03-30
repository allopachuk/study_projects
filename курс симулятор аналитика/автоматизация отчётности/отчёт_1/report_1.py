from datetime import datetime, timedelta
import pandas as pd
import pandahouse as ph
import telegram
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io

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
    'start_date': datetime(2023, 2, 10),
}
              
schedule_interval = '0 11 * * *'

@dag(default_args=default_args, schedule_interval=schedule_interval, catchup=False)
def lopachuk_task_7_1():
    
    # формируем отчёт
    
    @task()
    def report(chat=None):
        chat_id = chat or 80664476  # chat-id личной переписки с телеграм-ботом

        my_token = "6182429108:AAEo9eJoc-v1CopC7oVMRUJ7dCH3HGWqoH4"
        my_bot = telegram.Bot(token=my_token)
        
        # запрос таблицы с нужными метриками
        
        query = '''SELECT toDate(time) AS date,
                          COUNT(DISTINCT user_id) AS users,
                          countIf(user_id, action='view') AS views,
                          countIf(user_id, action='like') AS likes,
                          likes / views AS ctr
                     FROM simulator_20230120.feed_actions
                    WHERE toDate(time) >= toDate(now()) - 7
                      AND toDate(time) < toDate(now())
                 GROUP BY toDate(time)
                 ORDER BY toDate(time)'''
        
        df = ph.read_clickhouse(query=query, connection=connection)
        
        # формируем текст сообщения
        
        date = df._get_value(6, 'date').strftime('%d.%m.%Y')
        
        dau = df._get_value(6, 'users', takeable=False)
        views = df._get_value(6, 'views', takeable=False)
        likes = df._get_value(6, 'likes', takeable=False)      
        ctr = round(df._get_value(6, 'ctr', takeable=False), 4)
        
        msg = f'Значения ключевых метрик за {date}\n\nDAU: {dau}\nПросмотры: {views}\nЛайки: {likes}\nCTR: {ctr}'
        my_bot.sendMessage(chat_id=chat_id, text=msg)

        # формируем картинку с графиками
        
        df['date'] = df['date'].dt.strftime('%d.%m')

        sns.set(rc={'figure.figsize':(25,10)})
        sns.set_style("white")

        plt.subplot(221)
        sns.lineplot(data=df, x='date', y='users')
        plt.title('DAU', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.subplot(222)
        sns.lineplot(data=df, x='date', y='views')
        plt.title('Просмотры', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.subplot(223)
        sns.lineplot(data=df, x='date', y='likes')
        plt.title('Лайки', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.subplot(224)
        sns.lineplot(data=df, x='date', y='ctr')
        plt.title('CTR', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.suptitle("Графики со значениями метрик за предыдущие 7 дней", fontsize=20)
        plt.subplots_adjust(hspace = 0.4)

        plot = io.BytesIO()
        plt.savefig(plot)
        plot.seek(0)
        plot.name = 'plot.png'
        plt.close()
        my_bot.sendPhoto(chat_id=chat_id, photo=plot)
        
    report()

lopachuk_task_7_1 = lopachuk_task_7_1()