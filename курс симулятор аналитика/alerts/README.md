# Поиск аномалий (система алертов)

## Задача

Напишите систему алертов для нашего приложения. Система должна с периодичность каждые 15 минут проверять ключевые метрики, такие как активные пользователи в ленте / мессенджере, просмотры, лайки, CTR, количество отправленных сообщений. 

Изучите поведение метрик и подберите наиболее подходящий метод для детектирования аномалий. На практике как правило применяются статистические методы. 

В случае обнаружения аномального значения, в чат должен отправиться алерт - сообщение со следующей информацией: метрика, ее значение, величина отклонения.
В сообщение можно добавить дополнительную информацию, которая поможет при исследовании причин возникновения аномалии, это может быть, например,  график, ссылки на дашборд/чарт в BI-системе. 

## Данные

- таблица feed_actions - данные о просмотре постов в ленте:

user_id - уникальный идентификатор пользователя  
post_id - уникальный идентификатор поста в ленте  
action - просмотр или лайк  
time - дата и время  
gender - пол  
age - возраст  
country - страна  
city - город  
os - операционная система  
source - источник трафика, который привёл пользователя в приложение  
exp_group - группа (для A/B-тестов)  

- таблица message_actions - данные об отправке сообщений:

user_id - уникальный идентификатор пользователя-отправителя  
reciever_id - уникальный идентификатор пользователя-получателя  
time - дата и время  
source - источник трафика, который привёл пользователя в приложение  
exp_group - группа (для A/B-тестов)  
gender - пол  
age - возраст  
country - страна  
city - город  
os - операционная система  

## Результат

В качестве метода обнаружения аномалий был выбран метод, использующий межквартильный размах. Скрипт [здесь](alerts.py)  
Пример алерта по метрике likes:  
![image](https://user-images.githubusercontent.com/122831288/231826467-2181173e-d854-4e32-a721-cde9e5c7b8af.png)  
Дашборд:  
![image](https://user-images.githubusercontent.com/122831288/231826564-e3eb5ae0-e236-4fce-9898-3c7033c2535f.png)

## Используемые библиотеки

*pandas*, *matplotlib*, *seaborn*
