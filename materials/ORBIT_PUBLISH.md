# ORBIT v0.3 — publication and authorization

**Status: not deployed by the assistant.** The working environment has no authenticated GitHub write connector or usable GitHub CLI credentials. This guide and `publish.command` are a prepared workflow, not evidence of a running site.

## Русский

Распакуй архив. В Terminal перейди в `tiny-jepa-lab`. Нужны `git` и GitHub CLI. На macOS с Homebrew их можно установить командой `brew install gh git`. Запусти:

```bash
bash publish.command
```

Скрипт заранее сообщает, что исходники станут публичными, и просит ввести `PUBLISH`. Затем используется `gh auth login --web` или обновление разрешения `workflow` существующего OAuth-входа. Авторизация происходит на GitHub в браузере. Токен в чат, HTML, Python или переменные репозитория копировать не нужно.

Далее скрипт проверяет аккаунт `ArtAndrew`, создаёт `ArtAndrew/tiny-jepa-lab`, делает первый commit и push, включает Pages с `build_type=workflow`, задаёт `ORBIT_LEADERBOARD_ENABLED=true` и запускает Pages workflow. Он ждёт статуса выполнения и не печатает сообщение об успешном развёртывании до успешного завершения GitHub Actions.

Если репозиторий уже существует, скрипт останавливается до его изменения. Для обновления клонируй существующий репозиторий, скопируй новые исходники поверх рабочей копии, просмотри `git diff` и сделай обычный commit/push. Не удаляй существующий репозиторий и не делай force-push ради этой версии. Если имеется branch protection, публикуй через pull request.

Первый автоматический workflow от push может не пройти, потому что Pages ещё не включён; скрипт отдельно запускает `workflow_dispatch` после настройки. Если GitHub требует дополнительное согласование environment `github-pages`, выполни его в интерфейсе репозитория. CLI или API могут отказать из-за настроек организации, ограничений прав или биллинга; это не обходится скриптом.

Планируемые адреса после успешного развёртывания:

```text
https://artandrew.github.io/tiny-jepa-lab/
https://artandrew.github.io/tiny-jepa-lab/ru/
https://artandrew.github.io/tiny-jepa-lab/zh/
```

Это ожидаемые адреса, не подтверждение их доступности.

### Приём результатов

Открыта переменная репозитория `ORBIT_LEADERBOARD_ENABLED=true` — workflow обрабатывает новые issues с префиксом `[ORBIT replay] `. Игра подготавливает запись, но сам пользователь должен отправить её на GitHub. Далее Actions заново считает очки и публикует сайт. Никакой сервер в браузере не имитируется и число очков клиента не считается доверенным.

При наплыве спама установи переменную в `false` и при необходимости ограничь взаимодействия в GitHub. У этого минимального решения нет полноценной серверной антибот-системы. Не используй его для денежных соревнований. Снимок охватывает не больше 500 недавно обновлённых issues и 31 даты UTC. Старые записи могут выпадать из снимка; это не постоянная база рекордов.

Перед анонсом проверь HTTPS-страницу на настоящем телефоне, пять раундов, скачивание PNG, одну отправку результата из другого аккаунта, успешное завершение следующего workflow и появление результата в нужной дневной таблице. Превью ссылок в соцсетях проверяется отдельно: локальный PNG не доказывает корректный Open Graph на живом сайте.

## English

Run `bash publish.command` on your own machine, after installing Git and GitHub CLI. The script obtains authorization through GitHub's browser flow and publishes a public repository only under the expected account. It refuses existing repositories rather than overwriting them. Review the shell script before running it. It was syntax-checked but not executed against GitHub here.

For an existing repository, use an ordinary reviewed commit or pull request. Enable **Settings → Pages → GitHub Actions**, set repository variable `ORBIT_LEADERBOARD_ENABLED` to `true`, and run **Publish ORBIT and replay leaderboard**. The workflow uses the scoped built-in Actions token, read-only source/issue access, and Pages/OIDC permissions only for deployment. Do not create a browser-side secret.

After deployment, check the real site and one complete replay submission. The public board is asynchronous and bounded, not a realtime API or an anti-cheat service. Disable the repository variable to stop automatic issue-driven publication. The prepared workflow uses standard Ubuntu runners; no larger paid runner or persistent machine is configured. Service limits and account policy still apply.

## 简体中文

在自己的电脑上安装 Git 与 GitHub CLI，然后在解压目录运行 `bash publish.command`。脚本通过 GitHub 浏览器流程授权，确认公开发布，并检查账号为 `ArtAndrew`。它不会覆盖已有仓库。不要把令牌发送到聊天或放进网页。脚本只做过语法检查，尚未在 GitHub 上实际执行。

更新现有仓库时，应审查差异后普通提交或使用 pull request。在 **Settings → Pages** 选择 **GitHub Actions**，把仓库变量 `ORBIT_LEADERBOARD_ENABLED` 设为 `true`，再运行发布工作流。发布后，请用真实手机完成挑战、导出图片、提交一条回放，并确认后续工作流确实更新排行榜。排行榜异步更新，不是实时服务或可靠的人类防作弊系统；必要时把变量改为 `false`。

## Official references checked 2026-11-16

- https://cli.github.com/manual/gh_auth_login
- https://cli.github.com/manual/gh_run_list
- https://docs.github.com/en/rest/pages/pages#create-a-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.github.com/en/billing/concepts/product-billing/github-actions

GitHub currently treats standard hosted runner compute in public repositories as free; artifact storage and other account-level usage have their own rules. The workflow retains its Pages artifact for one day and does not select larger runners. This is not an unlimited-hosting or zero-cost guarantee under every account configuration.
