import asyncio
import os
from telethon import TelegramClient, functions, types
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()
eye = "👁️"


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def _int_or_none(s):
    try:
        return int(s)
    except Exception:
        return None


async def send_report(client, peer, message, ids, use_reason):
    try:
        if use_reason:
            return await client(functions.messages.ReportRequest(
                peer=peer,
                id=ids,
                reason=types.InputReportReasonSpam(),
                message=message
            ))
        else:
            return await client(functions.messages.ReportRequest(
                peer,
                ids,
                b"",
                message
            ))
    except TypeError:
        if use_reason:
            return await client(functions.messages.ReportRequest(peer, ids, b"", message))
        else:
            return await client(functions.messages.ReportRequest(
                peer=peer,
                id=ids,
                reason=types.InputReportReasonSpam(),
                message=message
            ))


async def reporter_main():
    console.print('\n[bold cyan]Аккаунт с которого будут отправляться репорты[/bold cyan]\n')

    api_id = os.getenv('API_ID') or input('[bold cyan]API_ID (from my.telegram.org):[/bold cyan]').strip()
    api_hash = os.getenv('API_HASH') or input('[bold cyan]API_HASH (from my.telegram.org):[/bold cyan] ').strip()
    session = input('[bold cyan]Session file name (default: reporter):[/bold cyan] ').strip() or 'reporter'

    client = TelegramClient(session, int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        console.print('[yellow]Not logged in — starting interactive sign-in...[/yellow]')
        await client.start()

    target = input('\n[bold cyan]Target (channel/group username or link):[/bold cyan] ').strip()
    if target.startswith('@'):
        target = target[1:]

    post_id_raw = input('[bold cyan]Post ID (leave empty to report the channel itself):[/bold cyan] ').strip()
    post_id = _int_or_none(post_id_raw)
    ids = [post_id] if post_id is not None else []

    message = input('Message (reason/details): ').strip() or \
        'Подозрение на накрутку подписчиков и использование фейковых аккаунтов.'

    count_raw = input('[/bold cyan]How many reports to send:[/bold cyan] ').strip() or '1'
    try:
        count = int(count_raw)
        if count < 1:
            count = 1
    except ValueError:
        count = 1

    MAX_SAFE = 150
    if count > MAX_SAFE:
        console.print(f"[yellow]Для безопасности максимум = {MAX_SAFE}. Уменьшаю количество до {MAX_SAFE}.[/yellow]")
        count = MAX_SAFE

    try:
        peer = await client.get_input_entity(target)
    except Exception:
        try:
            peer = await client.get_input_entity('@' + target)
        except Exception as e:
            console.print(f"[red]Не удалось получить entity для цели:[/red] {e}")
            await client.disconnect()
            return

    use_reason = True
    try:
        sig = functions.messages.ReportRequest.__init__.__annotations__
        if 'reason' not in sig:
            use_reason = False
    except Exception:
        use_reason = True

    console.print('\n[cyan]Отправка репортов...[/cyan]')
    successes = 0
    failures = 0
    for i in range(count):
        try:
            await send_report(client, peer, message, ids, use_reason)
            console.print(f"[green][{i+1}/{count}] Успешная отправка![/green]")
            successes += 1
        except Exception as e:
            console.print(f"[red][{i+1}/{count}] Ошибка при отправке:[/red] {repr(e)}")
            failures += 1
        await asyncio.sleep(1)

    console.print(f"\n[bold green]Done.[/bold green] Successes: {successes}, Failures: {failures}")
    await client.disconnect()


# === Меню интерфейс ===

def show_header():
    console.print(Panel.fit(
        f"[bold cyan]{eye}[/bold cyan]\n[bold magenta]Snoser by pvp[/bold magenta]",
        title="[white]Главное меню[/white]",
        border_style="cyan"
    ))


def run_reporter():
    console.print("\n[green]Запуск сносера[/green]")
    asyncio.run(reporter_main())
    console.print("[cyan]Завершено. Возврат в меню.[/cyan]")


def main_menu():
    while True:
        clear_console()  # Очищаем консоль перед выводом меню
        show_header()
        console.print("\n[bold white]Выберите действие:[/bold white]")
        console.print("[cyan]1.[/cyan] Снонс аккаунта")
        console.print("[cyan]2.[/cyan] Снос канала")
        console.print("[cyan]3.[/cyan] Выйти")

        choice = Prompt.ask("\n[bold red]Введите номер[/bold red]")

        if choice in ["1", "2"]:
            console.print(f"\n[red]→ Репорт ({'человек' if choice=='1' else 'канал'})[/red]")
            run_reporter()
            input("\nНажмите Enter, чтобы вернуться в меню...")
        elif choice == "3":
            console.print("\n[red]Выход.[/red]")
            break


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Остановлено пользователем.[/red]")

