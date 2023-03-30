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
    'start_date': datetime(2023, 2, 14),
               }
              
schedule_interval = '0 11 * * *'

@dag(default_args=default_args, schedule_interval=schedule_interval, catchup=False)
def lopachuk_task_7_2():
    
    # формируем отчёт
    
    @task()
    def report(chat=None):
        chat_id = chat or 80664476  # chat-id личной переписки с телеграм-ботом

        my_token = "6182429108:AAEo9eJoc-v1CopC7oVMRUJ7dCH3HGWqoH4"
        my_bot = telegram.Bot(token=my_token)
        
        # СБОР ДАННЫХ
        
        # DAU всего приложения
        
        query_all_dau = '''SELECT date,
                                  COUNT(DISTINCT user_id) AS users,
                                  countIf(DISTINCT user_id, os='Android') AS android,
                                  countIf(DISTINCT user_id, os='iOS') AS ios,
                                  countIf(DISTINCT user_id, source='ads') AS ads,
                                  countIf(DISTINCT user_id, source='organic') AS organic
                             FROM (
                                  SELECT DISTINCT toDate(time) AS date, user_id, os, source
                                    FROM simulator_20230120.feed_actions
                                   WHERE toDate(time) >= toDate(now()) - 8
                                     AND toDate(time) < toDate(now())
                               UNION ALL
                                  SELECT DISTINCT toDate(time) AS date, user_id, os, source
                                    FROM simulator_20230120.message_actions
                                   WHERE toDate(time) >= toDate(now()) - 8
                                     AND toDate(time) < toDate(now())
                                   ) t
                         GROUP BY date
                         ORDER BY date'''
        
        df_all_dau = ph.read_clickhouse(query=query_all_dau, connection=connection)
        
        # информация о пользователях
        
        query_all = '''SELECT multiIf(age < 18, '< 18', age < 25, '18 - 24', 
                                      age < 35, '25 - 34', age < 45, '35 - 44', 
                                      age <= 55, '45 - 55', '> 55') AS age, 
                              multiIf(gender = 0, 'ж', 'м') AS gender, 
                              COUNT(user_id) AS users
                        FROM (
                              SELECT DISTINCT user_id, gender, age
                                FROM (
                                      SELECT DISTINCT user_id, gender, age
                                        FROM simulator_20230120.feed_actions
                                       WHERE toDate(time) = toDate(now()) - 1
                                   UNION ALL
                                      SELECT DISTINCT user_id, gender, age
                                        FROM simulator_20230120.message_actions
                                       WHERE toDate(time) = toDate(now()) - 1
                                     ) t
                              ) t1
                      GROUP BY age, gender
                      ORDER BY age, gender'''
        
        df_all = ph.read_clickhouse(query=query_all, connection=connection)
        
        # число новых пользователей всего приложения и процент "рекламных" пользователей
        
        query_all_new = '''SELECT date, COUNT(DISTINCT user_id) as users, 
                                  ROUND(countIf(source='ads') / users * 100) AS ads_users
                             FROM (
                                  SELECT user_id, source, MIN(start_date) as date
                                    FROM (
                                         SELECT user_id, source, MIN(toDate(time)) AS start_date
                                           FROM simulator_20230120.feed_actions
                                       GROUP BY user_id, source
                                      UNION ALL 
                                         SELECT user_id, source, MIN(toDate(time)) AS start_date
                                           FROM simulator_20230120.message_actions
                                       GROUP BY user_id, source
                                         ) as t1
                                GROUP BY user_id, source) as t2
                            WHERE date >= toDate(now()) - 8
                              AND date < toDate(now())
                         GROUP BY date
                         ORDER BY date'''
        
        df_all_new = ph.read_clickhouse(query=query_all_new, connection=connection)
        
        # процент пользователей, пришедших неделю назад и оставшихся в приложении
        
        query_all_retention_p = '''SELECT ROUND(
                                               (SELECT COUNT(DISTINCT user_id) AS users
                                                  FROM
                                                      (
                                                      SELECT DISTINCT user_id
                                                        FROM simulator_20230120.feed_actions
                                                       WHERE user_id IN (
                                                                        SELECT user_id
                                                                          FROM simulator_20230120.feed_actions
                                                                      GROUP BY user_id
                                                                        HAVING MIN(toDate(time)) = toDate(now()) - 8
                                                                        )
                                                        AND toDate(time) = toDate(now()) - 1
                                                  UNION ALL
                                                     SELECT DISTINCT user_id
                                                       FROM simulator_20230120.message_actions
                                                      WHERE user_id IN (
                                                                       SELECT user_id
                                                                         FROM simulator_20230120.message_actions
                                                                     GROUP BY user_id
                                                                       HAVING MIN(toDate(time)) = toDate(now()) - 8
                                                                       )
                                                       AND toDate(time) = toDate(now()) - 1
                                                      )
                                                ) /
                                                (SELECT COUNT(DISTINCT user_id) AS users
                                                   FROM
                                                       (
                                                       SELECT user_id, source
                                                         FROM simulator_20230120.feed_actions
                                                     GROUP BY user_id, source
                                                       HAVING MIN(toDate(time)) = toDate(now()) - 8
                                                    UNION ALL
                                                       SELECT user_id, source
                                                         FROM simulator_20230120.message_actions
                                                     GROUP BY user_id, source
                                                       HAVING MIN(toDate(time)) = toDate(now()) - 8
                                                       )
                                                ) * 100
                                                ) AS p'''
        
        df_all_retention_p = ph.read_clickhouse(query=query_all_retention_p, connection=connection)
        
        # информация о пользователях ленты
        
        query_feed = '''SELECT toDate(time) AS date,
                               COUNT(DISTINCT user_id) AS users,
                               countIf(user_id, action='view') AS views,
                               countIf(user_id, action='like') AS likes,
                               ROUND(likes / views, 2) AS ctr,
                               ROUND(views / users, 2) AS views_per_user,
                               ROUND(likes / users, 2) AS likes_per_user
                          FROM simulator_20230120.feed_actions
                         WHERE toDate(time) >= toDate(now()) - 8
                           AND toDate(time) < toDate(now())
                      GROUP BY toDate(time)
                      ORDER BY date'''
        
        df_feed = ph.read_clickhouse(query=query_feed, connection=connection)
        
        # информация о пользователях мессенджера
        
        query_messenger = '''SELECT toDate(time) AS date,
                                    COUNT(DISTINCT user_id) AS users,
                                    COUNT(*) AS messages,
                                    ROUND(messages / users, 2) AS messages_per_user
                               FROM simulator_20230120.message_actions
                              WHERE toDate(time) >= toDate(now()) - 8
                                AND toDate(time) < toDate(now())
                           GROUP BY toDate(time)
                           ORDER BY date'''
        
        df_messenger = ph.read_clickhouse(query=query_messenger, connection=connection)
        
        # формируем текст сообщения
        
        date = df_all_dau._get_value(7, 'date').strftime('%d.%m.%Y')
        
        dau_all = int(df_all_dau._get_value(7, 'users', takeable=False))
        dau_all_day_ago = int(df_all_dau._get_value(6, 'users', takeable=False))
        dau_all_week_ago = int(df_all_dau._get_value(0, 'users', takeable=False))
        dau_day_growth = round((dau_all - dau_all_day_ago) / dau_all_day_ago * 100, 1)
        dau_week_growth = round((dau_all - dau_all_week_ago) / dau_all_week_ago * 100, 1)
        
        new_users = int(df_all_new._get_value(7, 'users', takeable=False))
        new_users_day_ago = int(df_all_new._get_value(6, 'users', takeable=False))
        new_users_week_ago = int(df_all_new._get_value(0, 'users', takeable=False))
        new_users_day_growth = round((new_users - new_users_day_ago) / new_users_day_ago * 100, 1)
        new_users_week_growth = round((new_users - new_users_week_ago) / new_users_week_ago * 100, 1)
        ads_users = df_all_new._get_value(7, 'ads_users', takeable=False)
        
        retention_p = df_all_retention_p._get_value(0, 'p', takeable=False)
        
        dau_android = int(df_all_dau._get_value(7, 'android', takeable=False))
        dau_android_day_ago = int(df_all_dau._get_value(6, 'android', takeable=False))
        dau_android_week_ago = int(df_all_dau._get_value(0, 'android', takeable=False))
        dau_ios = int(df_all_dau._get_value(7, 'ios', takeable=False))
        dau_ios_day_ago = int(df_all_dau._get_value(6, 'ios', takeable=False))
        dau_ios_week_ago = int(df_all_dau._get_value(0, 'ios', takeable=False))
        dau_android_day_growth = round((dau_android - dau_android_day_ago) / dau_android_day_ago * 100, 1)
        dau_android_week_growth = round((dau_android - dau_android_week_ago) / dau_android_week_ago * 100, 1)
        dau_ios_day_growth = round((dau_ios - dau_ios_day_ago) / dau_ios_day_ago * 100, 1)
        dau_ios_week_growth = round((dau_ios - dau_ios_week_ago) / dau_ios_week_ago * 100, 1)
        
        dau_feed = int(df_feed._get_value(7, 'users', takeable=False))
        dau_feed_day_ago = int(df_feed._get_value(6, 'users', takeable=False))
        dau_feed_week_ago = int(df_feed._get_value(0, 'users', takeable=False))
        dau_feed_day_growth = round((dau_feed - dau_feed_day_ago) / dau_feed_day_ago * 100, 1)
        dau_feed_week_growth = round((dau_feed - dau_feed_week_ago) / dau_feed_week_ago * 100, 1)
        
        views = int(df_feed._get_value(7, 'views', takeable=False))
        views_day_ago = int(df_feed._get_value(6, 'views', takeable=False))
        views_week_ago = int(df_feed._get_value(0, 'views', takeable=False))
        views_day_growth = round((views - views_day_ago) / views_day_ago * 100, 1)
        views_week_growth = round((views - views_week_ago) / views_week_ago * 100, 1)
        
        likes = int(df_feed._get_value(7, 'likes', takeable=False))
        likes_day_ago = int(df_feed._get_value(6, 'likes', takeable=False))
        likes_week_ago = int(df_feed._get_value(0, 'likes', takeable=False))
        likes_day_growth = round((likes - likes_day_ago) / likes_day_ago * 100, 1)
        likes_week_growth = round((likes - likes_week_ago) / likes_week_ago * 100, 1)
        
        ctr = float(df_feed._get_value(7, 'ctr', takeable=False))
        ctr_day_ago = float(df_feed._get_value(6, 'ctr', takeable=False))
        ctr_week_ago = float(df_feed._get_value(0, 'ctr', takeable=False))
        ctr_day_growth = round((ctr - ctr_day_ago) / ctr_day_ago * 100, 1)
        ctr_week_growth = round((ctr - ctr_week_ago) / ctr_week_ago * 100, 1)
        
        views_per_user = float(df_feed._get_value(7, 'views_per_user', takeable=False))
        views_per_user_day_ago = float(df_feed._get_value(6, 'views_per_user', takeable=False))
        views_per_user_week_ago = float(df_feed._get_value(0, 'views_per_user', takeable=False))
        views_per_user_day_growth = round((views_per_user - views_per_user_day_ago) / views_per_user_day_ago * 100, 1)
        views_per_user_week_growth = round((views_per_user - views_per_user_week_ago) / views_per_user_week_ago * 100, 1)
        
        likes_per_user = float(df_feed._get_value(7, 'likes_per_user', takeable=False))
        likes_per_user_day_ago = float(df_feed._get_value(6, 'likes_per_user', takeable=False))
        likes_per_user_week_ago = float(df_feed._get_value(0, 'likes_per_user', takeable=False))
        likes_per_user_day_growth = round((likes_per_user - likes_per_user_day_ago) / likes_per_user_day_ago * 100, 1)
        likes_per_user_week_growth = round((likes_per_user - likes_per_user_week_ago) / likes_per_user_week_ago * 100, 1)
        
        dau_messenger = int(df_messenger._get_value(7, 'users', takeable=False))
        dau_messenger_day_ago = int(df_messenger._get_value(6, 'users', takeable=False))
        dau_messenger_week_ago = int(df_messenger._get_value(0, 'users', takeable=False))
        dau_messenger_day_growth = round((dau_messenger - dau_messenger_day_ago) / dau_messenger_day_ago * 100, 1)
        dau_messenger_week_growth = round((dau_messenger - dau_messenger_week_ago) / dau_messenger_week_ago * 100, 1)
        
        messages = int(df_messenger._get_value(7, 'messages', takeable=False))
        messages_day_ago = int(df_messenger._get_value(6, 'messages', takeable=False))
        messages_week_ago = int(df_messenger._get_value(0, 'messages', takeable=False))
        messages_day_growth = round((messages - messages_day_ago) / messages_day_ago * 100, 1)
        messages_week_growth = round((messages - messages_week_ago) / messages_week_ago * 100, 1)
        
        messages_per_user = float(df_messenger._get_value(7, 'messages_per_user', takeable=False))
        messages_per_user_day_ago = float(df_messenger._get_value(6, 'messages_per_user', takeable=False))
        messages_per_user_week_ago = float(df_messenger._get_value(0, 'messages_per_user', takeable=False))
        messages_per_user_day_growth = round((messages_per_user - messages_per_user_day_ago) / messages_per_user_day_ago * 100, 1)
        messages_per_user_week_growth = round((messages_per_user - messages_per_user_week_ago) / messages_per_user_week_ago * 100, 1)
        
        msg = f'''
Отчёт по приложению за {date}

ОБЩИЕ ДАННЫЕ

Пользователи (DAU): {dau_all} ({dau_day_growth}% за день, {dau_week_growth}% за неделю)
Новые пользователи: {new_users}, из них {ads_users}% пришли по рекламе ({new_users_day_growth}% за день, {new_users_week_growth}% за неделю)
Retention: {retention_p}% пользователей, пришедших неделю назад, воспользовались приложением
Используют Android: {dau_android} ({dau_android_day_growth}% за день, {dau_android_week_growth}% за неделю)
Используют iOS: {dau_ios} ({dau_ios_day_growth}% за день, {dau_ios_week_growth}% за неделю)
                  
ДАННЫЕ О ЛЕНТЕ

Пользователи (DAU): {dau_feed} ({dau_feed_day_growth}% за день, {dau_feed_week_growth}% за неделю)
Просмотры: {views} ({views_day_growth}% за день, {views_week_growth}% за неделю)
Лайки: {likes} ({likes_day_growth}% за день, {likes_week_growth}% за неделю)
CTR: {ctr} ({ctr_day_growth}% за день, {ctr_week_growth}% за неделю)
Число просмотров на пользователя: {views_per_user} ({views_per_user_day_growth}% за день, {views_per_user_week_growth}% за неделю)
Число лайков на пользователя: {likes_per_user} ({likes_per_user_day_growth}% за день, {likes_per_user_week_growth}% за неделю)

ДАННЫЕ О МЕССЕНДЖЕРЕ

Пользователи (DAU): {dau_messenger} ({dau_messenger_day_growth}% за день, {dau_messenger_week_growth}% за неделю)
Число отправленных сообщений: {messages} ({messages_day_growth}% за день, {messages_week_growth}% за неделю)
Число сообщений на пользователя: {messages_per_user} ({messages_per_user_day_growth}% за день, {messages_per_user_week_growth}% за неделю)

Графики представлены ниже
'''
        my_bot.sendMessage(chat_id=chat_id, text=msg)

        # формируем картинки с графиками
        
        sns.set(rc={'figure.figsize':(25, 10)})
        sns.set_style("white")

        df_all_dau['date'] = df_all_dau['date'].dt.strftime('%d.%m')
        df_feed['date'] = df_feed['date'].dt.strftime('%d.%m')
        df_messenger['date'] = df_messenger['date'].dt.strftime('%d.%m')

        # DAU всего приложения за 7 дней

        sns.lineplot(data=df_all_dau, x='date', y='users')
        plt.title('Пользователи приложения', fontsize=20)
        plt.xlabel('')
        plt.ylabel('')
        plt.xticks(fontsize=15)
        plt.yticks(fontsize=15)

        plot = io.BytesIO()
        plt.savefig(plot)
        plot.seek(0)
        plot.name = 'dau.png'
        plt.close()

        my_bot.sendPhoto(chat_id=chat_id, photo=plot)

        # DAU по source за 7 дней

        df_all_dau.plot(x="date", y=["ads", "organic"], kind="bar")
        plt.title('Пользователи приложения по источнику', fontsize=20)
        plt.xlabel('')
        plt.ylabel('')
        plt.xticks(rotation=45, fontsize=15)
        plt.yticks(fontsize=15)
        plt.legend(fontsize="large")

        plot = io.BytesIO()
        plt.savefig(plot)
        plot.seek(0)
        plot.name = 'dau_source.png'
        plt.close()

        my_bot.sendPhoto(chat_id=chat_id, photo=plot)

        # DAU по os за 7 дней

        df_all_dau.plot(x="date", y=["android", "ios"], kind="bar")
        plt.title('Пользователи приложения по OS', fontsize=20)
        plt.xlabel('')
        plt.ylabel('')
        plt.xticks(rotation=45, fontsize=15)
        plt.yticks(fontsize=15)
        plt.legend(fontsize="large")

        plot = io.BytesIO()
        plt.savefig(plot)
        plot.seek(0)
        plot.name = 'dau_os.png'
        plt.close()

        my_bot.sendPhoto(chat_id=chat_id, photo=plot)

        # DAU по gender и age за вчера

        sns.barplot(data=df_all, x="age", y="users", hue="gender")
        plt.title(f'Пользователи приложения по полу и возрасту за {date}', fontsize=20)
        plt.xlabel('')
        plt.ylabel('')
        plt.xticks(fontsize=15)
        plt.yticks(fontsize=15)
        plt.legend(fontsize="large")

        plot = io.BytesIO()
        plt.savefig(plot)
        plot.seek(0)
        plot.name = 'dau_age.png'
        plt.close()

        my_bot.sendPhoto(chat_id=chat_id, photo=plot)

        # DAU ленты за 7 дней

        plt.subplot(231)
        sns.lineplot(data=df_feed, x='date', y='users')
        plt.title('Пользователи ленты', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        # Просмотры и лайки за 7 дней

        plt.subplot(232)
        sns.lineplot(data=df_feed, x='date', y='views')
        plt.title('Просмотры', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.subplot(233)
        sns.lineplot(data=df_feed, x='date', y='likes')
        plt.title('Лайки', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        # CTR

        plt.subplot(234)
        sns.lineplot(data=df_feed, x='date', y='ctr')
        plt.title('CTR', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        # Число просмотров и лайков на пользователя

        plt.subplot(235)
        sns.lineplot(data=df_feed, x='date', y='views_per_user')
        plt.title('Число просмотров на пользователя', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.subplot(236)
        sns.lineplot(data=df_feed, x='date', y='likes_per_user')
        plt.title('Число лайков на пользователя', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.suptitle("Метрики ленты", fontsize=20)
        plt.subplots_adjust(hspace = 0.4)

        plot = io.BytesIO()
        plt.savefig(plot)
        plot.seek(0)
        plot.name = 'feed_plots.png'
        plt.close()

        my_bot.sendPhoto(chat_id=chat_id, photo=plot)

        # DAU мессенджера за 7 дней

        plt.subplot(131)
        sns.lineplot(data=df_messenger, x='date', y='users')
        plt.title('Пользователи мессенджера', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        # Число отправленных сообщений

        plt.subplot(132)
        sns.lineplot(data=df_messenger, x='date', y='messages')
        plt.title('Число отправленных сообщений', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        # Число сообщений на пользователя

        plt.subplot(133)
        sns.lineplot(data=df_messenger, x='date', y='messages_per_user')
        plt.title('Число сообщений на пользователя', fontsize=15)
        plt.xlabel('')
        plt.ylabel('')

        plt.suptitle("Метрики мессенджера", fontsize=20)
        plt.subplots_adjust(hspace = 0.4)

        plot = io.BytesIO()
        plt.savefig(plot)
        plot.seek(0)
        plot.name = 'mess_plots.png'
        plt.close()

        my_bot.sendPhoto(chat_id=chat_id, photo=plot)
   
    report()

lopachuk_task_7_2 = lopachuk_task_7_2()