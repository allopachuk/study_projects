# A/B-тесты

## Задачи

Мы продумали дизайн эксперимента, и теперь нужно проверить корректность работы системы сплитования, выбрать подходящий статистический метод и проанализировать полученные результаты.

1. Провести АА-тест и убедиться в том, что наша система сплитования работает корректно, и ключевая метрика не отличается между группами не только в конкретно нашем АА-тесте, но и в целом  
2. Проанализировать данные А/B-теста: сравнить данные разными тестами, сделать вывод о результатах каждого и написать рекомендацию, раскатывать ли новый алгоритм на всех новых пользователей или нет  
3. Проанализировать t-тест между группами 0/3 и 1/2 по метрике линеаризованных лайков и сделать выводы

## Данные

- данные А/А-теста
- данные A/B-теста

## Результаты

1. Проведена симуляция 10000 А/А-тестов: сформированы подвыборки без повторения в 500 юзеров из 2 и 3 экспериментальной группы 10000 раз и проведено сравнение этих подвыборок t-testом.  
Построена гистограмма распределения получившихся 10000 p-values. Судя по графику, распределение p-values похоже на равномерное.  
![image](https://user-images.githubusercontent.com/122831288/231827165-76e88396-2ef5-4cdc-bce1-2dd7da94a942.png)  
Процент p-values, который меньше или равен 0.05, меньше 5. Статистически значимые различия между 2 и 3 группой проявляются только в ~4.49 % случаев.  
Следовательно, статистически значимой разницы между группами нет, и система сплитования работает корректно.  
Подробнее [здесь](https://github.com/allopachuk/study_projects/blob/main/%D0%BA%D1%83%D1%80%D1%81%20%D1%81%D0%B8%D0%BC%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80%20%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D1%82%D0%B8%D0%BA%D0%B0/a-b_tests/1.%20%D0%BF%D1%80%D0%BE%D0%B2%D0%B5%D1%80%D0%BA%D0%B0%20%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D1%8B%20%D1%81%D0%BF%D0%BB%D0%B8%D1%82%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F.ipynb)
2. Построена гистограмма распределения CTR в группах A и B.  
![image](https://user-images.githubusercontent.com/122831288/231827707-5f16f914-c5f5-4638-a613-133c6b796904.png)  
При анализе данных был использован t-тест, тест Манна-Уитни, t-тест на сглаженном CTR, пуассоновский bootstrap, t-тест и тест Манна-Уитни после бакетного преобразования.  
Хуже всего показал себя t-тест, остальные тесты показали статистически значимые различия между группами A и B.  
Пуассоновский бутстреп показал отрицательное влияние нововведений на измеряемую метрику, поэтому новый алгоритм применять не рекомендуется.  
![image](https://user-images.githubusercontent.com/122831288/231827980-1178e5ff-156a-46d0-b349-e3ed9f09d0a3.png)  
Подробнее [здесь](https://github.com/allopachuk/study_projects/blob/main/%D0%BA%D1%83%D1%80%D1%81%20%D1%81%D0%B8%D0%BC%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80%20%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D1%82%D0%B8%D0%BA%D0%B0/a-b_tests/2.%20%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D0%B7%20%D1%80%D0%B5%D0%B7%D1%83%D0%BB%D1%8C%D1%82%D0%B0%D1%82%D0%BE%D0%B2%20%D1%8D%D0%BA%D1%81%D0%BF%D0%B5%D1%80%D0%B8%D0%BC%D0%B5%D0%BD%D1%82%D0%B0.ipynb)
3. Оба t-теста (по CTR и по метрике линеаризованных лайков) в группах 0 и 3 показали статистически значимое различие между ними (p-value < 0.05). p-value в t-тесте по метрике линеаризованных лайков меньше, чем в t-тесте по CTR, следовательно, тест чувствительнее.  
Распределение CTR:  
![image](https://user-images.githubusercontent.com/122831288/231828260-a5cba9a4-df08-4b3e-95dc-fcee4eb082d2.png)  
Распределение линеаризованных лайков:  
![image](https://user-images.githubusercontent.com/122831288/231828449-2f7dee93-e3e8-4ebe-b2bd-dd6922b447e5.png)  
t-тест по CTR в группах 1 и 2 не показал различия между ними (p-value > 0.05). p-value в t-тесте по метрике линеаризованных лайков намного меньше, чем в t-тесте по CTR (p-value < 0.05), этот тест показал различия между группами, следовательно, он чувствительнее.  
Распределение CTR:  
![image](https://user-images.githubusercontent.com/122831288/231828562-719de825-273a-49ed-89f8-9b3dc5ccd472.png)  
Распределение линеаризованных лайков:  
![image](https://user-images.githubusercontent.com/122831288/231828673-6abaede6-b025-48e0-9f48-9f0a19d63649.png)  
Подробнее [здесь](https://github.com/allopachuk/study_projects/blob/main/%D0%BA%D1%83%D1%80%D1%81%20%D1%81%D0%B8%D0%BC%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80%20%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D1%82%D0%B8%D0%BA%D0%B0/a-b_tests/3.%20%D0%BD%D0%BE%D0%B2%D1%8B%D0%B9%20%D0%BC%D0%B5%D1%82%D0%BE%D0%B4%20%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D0%B7%D0%B0%20%D1%82%D0%B5%D1%81%D1%82%D0%BE%D0%B2.ipynb)

## Используемые библиотеки

*pandas*, *numpy*, *scipy*, *matplotlib*, *seaborn*
