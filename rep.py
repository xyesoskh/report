"""
Clean, safe Telegram reporter script for Telethon.
Works with older and newer Telethon versions: it tries to use the modern `reason=` argument
(if available) and falls back to the older `option` (bytes) signature when necessary.

Usage:
  1) pip install telethon
  2) python3 clean_reporter.py

The script will interactively ask for api_id, api_hash (or you can set them as env vars),
session name, target (username or channel link), optional post id, message and number of reports.

This script does NOT contain obfuscation or marshal/exec and is safe to inspect.
"""

import asyncio
import os
from telethon import TelegramClient, functions, types


def _int_or_none(s):
    try:
        return int(s)
    except Exception:
        return None


async def send_report(client, peer, message, ids, use_reason):
    """Send one ReportRequest; use_reason means try modern call with types.InputReportReasonSpam().
    Falls back to older signature if needed.
    Returns the result or raises an exception.
    """
    try:
        if use_reason:
            # modern Telethon: reason= types.InputReportReasonSpam()
            return await client(functions.messages.ReportRequest(
                peer=peer,
                id=ids,
                reason=types.InputReportReasonSpam(),
                message=message
            ))
        else:
            # older Telethon signature: (peer, id, option, message)
            return await client(functions.messages.ReportRequest(
                peer,
                ids,
                b"",
                message
            ))
    except TypeError:
        # fallback if signature mismatches
        if use_reason:
            return await client(functions.messages.ReportRequest(peer, ids, b"", message))
        else:
            return await client(functions.messages.ReportRequest(peer=peer, id=ids, reason=types.InputReportReasonSpam(), message=message))


async def main():
    print('\n=== Clean Reporter (Telethon) ===\n')

    api_id = os.getenv('API_ID') or input('API_ID (from my.telegram.org): ').strip()
    api_hash = os.getenv('API_HASH') or input('API_HASH (from my.telegram.org): ').strip()
    session = input('Session file name (default: reporter): ').strip() or 'reporter'

    client = TelegramClient(session, int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print('Not logged in — starting interactive sign-in...')
        await client.start()

    target = input('\nTarget (channel/group username or link, without @ is OK): ').strip()
    if target.startswith('@'):
        target = target[1:]

    post_id_raw = input('Post ID (leave empty to report the channel itself): ').strip()
    post_id = _int_or_none(post_id_raw)
    ids = [post_id] if post_id is not None else []

    message = input('Message (reason/details to include in report): ').strip() or \
              'Подозрение на накрутку подписчиков и использование фейковых аккаунтов.'

    # --- ввод количества репортов ---
    count_raw = input('How many reports to send: ').strip() or '1'
    try:
        count = int(count_raw)
        if count < 1:
            print('Нужно ввести число >= 1. Устанавливаю count = 1.')
            count = 1
    except ValueError:
        print('Неверный ввод — устанавливаю count = 1.')
        count = 1

    MAX_SAFE = 50
    if count > MAX_SAFE:
        print(f'Для безопасности максимум = {MAX_SAFE}. Уменьшаю количество до {MAX_SAFE}.')
        count = MAX_SAFE

    # Resolve peer
    try:
        peer = await client.get_input_entity(target)
    except Exception:
        try:
            peer = await client.get_input_entity('@' + target)
        except Exception as e:
            print('Не удалось получить entity для цели:', e)
            await client.disconnect()
            return

    # Decide whether modern 'reason' param exists by trying once with reason flag
    use_reason = True
    try:
        sig = functions.messages.ReportRequest.__init__.__annotations__
        if 'reason' not in sig:
            use_reason = False
    except Exception:
        use_reason = True

    print('\nSending reports...')
    successes = 0
    failures = 0
    for i in range(count):
        try:
            res = await send_report(client, peer, message, ids, use_reason)
            print(f'[{i+1}/{count}] Успешная отправка!')
            successes += 1
        except Exception as e:
            print(f'[{i+1}/{count}] Ошибка при отправке:', repr(e))
            failures += 1
        await asyncio.sleep(1)  # безопасная задержка между запросами

    print(f'\nDone. Successes: {successes}, Failures: {failures}')
    await client.disconnect()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nInterrupted by user')
