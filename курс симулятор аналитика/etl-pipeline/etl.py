from datetime import datetime, timedelta
import pandas as pd
import pandahouse as ph

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

connection = {'host': 'https://clickhouse.lab.karpov.courses',
                      'database':'simulator_20230120',
                      'user':'student', 
                      'password':'dpo_python_2020'
                     }

connection_test = {'host': 'https://clickhouse.lab.karpov.courses',
                      'database':'test',
                      'user':'student-rw', 
                      'password':'656e2b0c9c'
                     }

default_args = {
    'owner': 'a-lopachuk',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2023, 2, 11),
}
              
schedule_interval = '0 12 * * *'

@dag(default_args=default_args, schedule_interval=schedule_interval, catchup=False)
def lopachuk_etl():
    
    # для каждого пользователя в message_actions считаем, сколько он получил и отослал сообщений, скольким людям он писал, сколько людей писали ему
    
    @task()
    def extract_m():
        query = """WITH all_id AS (
                   SELECT DISTINCT toDate(time) AS event_date, user_id, gender, age, os
                     FROM simulator_20230120.message_actions
                    WHERE toDate(time) = toDate(now()) - 1
                UNION ALL
                   SELECT DISTINCT toDate(time) AS event_date, user_id, gender, age, os
                     FROM simulator_20230120.feed_actions
                    WHERE toDate(time) = toDate(now()) - 1
                                  )

                   SELECT DISTINCT t1.event_date AS event_date, t1.user_id AS user_id, t1.gender AS gender, t1.age AS age, t1.os AS os, 
                                   t2.messages_sent AS messages_sent, t2.users_sent AS users_sent, 
                                   t3.messages_received AS messages_received, t3.users_received AS users_received
                     FROM (SELECT DISTINCT event_date, user_id, gender, age, os FROM all_id) t1
                LEFT JOIN (SELECT user_id, COUNT(user_id) AS messages_sent, COUNT(DISTINCT reciever_id) AS users_sent
                             FROM simulator_20230120.message_actions
                            WHERE toDate(time) = toDate(now()) - 1
                         GROUP BY user_id) t2
                       ON t1.user_id = t2.user_id
                LEFT JOIN (SELECT reciever_id, COUNT(reciever_id) AS messages_received, COUNT(DISTINCT user_id) AS users_received
                             FROM simulator_20230120.message_actions
                            WHERE toDate(time) = toDate(now()) - 1
                         GROUP BY reciever_id) t3
                       ON t1.user_id = t3.reciever_id"""
        df_m = ph.read_clickhouse(query=query, connection=connection)
        return df_m
    
    # для каждого пользователя в feed_actions считаем, сколько постов он посмотрел и сколько лайков поставил
    
    @task()
    def extract_f():
        query = """SELECT user_id, countIf(action='view') AS views, countIf(action='like') AS likes
                     FROM simulator_20230120.feed_actions
                    WHERE toDate(time) = toDate(now()) - 1 
                 GROUP BY user_id"""
        df_f = ph.read_clickhouse(query=query, connection=connection)
        return df_f
    
    # объединяем две таблицы в одну
    
    @task
    def transfrom_join(df_m, df_f):
        df = pd.merge(df_m, df_f, how = 'left', on = ['user_id'])
        df.fillna(0, inplace=True)
        return df
    
    # метрики в разрезе по полу
    
    @task
    def transform_gender(df):
        df_gender = df[['event_date', 'gender', 'messages_sent', 'users_sent', 'messages_received', 'users_received', 'views', 'likes']]\
        .groupby(['event_date', 'gender'])\
        .sum()\
        .reset_index()
        df_gender['dimension'] = 'gender'
        df_gender.rename(columns={'gender': 'dimension_value'}, inplace=True)
        return df_gender
    
    # метрики в разрезе по ос
    
    @task
    def transform_os(df):
        df_os = df[['event_date', 'os', 'messages_sent', 'users_sent', 'messages_received', 'users_received', 'views', 'likes']]\
        .groupby(['event_date', 'os'])\
        .sum()\
        .reset_index()
        df_os['dimension'] = 'os'
        df_os.rename(columns={'os': 'dimension_value'}, inplace=True)
        return df_os
    
    # метрики в разрезе по возрасту
    
    @task
    def transform_age(df):
        df['age_gr'] = df['age'].apply(lambda x: '< 18' if x < 18
                                            else ('18-24' if x < 25 
                                            else ('25-34' if x < 35 
                                            else ('35-44' if x < 45 
                                            else ('45-55' if x <= 55
                                            else ('> 55'))))))
        df_age = df[['event_date', 'age_gr', 'messages_sent', 'users_sent', 'messages_received', 'users_received', 'views', 'likes']]\
        .groupby(['event_date', 'age_gr'])\
        .sum()\
        .reset_index()
        df_age['dimension'] = 'age'
        df_age.rename(columns={'age_gr': 'dimension_value'}, inplace=True)
        return df_age
    
    # создаём таблицу в БД и записываем данные
    
    @task
    def load(df_gender, df_os, df_age):
        create_table = """
            CREATE TABLE IF NOT EXISTS test.alopachuk_etl (
            event_date Date,
            dimension String,
            dimension_value String,
            views Float64,
            likes Float64,
            messages_received Float64,
            messages_sent Float64,
            users_received Float64,
            users_sent Float64 )
            ENGINE = MergeTree()
            ORDER BY event_date
            """
        ph.execute(create_table, connection=connection_test)
        ph.to_clickhouse(df_gender, 'alopachuk_etl', index=False, connection=connection_test)
        ph.to_clickhouse(df_os, 'alopachuk_etl', index=False, connection=connection_test)
        ph.to_clickhouse(df_age, 'alopachuk_etl', index=False, connection=connection_test)
        
    df_m = extract_m()
    df_f = extract_f()
    df = transfrom_join(df_m, df_f)
    df_gender = transform_gender(df)
    df_os = transform_os(df)
    df_age = transform_age(df)
    load(df_gender, df_os, df_age)

lopachuk_etl = lopachuk_etl()
    
    

        
             
        

