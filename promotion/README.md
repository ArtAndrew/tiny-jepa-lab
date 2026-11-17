# Материалы для анонса ORBIT

Основная формулировка: **ORBIT — учебное демо модели мира, в которое можно сыграть.** Модель мира прогнозирует, что изменится в среде; в этой игре прогноз последствий действий помогает выбрать план движения шарика.

[Игра RU](https://artandrew.github.io/tiny-jepa-lab/ru/) · [Game EN](https://artandrew.github.io/tiny-jepa-lab/) · [Репозиторий](https://github.com/ArtAndrew/tiny-jepa-lab)

## Готовые материалы

- [Анимация для README](../docs/assets/orbit-demo.gif).
- [Видео MP4, 13 секунд](../docs/assets/orbit-demo.mp4).
- Обложки 1280 × 640: [EN](../docs/assets/orbit-social-en.png), [RU](../docs/assets/orbit-social-ru.png), [中文](../docs/assets/orbit-social-zh.png).
- [Описание актуального релиза v0.7](v0.7-release.md).
- [Черновик статьи](habr-draft.md).

Анимация — иллюстрированный повтор одного настоящего раунда, а не запись интерфейса. Траектории, действия и очки рассчитаны исходным кодом игры; план AI выбран встроенной обученной нейросетью. Это пример поведения, а не оценка качества на всей выборке. Данные примера: [demo-replay.json](demo-replay.json).

## Короткий пост по-русски

Сможешь направить шарик к цели лучше маленькой нейросети?

Сделал ORBIT — учебное демо модели мира в форме игры. Модель прогнозирует последствия действий и выбирает план: «Что случится, если толкнуть шарик так?»

Три действия — и первый быстрый раунд. Сначала твой ход, затем — сравнение с AI. Отправь другу ссылку на ту же сцену или попробуй режим «Найди слабость»: передвигай цель и добавляй шум, чтобы попасть туда, где модель промахнётся. Нейросеть работает прямо в браузере, регистрация для игры не нужна. Можно увидеть и удачные прогнозы, и промахи.

Попробуй и расскажи: было ли понятно, что делать и почему модель выбрала такой план?

Играть: https://artandrew.github.io/tiny-jepa-lab/ru/
Код: https://github.com/ArtAndrew/tiny-jepa-lab

## Short English post

Can you guide a ball to the target better than a tiny neural network?

I made ORBIT, a playable world-model demo. A small JEPA-inspired model predicts the effects of actions and uses those predictions to plan. Pick three actions, run the round, and compare your result with the AI.

Start with one quick round, challenge a friend through a replayable link, or build a scene where you hit and the model misses. Local browser inference, no sign-up to play. I'd love feedback on whether the game makes prediction-based planning easier to understand.

Play: https://artandrew.github.io/tiny-jepa-lab/
Code: https://github.com/ArtAndrew/tiny-jepa-lab

## Show HN — заголовок и первый комментарий

**Show HN: ORBIT – a tiny world model you can play against in your browser**

Ссылка публикации: https://artandrew.github.io/tiny-jepa-lab/

Комментарий:

I built ORBIT to make a small world model tangible. You see a moving ball and choose three left/no-push/right actions. A pretrained JEPA-inspired network observes two images, predicts the latent outcomes of all 27 plans, and selects the one closest to the goal image. The simulator then shows what actually happens.

The neural planner does not receive the simulator's coordinates or velocity. Its coordinate readout is for visualization; plan selection happens in feature space. This is a deliberately narrow educational demo, not Meta's V-JEPA model or a comparison claiming to beat LLMs.

It runs locally in the browser. Playing needs no account; the optional public leaderboard uses GitHub issues and verifies replays. The repository includes separate weights, the complete encoder and action-predictor training code, synthetic data generation, runnable notebooks, tests and benchmark reports. The current model scored 74.45% on the 3,072-scene set used to select it from three training runs; this is not an independent post-selection estimate.

I'd appreciate feedback on the explanation and controls, and examples where the model's plan fails.

Source: https://github.com/ArtAndrew/tiny-jepa-lab

## Небольшой первый запуск

1. Дать игру 10–20 знакомым и собрать конкретные замечания к первому раунду. Это план тестирования, не обещание охвата.
2. Исправить повторяющиеся проблемы.
3. Опубликовать ролик и один короткий пост в подходящем сообществе, соблюдая его правила; отвечать на вопросы.
4. Подать Show HN, когда автор готов обсуждать реализацию. Не просить голоса или комментарии для продвижения.
5. Через неделю посмотреть переходы в GitHub → Insights → Traffic, отзывы и отправленные результаты. Посещения репозитория не равны числу сыгранных игр.

Тексты здесь — материалы для адаптации под правила каждого сообщества. [Предложение для Awesome JEPA](awesome-jepa-proposal.md) · [Пост Show and tell](show-and-tell.md).

Основания рекомендаций: [Show HN](https://news.ycombinator.com/showhn.html), [Open Source Guides](https://opensource.guide/finding-users/), [GitHub Traffic](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository).
