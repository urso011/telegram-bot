import html
from pyrogram import Client, filters
from pyrogram.types import (
    User,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database import cur
from config import ADMINS


def mention(user: User, with_id: bool = True, id=1) -> str:
    try:
        name = (
            f'{user.username}'
            if user.username
            else html.escape(user.first_name)
        )
    except Exception as e:
        print(e)

    mention = f'{name}'

    if with_id and not mention:
        mention += f' (<i>{id}</i>)'

    return mention


@Client.on_callback_query(filters.regex(r'^ranking$'))
async def ranking(c: Client, m: CallbackQuery):
    try:
        balance = cur.execute(
            f"""SELECT id, balance, username FROM users WHERE id not in {str(tuple(ADMINS))}
            ORDER BY balance DESC LIMIT 3"""
        ).fetchall()

        owners = cur.execute(
            f"""SELECT owner, count() as buy FROM cards_sold WHERE owner not in {str(tuple(ADMINS))}
            GROUP BY owner ORDER BY buy DESC LIMIT 3"""
        ).fetchall()

        emojis = {0: '🥇', 1: '🥈', 2: '🥉'}

        msg = str()

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='⬅️ Voltar', callback_data='start')]
            ]
        )

        if not owners and not balance:
            return m.edit_message_text(
                '<b>⚠️ Sem Informações.</b>', reply_markup=kb
            )

        if balance:
            tops_balance = '<b>🏆 TOP SALDO</b>\n\n' + '\n'.join(
                [
                    f'<i>{emojis[i]} {mention(await c.get_chat(chat_id=v[0]), id=v[0])}</i> {v[1]}'
                    for i, v in enumerate(balance)
                ]
            )
            msg += tops_balance

        if owners:
            top_buys = '\n<b>🏆 TOP COMPRAS</b>\n\n' + '\n'.join(
                [
                    f'<i>{emojis[i]} {mention(await c.get_chat(chat_id=v[0]), id=v[0])}</i> {v[1]}'
                    for i, v in enumerate(owners)
                ]
            )
            msg += f'\n{top_buys}'

        await m.edit_message_text(msg, reply_markup=kb)
    except:
        await m.answer('⚠️ Nenhum registro')
